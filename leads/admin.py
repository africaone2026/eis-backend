from django.contrib import admin
from django.utils.html import format_html
from .models import PilotApplication
from .scoring import get_score_breakdown


@admin.register(PilotApplication)
class PilotApplicationAdmin(admin.ModelAdmin):
    """
    Custom admin interface for Pilot Applications.
    Includes kanban board view, scoring display, and quick actions.
    """
    list_display = [
        'organization_name',
        'priority_tier_badge',
        'qualification_score_display',
        'sponsor_name',
        'industry',
        'status_badge',
        'submitted_at',
        'assigned_to',
    ]
    
    list_filter = [
        'priority_tier',
        'status',
        'industry',
        'organizational_scope',
        'submitted_at',
    ]
    
    search_fields = [
        'organization_name',
        'sponsor_name',
        'email',
        'phone',
    ]
    
    readonly_fields = [
        'id',
        'qualification_score',
        'priority_tier',
        'submitted_at',
        'ip_address',
        'user_agent',
        'score_breakdown_display',
    ]
    
    fieldsets = (
        ('Organization Information', {
            'fields': (
                'organization_name',
                'industry',
                'organizational_scope',
                'team_size',
            )
        }),
        ('Challenge & Requirements', {
            'fields': (
                'primary_challenge',
                'challenge_description',
            )
        }),
        ('Contact Information', {
            'fields': (
                'sponsor_name',
                'email',
                'phone',
            )
        }),
        ('Qualification Scoring', {
            'fields': (
                'qualification_score',
                'priority_tier',
                'score_breakdown_display',
            ),
            'classes': ('wide',)
        }),
        ('File Upload', {
            'fields': ('sample_report',),
        }),
        ('Status & Workflow', {
            'fields': (
                'status',
                'reviewed_at',
                'alignment_call_scheduled',
                'pilot_start_date',
                'assigned_to',
            )
        }),
        ('Internal Notes', {
            'fields': ('internal_notes',),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': (
                'id',
                'utm_source',
                'utm_campaign',
                'ip_address',
                'user_agent',
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'mark_as_reviewed',
        'mark_as_call_scheduled',
        'mark_as_pilot_active',
        'assign_to_me',
    ]
    
    date_hierarchy = 'submitted_at'
    
    def priority_tier_badge(self, obj):
        """Display priority tier as a colored badge."""
        colors = {
            'hot': '#ff4757',
            'warm': '#ffa502',
            'cool': '#338dff',
            'nurture': '#747d8c',
        }
        color = colors.get(obj.priority_tier, '#747d8c')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: bold;">{}</span>',
            color,
            obj.get_priority_tier_display()
        )
    priority_tier_badge.short_description = 'Priority'
    
    def qualification_score_display(self, obj):
        """Display score with color coding."""
        if obj.qualification_score >= 80:
            color = '#ff4757'
        elif obj.qualification_score >= 60:
            color = '#ffa502'
        elif obj.qualification_score >= 40:
            color = '#338dff'
        else:
            color = '#747d8c'
        
        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 16px;">{}/100</span>',
            color,
            obj.qualification_score
        )
    qualification_score_display.short_description = 'Score'
    
    def status_badge(self, obj):
        """Display status as a colored badge."""
        colors = {
            'pending': '#ffa502',
            'reviewed': '#338dff',
            'call_scheduled': '#2ed573',
            'call_completed': '#1e90ff',
            'pilot_active': '#7bed9f',
            'converted': '#2ed573',
            'rejected': '#ff4757',
            'nurture': '#747d8c',
        }
        color = colors.get(obj.status, '#747d8c')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def score_breakdown_display(self, obj):
        """Display detailed score breakdown."""
        breakdown = get_score_breakdown(obj)
        
        html = '<div style="margin-top: 10px;">'
        html += f'<h4>Total Score: {breakdown["total_score"]}/{breakdown["max_possible"]} ({breakdown["tier"].upper()})</h4>'
        html += '<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">'
        html += '<tr style="background: #f5f5f5;"><th style="padding: 8px; text-align: left;">Criteria</th><th style="padding: 8px; text-align: left;">Value</th><th style="padding: 8px; text-align: center;">Score</th></tr>'
        
        for key, component in breakdown['components'].items():
            html += f'<tr style="border-bottom: 1px solid #eee;">'
            html += f'<td style="padding: 8px;"><strong>{key.replace("_", " ").title()}</strong></td>'
            html += f'<td style="padding: 8px;">{component["value"]}</td>'
            html += f'<td style="padding: 8px; text-align: center;">{component["score"]}/{component["max"]}</td>'
            html += '</tr>'
        
        html += '</table>'
        html += '</div>'
        
        return format_html(html)
    score_breakdown_display.short_description = 'Score Breakdown'
    
    # Actions
    @admin.action(description='Mark selected leads as Reviewed')
    def mark_as_reviewed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='reviewed', reviewed_at=timezone.now())
        self.message_user(request, f'{updated} lead(s) marked as reviewed.')
    
    @admin.action(description='Mark selected leads as Call Scheduled')
    def mark_as_call_scheduled(self, request, queryset):
        updated = queryset.update(status='call_scheduled')
        self.message_user(request, f'{updated} lead(s) marked as call scheduled.')
    
    @admin.action(description='Mark selected leads as Pilot Active')
    def mark_as_pilot_active(self, request, queryset):
        updated = queryset.update(status='pilot_active')
        self.message_user(request, f'{updated} lead(s) marked as pilot active.')
    
    @admin.action(description='Assign selected leads to me')
    def assign_to_me(self, request, queryset):
        updated = queryset.update(assigned_to=request.user)
        self.message_user(request, f'{updated} lead(s) assigned to you.')
    
    def get_queryset(self, request):
        """
        Optimize queryset with select_related.
        """
        return super().get_queryset(request).select_related('assigned_to')
