from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend

from .models import EmergencyService, ServiceReview, PoliceInteraction, SafetyTip
from .serializers import (
    EmergencyServiceSerializer,
    ServiceReviewSerializer,
    PoliceInteractionSerializer,
    SafetyTipSerializer
)


class EmergencyServiceViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for emergency services"""
    queryset = EmergencyService.objects.filter(is_verified=True)
    serializer_class = EmergencyServiceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['service_type', 'county', 'is_24_7']
    search_fields = ['name', 'address', 'county']
    
    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """Find nearby emergency services"""
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        service_type = request.query_params.get('type')
        radius = request.query_params.get('radius', 20)  # Default 20km
        
        if not lat or not lng:
            return Response(
                {'detail': 'Latitude and longitude are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user_location = Point(float(lng), float(lat), srid=4326)
            
            # Start with base queryset
            queryset = EmergencyService.objects.filter(is_verified=True)
            
            # Filter by service type if provided
            if service_type:
                queryset = queryset.filter(service_type=service_type)
            
            # Filter by distance
            services = queryset.filter(
                location__distance_lte=(user_location, float(radius) * 1000)
            ).annotate(
                distance=Distance('location', user_location)
            ).order_by('distance')[:10]  # Limit to 10 nearest services
            
            serializer = self.get_serializer(services, many=True)
            return Response(serializer.data)
        except (ValueError, TypeError) as e:
            return Response(
                {'detail': 'Invalid coordinates.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def directions(self, request, pk=None):
        """Get directions to service location"""
        service = self.get_object()
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        
        if not lat or not lng:
            return Response(
                {'detail': 'Current location is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # TODO: Integrate with Google Maps Directions API
        # For now, return coordinates
        return Response({
            'service': {
                'name': service.name,
                'address': service.address,
                'coordinates': {
                    'lat': service.location.y,
                    'lng': service.location.x
                }
            },
            'current_location': {
                'lat': lat,
                'lng': lng
            }
        })


class ServiceReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for service reviews"""
    serializer_class = ServiceReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        service_id = self.request.query_params.get('service')
        if service_id:
            return ServiceReview.objects.filter(service_id=service_id)
        return ServiceReview.objects.all()
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PoliceInteractionViewSet(viewsets.ModelViewSet):
    """ViewSet for police interaction reports"""
    queryset = PoliceInteraction.objects.all()
    serializer_class = PoliceInteractionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['interaction_type', 'verified']
    search_fields = ['description', 'police_station', 'address']
    
    def perform_create(self, serializer):
        if self.request.user.is_authenticated and not serializer.validated_data.get('anonymous'):
            serializer.save(reporter=self.request.user)
        else:
            serializer.save()


class SafetyTipViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for safety tips"""
    queryset = SafetyTip.objects.filter(is_active=True)
    serializer_class = SafetyTipSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'severity']
    
    @action(detail=True, methods=['post'])
    def view(self, request, pk=None):
        """Increment view count"""
        tip = self.get_object()
        tip.views_count += 1
        tip.save()
        return Response({'views': tip.views_count})from django.shortcuts import render

# Create your views here.
