"""
Celery tasks for sending notifications.
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import requests
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_new_application_notification(application_id):
    """
    Send notification when a new pilot application is submitted.
    Sends Slack alert for hot/warm leads, email for all leads.
    """
    from leads.models import PilotApplication
    
    try:
        application = PilotApplication.objects.get(id=application_id)
    except PilotApplication.DoesNotExist:
        logger.error(f"Application {application_id} not found")
        return
    
    # Send Slack notification based on priority tier
    send_slack_notification(application)
    
    # Send email confirmation to applicant
    send_applicant_confirmation_email(application)
    
    # Send admin notification for hot leads
    if application.priority_tier == 'hot':
        send_hot_lead_alert(application)


@shared_task
def send_status_update_notification(application_id, old_status, new_status):
    """
    Send notification when application status changes.
    """
    from leads.models import PilotApplication
    
    try:
        application = PilotApplication.objects.get(id=application_id)
    except PilotApplication.DoesNotExist:
        logger.error(f"Application {application_id} not found")
        return
    
    # Send status update email to applicant
    send_status_update_email(application, old_status, new_status)
    
    # Send Slack notification for significant status changes
    if new_status in ['call_scheduled', 'pilot_active', 'converted']:
        send_slack_status_update(application, old_status, new_status)


@shared_task
def send_daily_digest():
    """
    Send daily digest of new leads and pending actions.
    """
    from leads.models import PilotApplication
    from django.utils import timezone
    from datetime import timedelta
    
    # Get leads from last 24 hours
    yesterday = timezone.now() - timedelta(days=1)
    new_leads = PilotApplication.objects.filter(submitted_at__gte=yesterday)
    
    # Get pending hot leads
    hot_leads = PilotApplication.objects.filter(
        priority_tier='hot',
        status='pending'
    )
    
    # Get upcoming calls
    upcoming_calls = PilotApplication.objects.filter(
        alignment_call_scheduled__gte=timezone.now(),
        alignment_call_scheduled__lte=timezone.now() + timedelta(days=2)
    )
    
    context = {
        'new_leads': new_leads,
        'hot_leads': hot_leads,
        'upcoming_calls': upcoming_calls,
        'date': timezone.now().strftime('%Y-%m-%d')
    }
    
    # Send email digest
    html_message = render_to_string('notifications/daily_digest.html', context)
    
    send_mail(
        subject=f'EIS Daily Digest - {context["date"]}',
        message='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.ADMIN_EMAIL],
        html_message=html_message,
        fail_silently=True
    )


def send_slack_notification(application):
    """
    Send Slack notification based on priority tier.
    """
    if not settings.SLACK_WEBHOOK_URL:
        return
    
    # Different messages based on tier
    tier_configs = {
        'hot': {
            'color': '#FF0000',
            'title': '🔥 HOT LEAD - Immediate Action Required',
            'mention': '@channel'
        },
        'warm': {
            'color': '#FFA500',
            'title': '🔆 WARM LEAD - Same Day Response',
            'mention': ''
        },
        'cool': {
            'color': '#00BFFF',
            'title': '❄️ COOL LEAD - Next Day Response',
            'mention': ''
        },
        'nurture': {
            'color': '#808080',
            'title': '🌱 NURTURE LEAD - Automated Sequence',
            'mention': ''
        }
    }
    
    config = tier_configs.get(application.priority_tier, tier_configs['nurture'])
    
    payload = {
        'attachments': [{
            'color': config['color'],
            'title': config['title'],
            'fields': [
                {'title': 'Organization', 'value': application.organization_name, 'short': True},
                {'title': 'Score', 'value': f"{application.qualification_score}/100", 'short': True},
                {'title': 'Industry', 'value': application.industry, 'short': True},
                {'title': 'Team Size', 'value': application.team_size, 'short': True},
                {'title': 'Challenge', 'value': application.primary_challenge, 'short': True},
                {'title': 'Scope', 'value': application.organizational_scope, 'short': True},
                {'title': 'Sponsor', 'value': application.sponsor_name, 'short': True},
                {'title': 'Email', 'value': application.email, 'short': True},
                {'title': 'Phone', 'value': application.phone, 'short': True},
            ],
            'footer': 'EIS - Executive Intelligence System',
            'ts': application.submitted_at.timestamp()
        }]
    }
    
    if config['mention']:
        payload['text'] = config['mention']
    
    try:
        response = requests.post(
            settings.SLACK_WEBHOOK_URL,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to send Slack notification: {e}")


def send_slack_status_update(application, old_status, new_status):
    """
    Send Slack notification for status updates.
    """
    if not settings.SLACK_WEBHOOK_URL:
        return
    
    status_emojis = {
        'pending': '⏳',
        'reviewed': '👀',
        'call_scheduled': '📅',
        'call_completed': '✅',
        'pilot_active': '🚀',
        'converted': '💰',
        'rejected': '❌',
        'nurture': '🌱'
    }
    
    old_emoji = status_emojis.get(old_status, '')
    new_emoji = status_emojis.get(new_status, '')
    
    payload = {
        'text': f"Lead status updated: *{application.organization_name}*",
        'attachments': [{
            'color': '#36a64f',
            'fields': [
                {'title': 'Previous Status', 'value': f"{old_emoji} {old_status.title()}", 'short': True},
                {'title': 'New Status', 'value': f"{new_emoji} {new_status.title()}", 'short': True},
            ]
        }]
    }
    
    try:
        response = requests.post(
            settings.SLACK_WEBHOOK_URL,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to send Slack status update: {e}")


def send_applicant_confirmation_email(application):
    """
    Send confirmation email to the applicant.
    """
    context = {
        'organization_name': application.organization_name,
        'sponsor_name': application.sponsor_name,
        'score': application.qualification_score,
        'tier': application.priority_tier,
        'estimated_response': application.estimated_response_time,
        'application_id': str(application.id)
    }
    
    html_message = render_to_string('notifications/applicant_confirmation.html', context)
    
    send_mail(
        subject='Your Executive Pilot Application - JavisOne',
        message='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[application.email],
        html_message=html_message,
        fail_silently=True
    )


def send_status_update_email(application, old_status, new_status):
    """
    Send status update email to the applicant.
    """
    templates = {
        'call_scheduled': 'notifications/status_call_scheduled.html',
        'pilot_active': 'notifications/status_pilot_active.html',
        'converted': 'notifications/status_converted.html',
        'rejected': 'notifications/status_rejected.html',
    }
    
    template = templates.get(new_status, 'notifications/status_generic.html')
    
    context = {
        'organization_name': application.organization_name,
        'sponsor_name': application.sponsor_name,
        'new_status': new_status,
        'application_id': str(application.id)
    }
    
    html_message = render_to_string(template, context)
    
    subject_map = {
        'call_scheduled': 'Alignment Call Scheduled - JavisOne',
        'pilot_active': 'Your Pilot is Now Active - JavisOne',
        'converted': 'Welcome to JavisOne - JavisOne',
        'rejected': 'Update on Your Application - JavisOne',
    }
    
    send_mail(
        subject=subject_map.get(new_status, 'Application Update - JavisOne'),
        message='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[application.email],
        html_message=html_message,
        fail_silently=True
    )


def send_hot_lead_alert(application):
    """
    Send urgent email alert for hot leads.
    """
    html_message = render_to_string('notifications/hot_lead_alert.html', {
        'application': application
    })
    
    send_mail(
        subject=f'🔥 URGENT: Hot Lead - {application.organization_name}',
        message='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.ADMIN_EMAIL],
        html_message=html_message,
        fail_silently=True
    )
