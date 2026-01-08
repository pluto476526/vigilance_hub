from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IncidentViewSet, IncidentCategoryViewSet, SafetyAlertViewSet

router = DefaultRouter()
router.register(r'incidents', IncidentViewSet, basename='incident')
router.register(r'categories', IncidentCategoryViewSet, basename='incident-category')
router.register(r'alerts', SafetyAlertViewSet, basename='safety-alert')

urlpatterns = [
    path('', include(router.urls)),
]
