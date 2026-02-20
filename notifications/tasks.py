"""
Celery tasks for sending notifications via Telegram and Email.
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import requests
import logging

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"


def send_telegram_message(chat_id, message, parse_mode='HTML'):
    """
    Send a message via Telegram bot.
    """
    if not settings.TELEGRAM_BOT_TOKEN or not chat_id:
        logger.warning("Telegram bot token or chat ID not configured")
        return False
    
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': parse_mode,
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


@shared_task
def send_new_application_notification(application_id):
    """
    Send notification when a new pilot application is submitted.
    Sends Telegram alert for hot/warm leads, email for all leads.
    """
    from leads.models import PilotApplication
    
    try:
        application = PilotApplication.objects.get(id=application_id)
    except PilotApplication.DoesNotExist:
        logger.error(f"Application {application_id} not found")
        return
    
    # Send Telegram notification based on priority tier
    send_telegram_lead_notification(application)
    
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
    
    # Send Telegram notification for significant status changes
    if new_status in ['call_scheduled', 'pilot_active', 'converted']:
        send_telegram_status_update(application, old_status, new_status)


@shared_task
def send_followup_reminder(application_id):
    """
    Send reminder for leads that need follow-up.
    """
    from leads.models import PilotApplication
    
    try:
        application = PilotApplication.objects.get(id=application_id)
    except PilotApplication.DoesNotExist:
        logger.error(f"Application {application_id} not found")
        return
    
    # Only send reminders for hot leads that are still pending
    if application.priority_tier == 'hot' and application.status == 'pending':
        message = f"""⚠️ <b>FOLLOW-UP REMINDER</b>

🔥 Hot lead still pending: <b>{application.organization_name}</b>
Score: {application.qualification_score}/100
Submitted: {application.submitted_at.strftime('%Y-%m-%d %H:%M')}

Contact: {application.sponsor_name}
Email: {application.email}
Phone: {application.phone}

<b>Action Required:</b> Respond within {settings.HOT_LEAD_RESPONSE_HOURS} hours"""
        
        send_telegram_message(settings.TELEGRAM_CHAT_ID, message)
        
        # Also send email
        send_mail(
            subject=f'⚠️ Follow-up Required: {application.organization_name}',
            message=f'Hot lead {application.organization_name} has been pending for 24 hours.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=True
        )


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
    
    # Get pending warm leads
    warm_leads = PilotApplication.objects.filter(
        priority_tier='warm',
        status='pending'
    )
    
    # Get upcoming calls
    upcoming_calls = PilotApplication.objects.filter(
        alignment_call_scheduled__gte=timezone.now(),
        alignment_call_scheduled__lte=timezone.now() + timedelta(days=2)
    )
    
    date_str = timezone.now().strftime('%Y-%m-%d')
    
    # Send Telegram summary
    telegram_message = f"""📊 <b>DAILY DIGEST - {date_str}</b>

📥 New Leads (24h): <b>{new_leads.count()}</b>
🔥 Hot Pending: <b>{hot_leads.count()}</b>
🔆 Warm Pending: <b>{warm_leads.count()}</b>
📅 Upcoming Calls: <b>{upcoming_calls.count()}</b>
"""
    
    if hot_leads.exists():
        telegram_message += "\n<b>🔥 HOT LEADS REQUIRING ACTION:</b>\n"
        for lead in hot_leads[:5]:
            telegram_message += f"• {lead.organization_name} ({lead.sponsor_name})\n"
    
    send_telegram_message(settings.TELEGRAM_CHAT_ID, telegram_message)
    
    # Send email digest
    context = {
        'new_leads': new_leads,
        'hot_leads': hot_leads,
        'warm_leads': warm_leads,
        'upcoming_calls': upcoming_calls,
        'date': date_str
    }
    
    html_message = render_to_string('notifications/daily_digest.html', context)
    
    send_mail(
        subject=f'JavisOne Daily Digest - {date_str}',
        message='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.ADMIN_EMAIL],
        html_message=html_message,
        fail_silently=True
    )


def send_telegram_lead_notification(application):
    """
    Send Telegram notification for new leads based on priority tier.
    """
    chat_id = settings.TELEGRAM_CHAT_ID
    if not chat_id:
        return
    
    # Different messages based on tier
    tier_configs = {
        'hot': {
            'emoji': '🔥',
            'title': 'HOT LEAD - IMMEDIATE ACTION',
            'priority': 'RESPOND WITHIN 4 HOURS'
        },
        'warm': {
            'emoji': '🔆',
            'title': 'WARM LEAD - SAME DAY RESPONSE',
            'priority': 'Respond today'
        },
        'cool': {
            'emoji': '❄️',
            'title': 'COOL LEAD - NEXT DAY RESPONSE',
            'priority': 'Respond within 24 hours'
        },
        'nurture': {
            'emoji': '🌱',
            'title': 'NURTURE LEAD',
            'priority': 'Automated sequence active'
        }
    }
    
    config = tier_configs.get(application.priority_tier, tier_configs['nurture'])
    
    message = f"""{config['emoji']} <b>{config['title']}</b>

