from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_outreach_emails():
    """Send queued outreach emails - runs daily"""
    from outreach.sequencer import queue_sequence_stages
    logger.info("Starting outreach email sending task...")
    queue_sequence_stages()
    logger.info("Outreach email sending task complete")


@shared_task
def poll_email_replies():
    """Poll IMAP inbox for replies - runs every 15 minutes"""
    from outreach.imap_receiver import poll_inbox
    logger.info("Starting email reply polling task...")
    poll_inbox()
    logger.info("Email reply polling task complete")


@shared_task
def check_campaign_health():
    """Check campaign health and send alerts - runs daily"""
    from outreach.models import Campaign
    from outreach.services import ReputationMonitor
    from django.utils import timezone
    
    logger.info("Checking campaign health...")
    
    active_campaigns = Campaign.objects.filter(status='active')
    
    for campaign in active_campaigns:
        health = ReputationMonitor.check_campaign_health(campaign)
        
        if not health['healthy']:
            logger.warning(f"Campaign {campaign.name} health alert: {health['recommendation']}")
            
            # Auto-pause if critical
            if health['bounce_rate'] > 10 or health['complaint_rate'] > 0.5:
                campaign.status = 'paused'
                campaign.save()
                logger.critical(f"Campaign {campaign.name} AUTO-PAUSED due to critical metrics!")
                
                # TODO: Send notification to admin
    
    logger.info("Campaign health check complete")


@shared_task
def advance_warmup_weeks():
    """Advance warmup weeks every Monday"""
    from outreach.models import Campaign
    from outreach.services import WarmupService
    from django.utils import timezone
    
    logger.info("Checking warmup week advancement...")
    
    warming_campaigns = Campaign.objects.filter(status='warming')
    
    for campaign in warming_campaigns:
        if campaign.warmup_week < 7:
            new_week = WarmupService.advance_week(campaign)
            logger.info(f"Advanced campaign {campaign.name} to warmup week {new_week}")
    
    logger.info("Warmup week advancement complete")
