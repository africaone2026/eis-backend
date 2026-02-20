from django.db import models
from django.contrib.auth.models import User
import uuid

# Choices for the form fields
INDUSTRY_CHOICES = [
    ('Fintech', 'Fintech'),
    ('Manufacturing', 'Manufacturing'),
    ('Healthcare', 'Healthcare'),
    ('NGO', 'NGO'),
    ('Government Agency', 'Government Agency'),
    ('Religious Organization', 'Religious Organization'),
    ('Other', 'Other'),
]

SCOPE_CHOICES = [
    ('Single Location', 'Single Location'),
    ('Multi-Region', 'Multi-Region'),
    ('Multi-Country', 'Multi-Country'),
    ('National-Level', 'National-Level'),
]

CHALLENGE_CHOICES = [
    ('Fragmented Reporting', 'Fragmented Reporting'),
    ('KPI Visibility Gaps', 'KPI Visibility Gaps'),
    ('Risk & Compliance Oversight', 'Risk & Compliance Oversight'),
    ('Slow Decision Cycles', 'Slow Decision Cycles'),
    ('Operational Complexity', 'Operational Complexity'),
    ('Other', 'Other'),
]

TEAM_SIZE_CHOICES = [
    ('1-20', '1-20'),
    ('21-100', '21-100'),
    ('101-500', '101-500'),
    ('500+', '500+'),
]

PRIORITY_TIER_CHOICES = [
    ('hot', '🔥 Hot (Immediate)'),
    ('warm', '🔆 Warm (Same Day)'),
    ('cool', '❄️ Cool (Next Day)'),
    ('nurture', '🌱 Nurture (Automated)'),
]

STATUS_CHOICES = [
    ('pending', 'Pending Review'),
    ('reviewed', 'Reviewed'),
    ('call_scheduled', 'Call Scheduled'),
    ('call_completed', 'Call Completed'),
    ('pilot_active', 'Pilot Active'),
    ('converted', 'Converted'),
    ('rejected', 'Rejected'),
    ('nurture', 'Nurture'),
]


class PilotApplication(models.Model):
    """
    Captures form submissions from the landing page for the Executive Pilot program.
    Includes qualification scoring and priority tier assignment.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Organization Information
    organization_name = models.CharField(max_length=255)
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES)
    organizational_scope = models.CharField(max_length=50, choices=SCOPE_CHOICES)
    team_size = models.CharField(max_length=20, choices=TEAM_SIZE_CHOICES)
    
    # Challenge/Pain Point
    primary_challenge = models.CharField(max_length=50, choices=CHALLENGE_CHOICES)
    challenge_description = models.TextField(blank=True)
    
    # Contact Information
    sponsor_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    
    # Qualification Scoring
    qualification_score = models.IntegerField(default=0)
    priority_tier = models.CharField(
        max_length=10, 
        choices=PRIORITY_TIER_CHOICES, 
        default='nurture'
    )
    
    # File Attachment (Sample Report)
    sample_report = models.FileField(
        upload_to='pilot_reports/%Y/%m/',
        blank=True,
        null=True
    )
    
    # Status Workflow
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    alignment_call_scheduled = models.DateTimeField(null=True, blank=True)
    pilot_start_date = models.DateField(null=True, blank=True)
    
    # Tracking & Attribution
    utm_source = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Internal Notes
    internal_notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_leads'
    )
    
    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Pilot Application'
        verbose_name_plural = 'Pilot Applications'
        indexes = [
            models.Index(fields=['priority_tier', '-submitted_at']),
            models.Index(fields=['status', '-submitted_at']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.organization_name} - {self.sponsor_name} ({self.priority_tier})"
    
    def save(self, *args, **kwargs):
        # Calculate score and tier before saving
        from .scoring import calculate_score, get_tier
        self.qualification_score = calculate_score(self)
        self.priority_tier = get_tier(self.qualification_score)
        super().save(*args, **kwargs)
    
    @property
    def estimated_response_time(self):
        """Return estimated response time based on priority tier."""
        response_times = {
            'hot': 'Within 4 hours',
            'warm': 'Same business day',
            'cool': 'Next business day',
            'nurture': 'Automated sequence',
        }
        return response_times.get(self.priority_tier, 'Unknown')
    
    @property
    def score_breakdown(self):
        """Return a breakdown of how the score was calculated."""
        from .scoring import get_score_breakdown
        return get_score_breakdown(self)
