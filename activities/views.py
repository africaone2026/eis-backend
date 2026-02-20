from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import LeadActivity
from .serializers import LeadActivitySerializer, LeadActivityCreateSerializer


class LeadActivityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for lead activities.
    """
    queryset = LeadActivity.objects.all()
    serializer_class = LeadActivitySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Filter activities by lead_id if provided.
        """
        queryset = LeadActivity.objects.all()
        lead_id = self.request.query_params.get('lead_id')
        if lead_id:
            queryset = queryset.filter(lead_id=lead_id)
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return LeadActivityCreateSerializer
        return self.serializer_class
    
    def perform_create(self, serializer):
        """
        Set the performed_by field to the current user.
        """
        serializer.save(performed_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def timeline(self, request):
        """
        Get activity timeline for a specific lead.
        """
        lead_id = request.query_params.get('lead_id')
        if not lead_id:
            return Response(
                {'error': 'lead_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        activities = LeadActivity.objects.filter(lead_id=lead_id)[:50]
        serializer = self.get_serializer(activities, many=True)
        return Response(serializer.data)
