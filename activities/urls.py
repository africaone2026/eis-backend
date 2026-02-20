from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'admin/activities', views.LeadActivityViewSet, basename='activity')

urlpatterns = [
    path('', include(router.urls)),
]
