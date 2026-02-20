from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import OutreachEmail, Engagement, SuppressionList
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Engagement)
def handle_engagement_signal(sender, instance, created, **kwargs):
    """
    Handle engagement events - auto-suppress on bounce/complaint
    """
    if not created:
        return
    
    if instance.engagement_type == 'bounce':
        # Add to suppression list
        email = instance.outreach_email.contact.email
        SuppressionList.objects.get_or_create(
            email=email,
            defaults={
                'reason': 'bounce',
                'source_campaign': instance.outreach_email.sequence_stage.campaign
            }
        )
        logger.info(f"Added {email} to suppression list due to bounce")
    
    elif instance.engagement_type == 'complaint':
        # Add to suppression list
        email = instance.outreach_email.contact.email
        SuppressionList.objects.get_or_create(
            email=email,
            defaults={
                'reason': 'complaint',
                'source_campaign': instance.outreach_email.sequence_stage.campaign
            }
        )
        
        # Also mark contact as do-not-contact
        contact = instance.outreach_email.contact
        contact.do_not_contact = True
        contact.save()
        
        logger.warning(f"SPAM COMPLAINT from {email} - contact suppressed")
