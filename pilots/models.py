from django.db import models
from django.contrib.auth.models import User
from leads.models import PilotApplication


class AlignmentCall(models.Model):
    """
    Schedule and track executive alignment calls.
    """
    CALL_OUTCOMES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
        ('rescheduled', 'Rescheduled'),
        ('cancelled', 'Cancelled'),
    ]
    
    lead = models.OneToOneField(
        PilotApplication,
        on_delete=models.CASCADE,
        related_name='alignment_call'
    )
    scheduled_at = models.DateTimeField()
    duration_minutes = models.IntegerField(default=30)
    meeting_link = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    outcome = models.CharField(
        max_length=20,
        choices=CALL_OUTCOMES,
        default='scheduled'
    )
    attended_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hosted_calls'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['scheduled_at']
        verbose_name = 'Alignment Call'
        verbose_name_plural = 'Alignment Calls'
    
    def __str__(self):
        return f"{self.lead.organization_name} - {self.scheduled_at}"


class PilotEngagement(models.Model):
    """
    Track active pilot customers.
    """
    PILOT_STATUS_CHOICES = [
        ('onboarding', 'Onboarding'),
        ('active', 'Active'),
        ('review', '30-Day Review'),
        ('extended', 'Extended'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    CONVERSION_CHOICES = [
        ('in_progress', 'In Progress'),
        ('converted', 'Converted to Paid'),
        ('churned', 'Churned'),
        ('nurture', 'Moved to Nurture'),
    ]
    
    lead = models.OneToOneField(
        PilotApplication,
        on_delete=models.CASCADE,
        related_name='pilot_engagement'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    weekly_briefs_delivered = models.IntegerField(default=0)
    kpis_configured = models.JSONField(default=list, blank=True)
    stakeholder_count = models.IntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=PILOT_STATUS_CHOICES,
        default='onboarding'
    )
    conversion_status = models.CharField(
        max_length=20,
        choices=CONVERSION_CHOICES,
        default='in_progress'
    )
    monthly_recurring_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
        verbose_name = 'Pilot Engagement'
        verbose_name_plural = 'Pilot Engagements'
    
    def __str__(self):
        return f"{self.lead.organization_name} - {self.status}"
    
    @property
    def days_remaining(self):
        """Calculate days remaining in pilot."""
        from datetime import date
        if self.end_date:
            return (self.end_date - date.today()).days
        return None
    
    @property
    def progress_percentage(self):
        """Calculate pilot progress percentage."""
        from datetime import date
        if self.start_date and self.end_date:
            total_days = (self.end_date - self.start_date).days
            if total_days <= 0:
                return 100
            elapsed = (date.today() - self.start_date).days
            return min(100, max(0, int((elapsed / total_days) * 100)))
        return 0
