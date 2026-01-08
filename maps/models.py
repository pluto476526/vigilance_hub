from django.db import models
from django.contrib.gis.db import models as gis_models


class SafetyZone(models.Model):
    """Safety zones with calculated safety scores"""
    ZONE_TYPES = (
        ('neighborhood', 'Neighborhood'),
        ('ward', 'Ward'),
        ('constituency', 'Constituency'),
        ('county', 'County'),
        ('custom', 'Custom Zone'),
    )
    
    name = models.CharField(max_length=200)
    zone_type = models.CharField(max_length=20, choices=ZONE_TYPES)
    boundary = gis_models.PolygonField()
    
    # Safety metrics
    safety_score = models.FloatField(default=0.0)  # 0-100
    incident_count_24h = models.IntegerField(default=0)
    incident_count_7d = models.IntegerField(default=0)
    incident_count_30d = models.IntegerField(default=0)
    
    # Risk levels
    crime_risk = models.FloatField(default=0.0)  # 0-10
    accident_risk = models.FloatField(default=0.0)  # 0-10
    hazard_risk = models.FloatField(default=0.0)  # 0-10
    
    # Emergency services in zone
    police_stations = models.IntegerField(default=0)
    hospitals = models.IntegerField(default=0)
    fire_stations = models.IntegerField(default=0)
    
    # Metadata
    population = models.IntegerField(null=True, blank=True)
    area_sq_km = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_incident_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'safety_zones'
        indexes = [
            models.Index(fields=['zone_type', 'safety_score']),
            models.Index(fields=['boundary'], name='zone_boundary_idx'),
        ]
    
    def __str__(self):
        return f"{self.name} (Score: {self.safety_score})"


class HeatMapData(models.Model):
    """Heat map data for visualization"""
    zone = models.ForeignKey(SafetyZone, on_delete=models.CASCADE, related_name='heatmap_data')
    data_type = models.CharField(max_length=50)  # crime, accidents, etc.
    intensity = models.FloatField(default=0.0)  # 0-1
    data_points = models.JSONField(default=list)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    class Meta:
        db_table = 'heatmap_data'
    
    def __str__(self):
        return f"Heatmap: {self.zone.name} - {self.data_type}"


class MapMarker(models.Model):
    """Custom map markers"""
    MARKER_TYPES = (
        ('incident', 'Incident'),
        ('service', 'Emergency Service'),
        ('checkpoint', 'Police Checkpoint'),
        ('safe_zone', 'Safe Zone'),
        ('danger', 'High Danger Area'),
    )
    
    marker_type = models.CharField(max_length=20, choices=MARKER_TYPES)
    location = gis_models.PointField()
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, default='map-marker')
    color = models.CharField(max_length=20, default='#ff0000')
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'map_markers'
    
    def __str__(self):
        return f"{self.title} ({self.get_marker_type_display()})"
