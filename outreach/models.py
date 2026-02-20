import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Prospect(models.Model):
    """Target organizations for outreach"""
    
    ARCHETYPE_CHOICES = [
        ('distributed_ops', 'Distributed Operations'),
        ('growth_efficiency', 'Growth & Capital Efficiency'),
        ('public_sector', 'Public Sector Oversight'),
    ]
    
    COMPANY_SIZE_CHOICES = [
        ('micro', '1-20'),
        ('small', '21-100'),
        ('medium', '101-500'),
        ('large', '500+'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('researching', 'Researching'),
        ('qualified', 'Qualified'),
        ('contacted', 'Contacted'),
        ('engaged', 'Engaged'),
        ('opportunity', 'Opportunity'),
        ('rejected', 'Rejected'),
        ('unsubscribed', 'Unsubscribed'),
    ]
    
    DECISION_AUTHORITY_CHOICES = [
        ('c_suite', 'C-Suite'),
        ('vp', 'VP/Director'),
        ('manager', 'Manager'),
        ('unknown', 'Unknown'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_name = models.CharField(max_length=255)
    industry = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='Uganda')
    city = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    company_size = models.CharField(max_length=20, choices=COMPANY_SIZE_CHOICES)
    
    # Scoring
    complexity_score = models.IntegerField(default=0, help_text='1-10 scale')
    multi_region = models.BooleanField(default=False)
    reporting_intensity = models.IntegerField(default=0, help_text='1-10 scale')
    
    # Classification
    archetype = models.CharField(max_length=20, choices=ARCHETYPE_CHOICES)
    decision_authority = models.CharField(max_length=20, choices=DECISION_AUTHORITY_CHOICES, default='unknown')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    
    # Source tracking
    source = models.CharField(max_length=100, help_text='e.g., LinkedIn, URSB, Ministry Directory')
    source_url = models.URLField(blank=True)
    discovered_at = models.DateTimeField(auto_now_add=True)
    
    # Metadata
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-complexity_score', 'organization_name']
        verbose_name = 'Prospect'
        verbose_name_plural = 'Prospects'
    
    def __str__(self):
        return f"{self.organization_name} ({self.country})"


class Contact(models.Model):
    """Individual contacts within prospects"""
    
    SENIORITY_CHOICES = [
        ('c_suite', 'C-Suite (CEO, CFO, COO, MD)'),
        ('vp_director', 'VP / Director'),
        ('senior_manager', 'Senior Manager'),
        ('manager', 'Manager'),
        ('other', 'Other'),
    ]
    
    VERIFICATION_STATUS = [
        ('unverified', 'Unverified'),
        ('verified', 'Verified'),
        ('bounced', 'Bounced'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prospect = models.ForeignKey(Prospect, on_delete=models.CASCADE, related_name='contacts')
    
    # Personal info
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    title = models.CharField(max_length=200)
    seniority_level = models.CharField(max_length=20, choices=SENIORITY_CHOICES)
    
    # Contact details
    email = models.EmailField()
    email_verified = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='unverified')
    phone = models.CharField(max_length=50, blank=True)
    linkedin_url = models.URLField(blank=True)
    
    # Role
    is_primary_contact = models.BooleanField(default=False)
    is_decision_maker = models.BooleanField(default=False)
    
    # Engagement tracking
    emails_sent = models.IntegerField(default=0)
    last_contacted_at = models.DateTimeField(null=True, blank=True)
    do_not_contact = models.BooleanField(default=False)
    
    # Metadata
    source = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['prospect', 'seniority_level', 'last_name']
        unique_together = ['prospect', 'email']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.prospect.organization_name}"


class Campaign(models.Model):
    """Outreach campaigns"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('warming', 'Domain Warm-up'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Targeting
    target_archetypes = models.JSONField(default=list, help_text='List of archetype codes')
    target_countries = models.JSONField(default=list)
    
    # Volume controls
    max_emails_per_week = models.IntegerField(default=50)
    current_week_volume = models.IntegerField(default=0)
    week_reset_at = models.DateTimeField(null=True, blank=True)
    
    # Scheduling
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    # Warm-up tracking
    warmup_week = models.IntegerField(default=0, help_text='Current warm-up week (0 = not started)')
    warmup_started_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class SequenceStage(models.Model):
    """Individual stages in an email sequence"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='stages')
    
    stage_number = models.IntegerField()
    name = models.CharField(max_length=100)
    
    # Templates
    subject_template = models.CharField(max_length=300)
    body_template = models.TextField(help_text='Use {{first_name}}, {{organization}}, {{title}} variables')
    
    # Timing
    delay_days = models.IntegerField(default=0, help_text='Days after previous stage')
    send_time_window_start = models.TimeField(default='09:00')
    send_time_window_end = models.TimeField(default='11:00')
    
    # Behavior
    require_reply_to_advance = models.BooleanField(default=False, help_text='If true, sequence pauses until reply')
    auto_advance_on_no_reply = models.BooleanField(default=True, help_text='Auto-advance if no reply after delay_days')
    
    # Content rules
    include_unsubscribe = models.BooleanField(default=True)
    track_opens = models.BooleanField(default=True)
    track_clicks = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['campaign', 'stage_number']
        unique_together = ['campaign', 'stage_number']
    
    def __str__(self):
        return f"{self.campaign.name} - Stage {self.stage_number}"


class OutreachEmail(models.Model):
    """Individual emails sent to contacts"""
    
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('bounced', 'Bounced'),
        ('complained', 'Complained'),
        ('replied', 'Replied'),
        ('failed', 'Failed'),
    ]
    
    ENGAGEMENT_STAGE_CHOICES = [
        (1, 'Cold Outreach'),
        (2, 'Curious Response'),
        (3, 'Qualified Interest'),
        (4, 'Alignment Call Scheduled'),
        (5, 'Pilot Discussion'),
        (6, 'Proposal Phase'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    sequence_stage = models.ForeignKey(SequenceStage, on_delete=models.CASCADE, related_name='emails')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='outreach_emails')
    prospect = models.ForeignKey(Prospect, on_delete=models.CASCADE, related_name='outreach_emails')
    
    # Content
    subject = models.CharField(max_length=300)
    body = models.TextField()
    body_rendered = models.TextField(help_text='Final rendered HTML')
    
    # Sending
    scheduled_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # AWS SES tracking
    message_id = models.CharField(max_length=200, blank=True, help_text='AWS SES Message ID')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    
    # Engagement tracking
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    reply_body = models.TextField(blank=True)
    
    # Engagement stage (1-6)
    engagement_stage = models.IntegerField(choices=ENGAGEMENT_STAGE_CHOICES, default=1)
    
    # Human escalation
    escalated_to_human = models.BooleanField(default=False)
    escalated_at = models.DateTimeField(null=True, blank=True)
    escalation_reason = models.TextField(blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_emails')
    
    # Error tracking
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Email to {self.contact} - {self.subject[:50]}"


class Engagement(models.Model):
    """Track replies, bounces, opens, clicks"""
    
    TYPE_CHOICES = [
        ('reply', 'Reply'),
        ('bounce', 'Bounce'),
        ('complaint', 'Complaint'),
        ('open', 'Open'),
        ('click', 'Click'),
        ('forward', 'Forward'),
    ]
    
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
        ('unknown', 'Unknown'),
    ]
    
    OBJECTION_CHOICES = [
        ('none', 'None'),
        ('already_have_dashboards', 'Already Have Dashboards'),
        ('internal_reporting', 'Internal Reporting'),
        ('send_more_info', 'Send More Information'),
        ('no_budget', 'No Budget'),
        ('not_interested', 'Not Interested'),
        ('timing', 'Bad Timing'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    outreach_email = models.ForeignKey(OutreachEmail, on_delete=models.CASCADE, related_name='engagements')
    
    engagement_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    captured_at = models.DateTimeField(auto_now_add=True)
    
    # Content (for replies)
    raw_content = models.TextField(blank=True)
    processed_content = models.TextField(blank=True)
    
    # Analysis
    sentiment = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, default='unknown')
    objection_category = models.CharField(max_length=30, choices=OBJECTION_CHOICES, default='none')
    
    # Flags
    requires_response = models.BooleanField(default=False)
    escalated = models.BooleanField(default=False)
    human_reviewed = models.BooleanField(default=False)
    
    # Assignment
    human_assigned = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-captured_at']
    
    def __str__(self):
        return f"{self.engagement_type} from {self.outreach_email.contact}"


class SuppressionList(models.Model):
    """Global do-not-contact list"""
    
    REASON_CHOICES = [
        ('unsubscribe', 'Unsubscribe Request'),
        ('bounce', 'Hard Bounce'),
        ('complaint', 'Spam Complaint'),
        ('manual', 'Manual Add'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    domain = models.CharField(max_length=255, blank=True)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    source_campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Suppression List Entry'
        verbose_name_plural = 'Suppression List'
    
    def save(self, *args, **kwargs):
        # Extract domain from email
        if self.email and '@' in self.email:
            self.domain = self.email.split('@')[1]
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.email} ({self.reason})"
