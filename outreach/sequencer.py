import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction

from .models import (
    Prospect, Contact, Campaign, SequenceStage, 
    OutreachEmail, Engagement, SuppressionList
)
from .services import SESService, WarmupService, ReputationMonitor

logger = logging.getLogger(__name__)


class EmailSequencer:
    """Orchestrate email sequences and stage progression"""
    
    def __init__(self):
        self.ses_service = SESService()
    
    def get_next_send_time(self, stage, timezone_str='Africa/Kampala'):
        """
        Calculate the next optimal send time
        Respects the stage's time window and avoids weekends
        """
        from django.utils import timezone as django_timezone
        import pytz
        
        tz = pytz.timezone(timezone_str)
        now = django_timezone.now().astimezone(tz)
        
        # Start from tomorrow at the beginning of the time window
        next_date = now.date() + timedelta(days=1)
        next_time = datetime.combine(next_date, stage.send_time_window_start)
        next_datetime = tz.localize(next_time)
        
        # Skip weekends
        while next_datetime.weekday() >= 5:  # Saturday = 5, Sunday = 6
            next_datetime += timedelta(days=1)
        
        # Ensure within time window
        window_end = datetime.combine(next_date, stage.send_time_window_end)
        window_end = tz.localize(window_end)
        
        if next_datetime > window_end:
            # Move to next day
            next_datetime += timedelta(days=1)
            next_time = datetime.combine(next_datetime.date(), stage.send_time_window_start)
            next_datetime = tz.localize(next_time)
        
        return next_datetime
    
    def can_send_today(self, campaign):
        """Check if we can send more emails today based on warm-up limits"""
        # Get daily limit based on warm-up week
        daily_limit = WarmupService.get_daily_limit(campaign.warmup_week)
        
        # Check today's sends
        from django.utils import timezone
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_sent = OutreachEmail.objects.filter(
            sequence_stage__campaign=campaign,
            sent_at__gte=today_start,
            status__in=['sent', 'delivered', 'replied']
        ).count()
        
        return today_sent < daily_limit, daily_limit - today_sent
    
    def check_weekly_volume(self, campaign):
        """Check and reset weekly volume if needed"""
        from django.utils import timezone
        
        if not campaign.week_reset_at:
            campaign.week_reset_at = timezone.now()
            campaign.current_week_volume = 0
            campaign.save()
            return True
        
        # Check if it's been a week
        days_since_reset = (timezone.now() - campaign.week_reset_at).days
        if days_since_reset >= 7:
            # Reset weekly counter
            campaign.week_reset_at = timezone.now()
            campaign.current_week_volume = 0
            
            # Advance warm-up week if applicable
            if campaign.status == 'warming':
                WarmupService.advance_week(campaign)
            
            campaign.save()
            logger.info(f"Weekly volume reset for campaign {campaign.name}")
        
        # Check if we've hit weekly limit
        weekly_limit = WarmupService.get_weekly_limit(campaign.warmup_week)
        return campaign.current_week_volume < weekly_limit
    
    def render_template(self, template, contact):
        """Render email template with contact variables"""
        variables = {
            'first_name': contact.first_name,
            'last_name': contact.last_name,
            'organization': contact.prospect.organization_name,
            'title': contact.title,
            'industry': contact.prospect.industry,
        }
        
        rendered = template
        for key, value in variables.items():
            placeholder = f'{{{{{key}}}}}'
            rendered = rendered.replace(placeholder, str(value) if value else '')
        
        return rendered
    
    def is_suppressed(self, email):
        """Check if email is on suppression list"""
        return SuppressionList.objects.filter(email__iexact=email).exists()
    
    def should_escalate(self, email_content, engagement_stage):
        """
        Determine if a reply requires human escalation
        Returns: (should_escalate, reason)
        """
        content_lower = email_content.lower() if email_content else ''
        
        # Government official detection
        government_titles = [
            'minister', 'permanent secretary', 'commissioner', 
            'director general', 'permanent secretary', 'ambassador',
            'honorable', 'hon.', 'mp', 'member of parliament'
        ]
        for title in government_titles:
            if title in content_lower:
                return True, "Government official engagement"
        
        # Legal/compliance keywords
        legal_keywords = ['legal', 'compliance', 'procurement', 'rfp', 'tender', 'contract']
        for keyword in legal_keywords:
            if keyword in content_lower:
                return True, f"Legal/compliance topic: {keyword}"
        
        # Investor keywords
        investor_keywords = ['investor', 'investment', 'vc', 'venture capital', 'due diligence']
        for keyword in investor_keywords:
            if keyword in content_lower:
                return True, f"Investor-level engagement: {keyword}"
        
        # Technical integration at early stage
        technical_keywords = ['api', 'integration', 'technical', 'infrastructure', 'deployment']
        if engagement_stage <= 2:  # Early stages
            for keyword in technical_keywords:
                if keyword in content_lower:
                    return True, f"Technical question at early stage: {keyword}"
        
        # Negative sentiment indicators
        negative_indicators = ['not interested', 'stop', 'unsubscribe', 'remove', 'spam']
        for indicator in negative_indicators:
            if indicator in content_lower:
                return True, f"Negative response indicator: {indicator}"
        
        return False, None
    
    def process_reply(self, outreach_email, reply_content, received_at):
        """Process an incoming reply"""
        from django.utils import timezone
        
        # Update email status
        outreach_email.status = 'replied'
        outreach_email.replied_at = received_at
        outreach_email.reply_body = reply_content
        outreach_email.save()
        
        # Check for escalation
        should_escalate, escalation_reason = self.should_escalate(
            reply_content, 
            outreach_email.engagement_stage
        )
        
        if should_escalate:
            outreach_email.escalated_to_human = True
            outreach_email.escalated_at = timezone.now()
            outreach_email.escalation_reason = escalation_reason
            outreach_email.save()
            logger.info(f"Email escalated: {escalation_reason}")
        
        # Create engagement record
        Engagement.objects.create(
            outreach_email=outreach_email,
            engagement_type='reply',
            raw_content=reply_content,
            requires_response=should_escalate,
            escalated=should_escalate
        )
        
        # Advance engagement stage if appropriate
        current_stage = outreach_email.engagement_stage
        if current_stage < 6 and not should_escalate:
            outreach_email.engagement_stage = min(current_stage + 1, 6)
            outreach_email.save()
        
        return should_escalate, escalation_reason
    
    def send_sequence_email(self, contact, stage):
        """
        Send an email for a specific sequence stage
        Returns: (success, outreach_email, error_message)
        """
        # Check suppression
        if self.is_suppressed(contact.email):
            logger.info(f"Skipping suppressed email: {contact.email}")
            return False, None, "Email suppressed"
        
        # Check if contact opted out
        if contact.do_not_contact:
            logger.info(f"Skipping opted-out contact: {contact.email}")
            return False, None, "Contact opted out"
        
        # Check campaign limits
        campaign = stage.campaign
        can_send, remaining = self.can_send_today(campaign)
        if not can_send:
            logger.info(f"Daily limit reached for campaign {campaign.name}")
            return False, None, "Daily limit reached"
        
        if not self.check_weekly_volume(campaign):
            logger.info(f"Weekly limit reached for campaign {campaign.name}")
            return False, None, "Weekly limit reached"
        
        # Check reputation
        health = ReputationMonitor.check_campaign_health(campaign)
        if not health['healthy']:
            logger.warning(f"Campaign health check failed: {health['recommendation']}")
            return False, None, health['recommendation']
        
        # Render templates
        subject = self.render_template(stage.subject_template, contact)
        body = self.render_template(stage.body_template, contact)
        
        # Add unsubscribe link
        if stage.include_unsubscribe:
            body += f"\n\n---\nTo unsubscribe, reply with 'UNSUBSCRIBE' or contact us."
        
        # Create HTML version
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                {body.replace(chr(10), '<br>')}
            </div>
        </body>
        </html>
        """
        
        # Create OutreachEmail record
        with transaction.atomic():
            outreach_email = OutreachEmail.objects.create(
                sequence_stage=stage,
                contact=contact,
                prospect=contact.prospect,
                subject=subject,
                body=body,
                body_rendered=body_html,
                scheduled_at=timezone.now(),
                status='sending'
            )
            
            # Send via SES
            result = self.ses_service.send_email(
                to_email=contact.email,
                subject=subject,
                body_text=body,
                body_html=body_html,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@javisone.com'),
                reply_to=getattr(settings, 'REPLY_TO_EMAIL', 'inquiries@javisone.com'),
                configuration_set=getattr(settings, 'AWS_SES_CONFIGURATION_SET', None),
                message_tags={
                    'campaign_id': str(campaign.id),
                    'stage': str(stage.stage_number),
                    'email_id': str(outreach_email.id)
                }
            )
            
            if result['success']:
                outreach_email.status = 'sent'
                outreach_email.sent_at = timezone.now()
                outreach_email.message_id = result['message_id']
                outreach_email.save()
                
                # Update campaign volume
                campaign.current_week_volume += 1
                campaign.save(update_fields=['current_week_volume'])
                
                # Update contact
                contact.emails_sent += 1
                contact.last_contacted_at = timezone.now()
                contact.save()
                
                logger.info(f"Email sent to {contact.email}, MessageId: {result['message_id']}")
                return True, outreach_email, None
            else:
                outreach_email.status = 'failed'
                outreach_email.error_message = result['error']
                outreach_email.save()
                
                logger.error(f"Failed to send email to {contact.email}: {result['error']}")
                return False, outreach_email, result['error']


def queue_sequence_stages():
    """
    Background task: Queue emails for sequence stages
    Called daily by Celery
    """
    from django.utils import timezone
    
    logger.info("Starting sequence stage queueing...")
    
    # Get active campaigns
    campaigns = Campaign.objects.filter(status='active')
    
    for campaign in campaigns:
        sequencer = EmailSequencer()
        
        # Get Stage 1 contacts (cold outreach)
        stage_1 = campaign.stages.filter(stage_number=1, is_active=True).first()
        if stage_1:
            # Find qualified prospects who haven't been contacted
            prospects = Prospect.objects.filter(
                status='qualified',
                contacts__is_primary_contact=True,
                contacts__do_not_contact=False
            ).exclude(
                outreach_emails__sequence_stage__campaign=campaign
            ).distinct()[:sequencer.get_daily_limit(campaign)]
            
            for prospect in prospects:
                contact = prospect.contacts.filter(is_primary_contact=True).first()
                if contact and not sequencer.is_suppressed(contact.email):
                    success, email, error = sequencer.send_sequence_email(contact, stage_1)
                    if not success and error == "Daily limit reached":
                        break
        
        # Handle stage progression (Stage 2+, for contacts who haven't replied)
        for stage in campaign.stages.filter(stage_number__gt=1, is_active=True):
            previous_stage = campaign.stages.filter(stage_number=stage.stage_number - 1).first()
            if not previous_stage:
                continue
            
            # Find emails from previous stage that are due for follow-up
            due_date = timezone.now() - timedelta(days=stage.delay_days)
            
            previous_emails = OutreachEmail.objects.filter(
                sequence_stage=previous_stage,
                status='sent',  # No reply received
                sent_at__lte=due_date
            ).exclude(
                contact__outreach_emails__sequence_stage=stage  # Don't send duplicate
            )
            
            for prev_email in previous_emails:
                # Check if we should auto-advance or require reply
                if stage.require_reply_to_advance:
                    continue  # Skip, human needs to review
                
                contact = prev_email.contact
                success, email, error = sequencer.send_sequence_email(contact, stage)
                if not success and error == "Daily limit reached":
                    break
    
    logger.info("Sequence stage queueing complete")