<b>Organization:</b> {application.organization_name}
<b>Score:</b> {application.qualification_score}/100
<b>Tier:</b> {application.priority_tier.upper()}

<b>Contact:</b> {application.sponsor_name}
<b>Email:</b> {application.email}
<b>Phone:</b> {application.phone}

<b>Details:</b>
• Industry: {application.industry}
• Team Size: {application.team_size}
• Scope: {application.organizational_scope}
• Challenge: {application.primary_challenge}

<b>Priority:</b> {config['priority']}

<a href="https://admin.javisone.com/admin/leads/pilotapplication/{application.id}/change/">View in Admin</a>
"""
    
    send_telegram_message(chat_id, message)


def send_telegram_status_update(application, old_status, new_status):
    """
    Send Telegram notification for status updates.
    """
    chat_id = settings.TELEGRAM_CHAT_ID
    if not chat_id:
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
    
    old_emoji = status_emojis.get(old_status, '•')
    new_emoji = status_emojis.get(new_status, '•')
    
    message = f"""📊 <b>LEAD STATUS UPDATE</b>

<b>{application.organization_name}</b>

{old_emoji} {old_status.replace('_', ' ').title()}
⬇️
{new_emoji} <b>{new_status.replace('_', ' ').title()}</b>

Contact: {application.sponsor_name}
Score: {application.qualification_score}/100
"""
    
    send_telegram_message(chat_id, message)


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


@shared_task
def check_pending_hot_leads():
    """
    Check for hot leads that have been pending for more than 24 hours
    and send follow-up reminders.
    """
    from leads.models import PilotApplication
    from django.utils import timezone
    from datetime import timedelta
    
    # Get hot leads that have been pending for 24+ hours
    cutoff_time = timezone.now() - timedelta(hours=settings.FOLLOWUP_REMINDER_HOURS)
    
    pending_hot_leads = PilotApplication.objects.filter(
        priority_tier='hot',
        status='pending',
        submitted_at__lte=cutoff_time
    )
    
    for lead in pending_hot_leads:
        # Check if we haven't already sent a reminder recently
        from activities.models import LeadActivity
        recent_reminder = LeadActivity.objects.filter(
            lead=lead,
            activity_type='followup_reminder',
            created_at__gte=cutoff_time
        ).exists()
        
        if not recent_reminder:
            # Send reminder
            send_followup_reminder.delay(str(lead.id))
            
            # Log the reminder
            LeadActivity.objects.create(
                lead=lead,
                activity_type='followup_reminder',
                description=f'Automated follow-up reminder sent after {settings.FOLLOWUP_REMINDER_HOURS} hours'
            )


@shared_task
def send_weekly_summary():
    """
    Send weekly summary of all pipeline activity.
    """
    from leads.models import PilotApplication
    from django.utils import timezone
    from datetime import timedelta
    
    # Get last 7 days stats
    last_week = timezone.now() - timedelta(days=7)
    
    new_leads = PilotApplication.objects.filter(submitted_at__gte=last_week)
    converted_leads = PilotApplication.objects.filter(
        status='converted',
        updated_at__gte=last_week
    )
    
    # Pipeline snapshot
    pipeline_counts = {
        'pending': PilotApplication.objects.filter(status='pending').count(),
        'reviewed': PilotApplication.objects.filter(status='reviewed').count(),
        'call_scheduled': PilotApplication.objects.filter(status='call_scheduled').count(),
        'call_completed': PilotApplication.objects.filter(status='call_completed').count(),
        'pilot_active': PilotApplication.objects.filter(status='pilot_active').count(),
        'converted': PilotApplication.objects.filter(status='converted').count(),
    }
    
    # Send Telegram summary
    week_str = timezone.now().strftime('%Y-%m-%d')
    message = f"""📈 <b>WEEKLY SUMMARY - Week of {week_str}</b>

<b>New Leads:</b> {new_leads.count()}
<b>Conversions:</b> {converted_leads.count()}

<b>Current Pipeline:</b>
⏳ Pending: {pipeline_counts['pending']}
👀 Reviewed: {pipeline_counts['reviewed']}
📅 Call Scheduled: {pipeline_counts['call_scheduled']}
✅ Call Completed: {pipeline_counts['call_completed']}
🚀 Pilot Active: {pipeline_counts['pilot_active']}
💰 Converted: {pipeline_counts['converted']}

<a href="https://dash.javisone.com">View Dashboard</a>
"""
    
    send_telegram_message(settings.TELEGRAM_CHAT_ID, message)
    
    # Send email summary
    context = {
        'new_leads': new_leads,
        'converted_leads': converted_leads,
        'pipeline_counts': pipeline_counts,
        'week_start': last_week.strftime('%Y-%m-%d'),
        'week_end': timezone.now().strftime('%Y-%m-%d')
    }
    
    html_message = render_to_string('notifications/weekly_summary.html', context)
    
    send_mail(
        subject=f'JavisOne Weekly Summary - {week_str}',
        message='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.ADMIN_EMAIL],
        html_message=html_message,
        fail_silently=True
    )
