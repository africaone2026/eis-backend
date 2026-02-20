from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'admin/leads', views.PilotApplicationViewSet, basename='lead')

urlpatterns = [
    path('', include(router.urls)),
    
    # Public endpoints
    path('pilot-applications/', views.create_pilot_application, name='create-pilot-application'),
    path('pilot-applications/<uuid:application_id>/status/', views.check_application_status, name='check-application-status'),
    
    # Admin dashboard
    path('admin/dashboard/stats/', views.dashboard_stats, name='dashboard-stats'),
]
