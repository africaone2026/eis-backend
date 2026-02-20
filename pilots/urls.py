from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'admin/calls', views.AlignmentCallViewSet, basename='alignment-call')
router.register(r'admin/pilots', views.PilotEngagementViewSet, basename='pilot-engagement')

urlpatterns = [
    path('', include(router.urls)),
]
