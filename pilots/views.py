from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import AlignmentCall, PilotEngagement
from .serializers import AlignmentCallSerializer, PilotEngagementSerializer


class AlignmentCallViewSet(viewsets.ModelViewSet):
    """
    ViewSet for alignment calls.
    """
    queryset = AlignmentCall.objects.all()
    serializer_class = AlignmentCallSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Filter calls by upcoming, past, etc.
        """
        queryset = AlignmentCall.objects.all()
        filter_type = self.request.query_params.get('filter')
        
        from django.utils import timezone
        
        if filter_type == 'upcoming':
            queryset = queryset.filter(scheduled_at__gte=timezone.now())
        elif filter_type == 'past':
            queryset = queryset.filter(scheduled_at__lt=timezone.now())
        
        return queryset
    
    def perform_create(self, serializer):
        """
        Set the attended_by field to the current user and update lead.
        """
        call = serializer.save(attended_by=self.request.user)
        
        # Update lead status and alignment call scheduled date
        lead = call.lead
        lead.alignment_call_scheduled = call.scheduled_at
        lead.status = 'call_scheduled'
        lead.save()
        
        # Log activity
        from activities.models import LeadActivity
        LeadActivity.objects.create(
            lead=lead,
            activity_type='meeting_scheduled',
            description=f'Alignment call scheduled for {call.scheduled_at}',
            performed_by=self.request.user,
            metadata={'meeting_link': call.meeting_link}
        )
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Mark a call as completed.
        """
        call = self.get_object()
        call.outcome = 'completed'
        call.save()
        
        # Update lead status
        lead = call.lead
        lead.status = 'call_completed'
        lead.save()
        
        return Response({'status': 'success'})


class PilotEngagementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for pilot engagements.
    """
    queryset = PilotEngagement.objects.all()
    serializer_class = PilotEngagementSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """
        Update pilot progress metrics.
        """
        engagement = self.get_object()
        
        if 'weekly_briefs_delivered' in request.data:
            engagement.weekly_briefs_delivered = request.data['weekly_briefs_delivered']
        
        if 'kpis_configured' in request.data:
            engagement.kpis_configured = request.data['kpis_configured']
        
        if 'stakeholder_count' in request.data:
            engagement.stakeholder_count = request.data['stakeholder_count']
        
        engagement.save()
        
        return Response({'status': 'success'})
    
    @action(detail=True, methods=['post'])
    def convert(self, request, pk=None):
        """
        Mark pilot as converted to paid.
        """
        engagement = self.get_object()
        engagement.conversion_status = 'converted'
        
        if 'monthly_recurring_revenue' in request.data:
            engagement.monthly_recurring_revenue = request.data['monthly_recurring_revenue']
        
        engagement.save()
        
        # Update lead status
        lead = engagement.lead
        lead.status = 'converted'
        lead.save()
        
        return Response({'status': 'success'})
