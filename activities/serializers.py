from rest_framework import serializers
from .models import LeadActivity


class LeadActivitySerializer(serializers.ModelSerializer):
    """
    Serializer for lead activities.
    """
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    performed_by_name = serializers.CharField(source='performed_by.get_full_name', read_only=True)
    
    class Meta:
        model = LeadActivity
        fields = [
            'id', 'lead', 'activity_type', 'activity_type_display',
            'description', 'performed_by', 'performed_by_name',
            'created_at', 'metadata'
        ]
        read_only_fields = ['id', 'created_at']


class LeadActivityCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating lead activities.
    """
    class Meta:
        model = LeadActivity
        fields = ['activity_type', 'description', 'metadata']
