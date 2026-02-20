from rest_framework import serializers
from .models import AlignmentCall, PilotEngagement


class AlignmentCallSerializer(serializers.ModelSerializer):
    """
    Serializer for alignment calls.
    """
    outcome_display = serializers.CharField(source='get_outcome_display', read_only=True)
    attended_by_name = serializers.CharField(source='attended_by.get_full_name', read_only=True)
    lead_organization = serializers.CharField(source='lead.organization_name', read_only=True)
    
    class Meta:
        model = AlignmentCall
        fields = [
            'id', 'lead', 'lead_organization', 'scheduled_at',
            'duration_minutes', 'meeting_link', 'notes', 'outcome',
            'outcome_display', 'attended_by', 'attended_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PilotEngagementSerializer(serializers.ModelSerializer):
    """
    Serializer for pilot engagements.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    conversion_status_display = serializers.CharField(source='get_conversion_status_display', read_only=True)
    lead_organization = serializers.CharField(source='lead.organization_name', read_only=True)
    days_remaining = serializers.IntegerField(source='days_remaining', read_only=True)
    progress_percentage = serializers.IntegerField(source='progress_percentage', read_only=True)
    
    class Meta:
        model = PilotEngagement
        fields = [
            'id', 'lead', 'lead_organization', 'start_date', 'end_date',
            'weekly_briefs_delivered', 'kpis_configured', 'stakeholder_count',
            'status', 'status_display', 'conversion_status', 'conversion_status_display',
            'monthly_recurring_revenue', 'notes', 'days_remaining',
            'progress_percentage', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
