from django.utils import timezone
from django.db.models import F
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from .models import Incident, IncidentCategory, IncidentMedia, IncidentVerification, SafetyAlert
from .utils import IncidentValidation, IncidentCategorySelector, MediaProcessor
from .filters import IncidentFilter
from .permissions import IsOwnerOrReadOnly, IsTrustedReporter
from .forms import IncidentReportForm

from .serializers import (
    IncidentSerializer, 
    IncidentCreateSerializer,
    IncidentCategorySerializer,
    IncidentVerificationSerializer,
    SafetyAlertSerializer
)

import json

class IncidentViewSet(viewsets.ModelViewSet):
    """ViewSet for incidents"""
    queryset = Incident.objects.filter(status__in=['reported', 'verified', 'investigating'])
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = IncidentFilter
    search_fields = ['title', 'description', 'address']
    ordering_fields = ['created_at', 'severity', 'verification_count']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return IncidentCreateSerializer
        return IncidentSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by location if provided
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')
        radius = self.request.query_params.get('radius', 10)  # Default 10km
        
        if lat and lng:
            try:
                user_location = Point(float(lng), float(lat), srid=4326)
                queryset = queryset.filter(
                    location__distance_lte=(user_location, radius * 1000)  # Convert km to meters
                ).annotate(
                    distance=Distance('location', user_location)
                ).order_by('distance')
            except (ValueError, TypeError):
                pass
        
        # Filter by date range
        days = self.request.query_params.get('days')
        if days:
            try:
                days = int(days)
                cutoff_date = timezone.now() - timezone.timedelta(days=days)
                queryset = queryset.filter(created_at__gte=cutoff_date)
            except ValueError:
                pass
        
        return queryset
    
    def perform_create(self, serializer):
        """Set reporter for new incidents"""
        if self.request.user.is_authenticated and not serializer.validated_data.get('anonymous'):
            serializer.save(reporter=self.request.user)
        else:
            serializer.save()
        
        # Auto-verify if user is trusted reporter
        incident = serializer.instance
        if self.request.user.is_authenticated and self.request.user.is_trusted_reporter:
            incident.verify(self.request.user)
            incident.save()
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def verify(self, request, pk=None):
        """Verify an incident"""
        incident = self.get_object()
        
        # Check if already verified by this user
        if IncidentVerification.objects.filter(incident=incident, user=request.user).exists():
            return Response(
                {'detail': 'You have already verified this incident.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        verification = IncidentVerification.objects.create(
            incident=incident,
            user=request.user,
            is_verified=True
        )
        
        # Update incident verification count
        incident.verification_count += 1
        if incident.verification_count >= 3 and not incident.verified:
            incident.verify(request.user)
        incident.save()
        
        return Response({'status': 'Incident verified successfully'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def dispute(self, request, pk=None):
        """Dispute an incident as false"""
        incident = self.get_object()
        
        # Check if already disputed by this user
        existing = IncidentVerification.objects.filter(
            incident=incident, 
            user=request.user,
            is_verified=False
        ).exists()
        
        if existing:
            return Response(
                {'detail': 'You have already disputed this incident.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        verification = IncidentVerification.objects.create(
            incident=incident,
            user=request.user,
            is_verified=False,
            comment=request.data.get('comment', '')
        )
        
        # Update false report count
        incident.false_report_count += 1
        if incident.false_report_count >= 3:
            incident.status = 'false_report'
        incident.save()
        
        return Response({'status': 'Incident disputed successfully'})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get incident statistics"""
        total = Incident.objects.count()
        verified = Incident.objects.filter(verified=True).count()
        critical = Incident.objects.filter(severity='critical').count()
        resolved = Incident.objects.filter(status='resolved').count()
        
        # Daily stats
        today = timezone.now().date()
        today_count = Incident.objects.filter(created_at__date=today).count()
        
        return Response({
            'total_incidents': total,
            'verified_incidents': verified,
            'critical_incidents': critical,
            'resolved_incidents': resolved,
            'today_incidents': today_count,
        })
    
    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """Get nearby incidents"""
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        radius = request.query_params.get('radius', 5)  # Default 5km
        
        if not lat or not lng:
            return Response(
                {'detail': 'Latitude and longitude are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user_location = Point(float(lng), float(lat), srid=4326)
            incidents = Incident.objects.filter(
                location__distance_lte=(user_location, float(radius) * 1000),
                status__in=['reported', 'verified', 'investigating']
            ).annotate(
                distance=Distance('location', user_location)
            ).order_by('distance')[:20]  # Limit to 20 nearest incidents
            
            serializer = self.get_serializer(incidents, many=True)
            return Response(serializer.data)
        except (ValueError, TypeError) as e:
            return Response(
                {'detail': 'Invalid coordinates.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class IncidentCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for incident categories"""
    queryset = IncidentCategory.objects.filter(is_active=True)
    serializer_class = IncidentCategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class SafetyAlertViewSet(viewsets.ModelViewSet):
    """ViewSet for safety alerts"""
    queryset = SafetyAlert.objects.all()
    serializer_class = SafetyAlertSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['alert_type', 'severity']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTrustedReporter()]
        return super().get_permissions()
    
    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Send safety alert immediately"""
        alert = self.get_object()
        
        # TODO: Implement alert sending logic
        # This would integrate with SMS, email, and push notification services
        
        alert.sent_at = timezone.now()
        alert.save()
        
        return Response({'status': 'Alert sent successfully'})

# @login_required
def report_incident_view(request):
    if request.method == "POST":
        form = IncidentReportForm(request.POST, request.FILES)

        # Validate incident data first
        validation_errors = IncidentValidation.validate_incident_data(request.POST)
        if validation_errors:
            for field, error in validation_errors.items():
                form.add_error(field, error)
            return render(request, "incidents/report.html", {"form": form})

        # Check for spam
        if IncidentValidation.check_spam(request.user, request.POST):
            messages.error(request, "Your report looks like spam. Try again later.")
            return render(request, "incidents/report.html", {"form": form})

        if form.is_valid():
            # Get location
            lat = -0.42013
            lon = 36.9476
            point = Point(float(lon), float(lat), srid=4326) if lat and lon else None

            # Save incident
            incident = form.save(user=request.user, point=point, commit=False)

            # Assign category
            incident.category = IncidentCategorySelector.assign_category(incident)
            incident.save()

            # Process uploaded media files
            for f in request.FILES.getlist("media_files"):
                # Validate file
                file_errors = MediaProcessor.validate_file(f)
                if file_errors:
                    messages.warning(request, f"{f.name}: {', '.join(file_errors)}")
                    continue

                # Process image if image file
                if f.content_type.startswith("image/"):
                    processed_file = MediaProcessor.process_image(f, blur_faces=True)
                else:
                    processed_file = f  # leave videos/audio as-is

                # Save media record
                IncidentMedia.objects.create(
                    incident=incident,
                    file=processed_file,
                    file_type=f.content_type.split("/")[0],
                    uploaded_by=request.user
                )

            messages.success(request, "Incident reported successfully!")
            return redirect("incident_list")

    else:
        form = IncidentReportForm()

    return render(request, "incidents/report.html", {"form": form})

def incident_list_view(request):
    qs = Incident.objects.filter(
        status__in=["reported", "verified", "investigating"]
    )

    # Filters
    severity = request.GET.get("severity")
    incident_type = request.GET.get("incident_type")
    county = request.GET.get("county")

    if severity:
        qs = qs.filter(severity=severity)

    if incident_type:
        qs = qs.filter(incident_type=incident_type)

    if county:
        qs = qs.filter(county__iexact=county)

    # Pagination
    paginator = Paginator(qs, 9)  # 9 cards per page
    page_number = request.GET.get("page")
    incidents = paginator.get_page(page_number)

    context = {
        "incidents": incidents,
    }

    return render(request, "incidents/list.html", context)

def incident_detail_view(request, incident_id):
    incident = get_object_or_404(
        Incident,
        id=incident_id,
        status__in=["reported", "verified", "investigating", "resolved"]
    )

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to perform this action.")
            return redirect("login")

        action = request.POST.get("action")

        # Prevent duplicate actions
        if IncidentVerification.objects.filter(
            incident=incident,
            user=request.user
        ).exists():
            messages.warning(request, "You have already acted on this incident.")
            return redirect("incident_detail", incident_id=incident.id)

        # VERIFY INCIDENT
        if action == "verify":
            IncidentVerification.objects.create(
                incident=incident,
                user=request.user,
                is_verified=True
            )

            incident.verification_count += 1

            if incident.verification_count >= 3 and not incident.verified:
                incident.verify(request.user)

            incident.save()
            messages.success(request, "Incident verified successfully.")

        # MARK AS FALSE
        elif action == "dispute":
            IncidentVerification.objects.create(
                incident=incident,
                user=request.user,
                is_verified=False
            )

            incident.false_report_count += 1

            if incident.false_report_count >= 3:
                incident.status = "false_report"

            incident.save()
            messages.success(request, "Incident marked as disputed.")

        return redirect("incident_detail", incident_id=incident.id)

    context = {
        "incident": incident,
    }

    return render(request, "incidents/detail.html", context)
