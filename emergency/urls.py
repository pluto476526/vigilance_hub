from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmergencyServiceViewSet, 
    ServiceReviewViewSet,
    PoliceInteractionViewSet,
    SafetyTipViewSet
)

router = DefaultRouter()
router.register(r'services', EmergencyServiceViewSet, basename='emergency-service')
router.register(r'reviews', ServiceReviewViewSet, basename='service-review')
router.register(r'police-interactions', PoliceInteractionViewSet, basename='police-interaction')
router.register(r'safety-tips', SafetyTipViewSet, basename='safety-tip')

urlpatterns = [
    path('', include(router.urls)),
]
