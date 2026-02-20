from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, throttle_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import AnonRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from .models import PilotApplication
from .serializers import (
    PilotApplicationSerializer,
    PilotApplicationCreateSerializer,
    PilotApplicationPublicResponseSerializer,
    PilotApplicationStatusSerializer,
    LeadPipelineSerializer,
    LeadListSerializer
)
from notifications.tasks import send_new_application_notification


class PilotApplicationRateThrottle(AnonRateThrottle):
    """
    Rate throttle for pilot application submissions.
    Default: 5 submissions per IP per hour.
    """
    rate = getattr(settings, 'RATE_LIMIT', '5/hour')
    
    def get_cache_key(self, request, view):
        # Use IP address as the cache key
        ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class PilotApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PilotApplication admin operations.
    Requires authentication.
    """
    queryset = PilotApplication.objects.all()
    serializer_class = PilotApplicationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority_tier', 'industry', 'assigned_to']
    search_fields = ['organization_name', 'sponsor_name', 'email']
    ordering_fields = ['submitted_at', 'qualification_score', 'reviewed_at']
    ordering = ['-submitted_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return LeadListSerializer
        return self.serializer_class
    
    @action(detail=False, methods=['get'])
    def pipeline(self, request):
        """
        Return leads grouped by status for the kanban board.
        """
        leads = self.get_queryset()
        serializer = LeadPipelineSerializer(leads, many=True)
        
        # Group by status
        pipeline = {
            'pending': [],
            'reviewed': [],
            'call_scheduled': [],
            'call_completed': [],
            'pilot_active': [],
            'converted': [],
            'rejected': [],
            'nurture': []
        }
        
        for lead in serializer.data:
            status_key = lead['status']
            if status_key in pipeline:
                pipeline[status_key].append(lead)
        
        return Response(pipeline)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """
        Update the status of a lead.
        """
        lead = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(PilotApplication.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        lead.status = new_status
        
        if new_status == 'reviewed' and not lead.reviewed_at:
            lead.reviewed_at = timezone.now()
        
        lead.save()
        
        # Log activity
        from activities.models import LeadActivity
        LeadActivity.objects.create(
            lead=lead,
            activity_type='status_changed',
            description=f'Status changed to {lead.get_status_display()}',
            performed_by=request.user,
            metadata={'old_status': lead.status, 'new_status': new_status}
        )
        
        return Response({'status': 'success', 'new_status': new_status})
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """
        Assign a lead to a user.
        """
        lead = self.get_object()
        user_id = request.data.get('user_id')
        
        from django.contrib.auth.models import User
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        old_assignee = lead.assigned_to
        lead.assigned_to = user
        lead.save()
        
        # Log activity
        from activities.models import LeadActivity
        LeadActivity.objects.create(
            lead=lead,
            activity_type='assigned',
            description=f'Lead assigned to {user.get_full_name() or user.username}',
            performed_by=request.user,
            metadata={
                'old_assignee': old_assignee.get_full_name() if old_assignee else None,
                'new_assignee': user.get_full_name() or user.username
            }
        )
        
        return Response({'status': 'success', 'assigned_to': user.get_full_name() or user.username})


# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = ['.pdf', '.xlsx', '.xls', '.csv', '.doc', '.docx', '.ppt', '.pptx']
ALLOWED_MIME_TYPES = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'text/csv',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.ms-powerpoint',
]


@api_view(['POST'])
@throttle_classes([PilotApplicationRateThrottle])
@permission_classes([AllowAny])
def create_pilot_application(request):
    """
    Public API endpoint for creating new pilot applications.
    Rate limited to 5 submissions per IP per hour.
    """
    # Get client IP and user agent
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Prepare data
    data = request.data.copy() if hasattr(request.data, 'copy') else request.data
    data['ip_address'] = ip_address
    data['user_agent'] = user_agent
    
    # Handle file upload
    if 'sample_report' in request.FILES:
        file = request.FILES['sample_report']
        
        # Validate file size (10MB limit)
        if file.size > settings.MAX_UPLOAD_SIZE:
            return Response(
                {'error': f'File size exceeds {settings.MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB limit'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file extension
        import os
        ext = os.path.splitext(file.name.lower())[1]
        if ext not in ALLOWED_EXTENSIONS:
            return Response(
                {'error': f'File type not allowed. Allowed types: PDF, Excel, CSV, Word, PowerPoint'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    serializer = PilotApplicationCreateSerializer(data=data)
    
    if serializer.is_valid():
        application = serializer.save()
        
        # Send notifications asynchronously
        send_new_application_notification.delay(str(application.id))
        
        # Return public response
        response_serializer = PilotApplicationPublicResponseSerializer(application)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def check_application_status(request, application_id):
    """
    Public API endpoint for applicants to check their application status.
    """
    try:
        application = PilotApplication.objects.get(id=application_id)
    except PilotApplication.DoesNotExist:
        return Response(
            {'error': 'Application not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = PilotApplicationStatusSerializer(application)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    Admin dashboard statistics.
    """
    from django.db.models import Count, Avg
    
    # Get counts by status
    status_counts = PilotApplication.objects.values('status').annotate(count=Count('id'))
    
    # Get counts by priority tier
    tier_counts = PilotApplication.objects.values('priority_tier').annotate(count=Count('id'))
    
    # Get recent leads (last 7 days)
    from datetime import timedelta
    last_7_days = timezone.now() - timedelta(days=7)
    recent_leads = PilotApplication.objects.filter(submitted_at__gte=last_7_days).count()
    
    # Get average qualification score
    avg_score = PilotApplication.objects.aggregate(avg_score=Avg('qualification_score'))['avg_score'] or 0
    
    # Hot leads requiring immediate attention
    hot_leads = PilotApplication.objects.filter(priority_tier='hot', status='pending').count()
    
    stats = {
        'total_leads': PilotApplication.objects.count(),
        'status_breakdown': {item['status']: item['count'] for item in status_counts},
        'tier_breakdown': {item['priority_tier']: item['count'] for item in tier_counts},
        'recent_leads_7d': recent_leads,
        'average_score': round(avg_score, 1),
        'hot_leads_pending': hot_leads,
        'calls_scheduled_this_week': PilotApplication.objects.filter(
            alignment_call_scheduled__gte=timezone.now(),
            alignment_call_scheduled__lte=timezone.now() + timedelta(days=7)
        ).count()
    }
    
    return Response(stats)


def get_client_ip(request):
    """
    Get the client IP address from the request.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
