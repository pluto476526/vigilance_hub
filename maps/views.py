from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
import json

from incidents.models import Incident
from emergency.models import EmergencyService
from .models import SafetyZone, MapMarker
from .utils import MapDataGenerator, SafetyScoreCalculator


def incident_map_view(request):
    """
    Render the safety map with incidents, services, and safety zones.
    """

    # Time range filter
    time_range = request.GET.get("time_range", "168")  # default 7 days

    if time_range != "all":
        since = timezone.now() - timedelta(hours=int(time_range))
        incident_qs = Incident.objects.filter(created_at__gte=since)
    else:
        incident_qs = Incident.objects.all()

    # Active incidents only
    incident_qs = incident_qs.filter(
        status__in=["reported", "verified", "investigating"]
    ).select_related()

    # Emergency services
    service_qs = EmergencyService.objects.filter(is_verified=True)

    # Safety zones
    safety_zones = SafetyZone.objects.all()

    # Convert to frontend marker format
    incident_markers = MapDataGenerator.generate_incident_markers(incident_qs)
    service_markers = MapDataGenerator.generate_service_markers(service_qs)

    # Optional: safety zone summary for overlays
    zones_data = [
        {
            "name": zone.name,
            "type": zone.zone_type,
            "safety_score": zone.safety_score,
            "crime_risk": zone.crime_risk,
            "accident_risk": zone.accident_risk,
            "hazard_risk": zone.hazard_risk,
        }
        for zone in safety_zones
    ]

    # Stats for quick cards
    stats = {
        "incident_count": incident_qs.count(),
        "verified_count": incident_qs.filter(verified=True).count(),
        "high_risk_count": incident_qs.filter(severity__in=["high", "critical"]).count(),
    }

    context = {
        "incident_markers": json.dumps(incident_markers),
        "service_markers": json.dumps(service_markers),
        "safety_zones": json.dumps(zones_data),
        "stats": stats,
    }

    return render(request, "incidents/map.html", context)
