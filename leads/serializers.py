from rest_framework import serializers
from .models import PilotApplication
from .scoring import get_score_breakdown


class PilotApplicationSerializer(serializers.ModelSerializer):
    """
    Full serializer for PilotApplication (used in admin API).
    """
    score_breakdown = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_tier_display = serializers.CharField(source='get_priority_tier_display', read_only=True)
    
    class Meta:
        model = PilotApplication
        fields = [
            'id', 'organization_name', 'industry', 'organizational_scope',
            'team_size', 'primary_challenge', 'challenge_description',
            'sponsor_name', 'email', 'phone', 'qualification_score',
            'priority_tier', 'priority_tier_display', 'sample_report',
            'status', 'status_display', 'submitted_at', 'reviewed_at',
            'alignment_call_scheduled', 'pilot_start_date', 'utm_source',
            'utm_campaign', 'ip_address', 'internal_notes', 'assigned_to',
            'score_breakdown'
        ]
        read_only_fields = [
            'id', 'qualification_score', 'priority_tier', 'submitted_at',
            'reviewed_at', 'ip_address', 'score_breakdown'
        ]
    
    def get_score_breakdown(self, obj):
        return get_score_breakdown(obj)


class PilotApplicationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new pilot applications from the public API.
    Only includes fields that should be submitted by applicants.
    """
    class Meta:
        model = PilotApplication
        fields = [
            'organization_name', 'industry', 'organizational_scope',
            'team_size', 'primary_challenge', 'challenge_description',
            'sponsor_name', 'email', 'phone', 'sample_report',
            'utm_source', 'utm_campaign'
        ]
    
    def validate_email(self, value):
        """Normalize email to lowercase."""
        return value.lower().strip()
    
    def validate_phone(self, value):
        """Basic phone validation - strip non-numeric characters."""
        return value.strip()


class PilotApplicationPublicResponseSerializer(serializers.ModelSerializer):
    """
    Serializer for public API responses (limited data exposed).
    """
    class Meta:
        model = PilotApplication
        fields = [
            'id', 'qualification_score', 'priority_tier',
            'submitted_at', 'status'
        ]


class PilotApplicationStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for checking application status (applicant portal).
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_tier_display = serializers.CharField(source='get_priority_tier_display', read_only=True)
    
    class Meta:
        model = PilotApplication
        fields = [
            'id', 'organization_name', 'status', 'status_display',
            'priority_tier', 'priority_tier_display', 'submitted_at',
            'alignment_call_scheduled', 'pilot_start_date'
        ]


class LeadPipelineSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for the kanban board view.
    """
    priority_tier_display = serializers.CharField(source='get_priority_tier_display', read_only=True)
    days_since_submission = serializers.SerializerMethodField()
    
    class Meta:
        model = PilotApplication
        fields = [
            'id', 'organization_name', 'industry', 'sponsor_name',
            'email', 'qualification_score', 'priority_tier',
            'priority_tier_display', 'status', 'submitted_at',
            'days_since_submission', 'assigned_to'
        ]
    
    def get_days_since_submission(self, obj):
        from django.utils import timezone
        return (timezone.now() - obj.submitted_at).days


class LeadListSerializer(serializers.ModelSerializer):
    """
    Serializer for lead list views.
    """
    priority_tier_display = serializers.CharField(source='get_priority_tier_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    
    class Meta:
        model = PilotApplication
        fields = [
            'id', 'organization_name', 'industry', 'sponsor_name',
            'email', 'phone', 'qualification_score', 'priority_tier',
            'priority_tier_display', 'status', 'status_display',
            'submitted_at', 'alignment_call_scheduled', 'assigned_to',
            'assigned_to_name'
        ]
