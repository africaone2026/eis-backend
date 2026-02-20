from django.db import models
from django.contrib.auth.models import User
from leads.models import PilotApplication


class LeadActivity(models.Model):
    """
    Track all interactions with a lead.
    """
    ACTIVITY_TYPES = [
        ('email_sent', 'Email Sent'),
        ('email_received', 'Email Received'),
        ('call_made', 'Call Made'),
        ('call_received', 'Call Received'),
        ('status_changed', 'Status Changed'),
        ('note_added', 'Note Added'),
        ('assigned', 'Lead Assigned'),
        ('file_uploaded', 'File Uploaded'),
        ('meeting_scheduled', 'Meeting Scheduled'),
        ('meeting_completed', 'Meeting Completed'),
        ('reminder_sent', 'Reminder Sent'),
        ('follow_up', 'Follow Up'),
    ]
    
    lead = models.ForeignKey(
        PilotApplication,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    description = models.TextField()
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Lead Activity'
        verbose_name_plural = 'Lead Activities'
    
    def __str__(self):
        return f"{self.lead.organization_name} - {self.get_activity_type_display()}"
