from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Prospect, Contact, Campaign, SequenceStage,
    OutreachEmail, Engagement, SuppressionList
)


@admin.register(Prospect)
class ProspectAdmin(admin.ModelAdmin):
    list_display = [
        'organization_name', 'industry', 'country', 'company_size',
        'complexity_score', 'archetype', 'status', 'created_at'
    ]
    list_filter = ['status', 'archetype', 'industry', 'country', 'company_size']
    search_fields = ['organization_name', 'website', 'notes']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Organization', {
            'fields': ('organization_name', 'industry', 'website', 'company_size')
        }),
        ('Location', {
            'fields': ('country', 'city')
        }),
        ('Scoring', {
            'fields': ('complexity_score', 'multi_region', 'reporting_intensity')
        }),
        ('Classification', {
            'fields': ('archetype', 'decision_authority', 'status')
        }),
        ('Source', {
            'fields': ('source', 'source_url', 'discovered_at')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 'prospect', 'title', 'seniority_level',
        'email', 'email_verified', 'is_primary_contact', 'do_not_contact'
    ]
    list_filter = ['seniority_level', 'email_verified', 'is_primary_contact', 'do_not_contact']
    search_fields = ['first_name', 'last_name', 'email', 'title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Name'


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'status', 'max_emails_per_week', 'current_week_volume',
        'warmup_week', 'start_date', 'created_by'
    ]
    list_filter = ['status', 'warmup_week']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    actions = ['activate_campaign', 'pause_campaign']
    
    def activate_campaign(self, request, queryset):
        queryset.update(status='active')
    activate_campaign.short_description = "Activate selected campaigns"
    
    def pause_campaign(self, request, queryset):
        queryset.update(status='paused')
    pause_campaign.short_description = "Pause selected campaigns"


@admin.register(SequenceStage)
class SequenceStageAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'stage_number', 'name', 'delay_days', 'is_active']
    list_filter = ['is_active', 'require_reply_to_advance']
    search_fields = ['name', 'subject_template']
    ordering = ['campaign', 'stage_number']


@admin.register(OutreachEmail)
class OutreachEmailAdmin(admin.ModelAdmin):
    list_display = [
        'contact', 'subject_preview', 'status', 'engagement_stage',
        'sent_at', 'replied_at', 'escalated_to_human'
    ]
    list_filter = ['status', 'engagement_stage', 'escalated_to_human']
    search_fields = ['contact__email', 'subject', 'reply_body']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def subject_preview(self, obj):
        return obj.subject[:50] + '...' if len(obj.subject) > 50 else obj.subject
    subject_preview.short_description = 'Subject'
    
    actions = ['mark_escalated', 'mark_do_not_contact']
    
    def mark_escalated(self, request, queryset):
        queryset.update(escalated_to_human=True)
    mark_escalated.short_description = "Mark as escalated to human"
    
    def mark_do_not_contact(self, request, queryset):
        for email in queryset:
            email.contact.do_not_contact = True
            email.contact.save()
    mark_do_not_contact.short_description = "Mark contacts as do-not-contact"


@admin.register(Engagement)
class EngagementAdmin(admin.ModelAdmin):
    list_display = [
        'outreach_email', 'engagement_type', 'sentiment',
        'requires_response', 'escalated', 'captured_at'
    ]
    list_filter = ['engagement_type', 'sentiment', 'requires_response', 'escalated']
    readonly_fields = ['id', 'captured_at']


@admin.register(SuppressionList)
class SuppressionListAdmin(admin.ModelAdmin):
    list_display = ['email', 'domain', 'reason', 'created_at']
    list_filter = ['reason']
    search_fields = ['email', 'domain']
    readonly_fields = ['created_at']
