from django.contrib.gis.geos import Point, Polygon
from django.contrib.gis.db.models.functions import Distance
from django.db.models import Count, Avg, Q
from datetime import datetime, timedelta
import math
from typing import List, Dict, Tuple
import json

from incidents.models import Incident
from emergency.models import EmergencyService
from .models import SafetyZone


class SafetyScoreCalculator:
    """Calculate safety scores for locations"""
    
    @staticmethod
    def calculate_location_score(location: Point, radius_km: float = 5) -> Dict:
        """
        Calculate safety score for a location based on nearby incidents
        and emergency services
        """
        # Get incidents in radius
        incidents = Incident.objects.filter(
            location__distance_lte=(location, radius_km * 1000),
            created_at__gte=datetime.now() - timedelta(days=30)
        )
        
        # Get emergency services in radius
        services = EmergencyService.objects.filter(
            location__distance_lte=(location, radius_km * 1000),
            is_verified=True
        )
        
        # Calculate incident metrics
        total_incidents = incidents.count()
        critical_incidents = incidents.filter(severity='critical').count()
        verified_incidents = incidents.filter(verified=True).count()
        
        # Calculate service metrics
        police_count = services.filter(service_type='police').count()
        hospital_count = services.filter(service_type='hospital').count()
        fire_count = services.filter(service_type='fire').count()
        
        # Calculate base safety score (0-100)
        # More incidents = lower score, more services = higher score
        incident_score = max(0, 100 - (total_incidents * 5))
        service_score = min(30, (police_count * 10 + hospital_count * 8 + fire_count * 6))
        
        safety_score = min(100, max(0, incident_score + service_score))
        
        # Determine safety level
        if safety_score >= 80:
            safety_level = 'safe'
            color = '#28a745'  # Green
        elif safety_score >= 60:
            safety_level = 'moderate'
            color = '#ffc107'  # Yellow
        elif safety_score >= 40:
            safety_level = 'caution'
            color = '#fd7e14'  # Orange
        else:
            safety_level = 'danger'
            color = '#dc3545'  # Red
        
        return {
            'safety_score': round(safety_score, 1),
            'safety_level': safety_level,
            'color': color,
            'metrics': {
                'total_incidents': total_incidents,
                'critical_incidents': critical_incidents,
                'verified_incidents': verified_incidents,
                'police_stations': police_count,
                'hospitals': hospital_count,
                'fire_stations': fire_count,
            }
        }
    
    @staticmethod
    def generate_heatmap_data(bbox: Tuple[float, float, float, float], 
                             grid_size: int = 10) -> List[Dict]:
        """
        Generate heatmap data for a bounding box
        bbox: (min_lng, min_lat, max_lng, max_lat)
        """
        min_lng, min_lat, max_lng, max_lat = bbox
        
        heatmap_data = []
        lng_step = (max_lng - min_lng) / grid_size
        lat_step = (max_lat - min_lat) / grid_size
        
        for i in range(grid_size):
            for j in range(grid_size):
                cell_center_lng = min_lng + (i + 0.5) * lng_step
                cell_center_lat = min_lat + (j + 0.5) * lat_step
                
                cell_center = Point(cell_center_lng, cell_center_lat, srid=4326)
                
                # Calculate incidents in this cell (approx)
                cell_radius = math.sqrt(lng_step**2 + lat_step**2) / 2 * 100000
                
                incidents = Incident.objects.filter(
                    location__distance_lte=(cell_center, cell_radius),
                    created_at__gte=datetime.now() - timedelta(days=7)
                )
                
                intensity = min(1.0, incidents.count() / 10.0)  # Normalize to 0-1
                
                if intensity > 0:
                    heatmap_data.append({
                        'lat': cell_center_lat,
                        'lng': cell_center_lng,
                        'intensity': intensity,
                        'incident_count': incidents.count()
                    })
        
        return heatmap_data


class GeocodingUtils:
    """Geocoding utilities"""
    
    @staticmethod
    def reverse_geocode(lat: float, lng: float) -> Dict:
        """
        Reverse geocode coordinates to address
        TODO: Integrate with Google Maps Geocoding API
        """
        # Placeholder implementation
        return {
            'address': f'Near {lat:.6f}, {lng:.6f}',
            'county': 'Nairobi',  # Default
            'constituency': '',
            'ward': ''
        }
    
    @staticmethod
    def calculate_distance(point1: Point, point2: Point) -> float:
        """Calculate distance between two points in kilometers"""
        return point1.distance(point2) * 100  # Approximate conversion to km


class MapDataGenerator:
    """Generate map data for frontend"""
    
    @staticmethod
    def generate_incident_markers(incidents) -> List[Dict]:
        """Convert incidents to map markers"""
        markers = []
        
        icon_mapping = {
            'crime': 'shield-exclamation',
            'accident': 'car-crash',
            'hazard': 'triangle-exclamation',
            'checkpoint': 'shield-check',
            'sos': 'sos',
            'police_interaction': 'user-police',
            'other': 'exclamation-circle'
        }
        
        color_mapping = {
            'low': '#28a745',      # Green
            'medium': '#ffc107',   # Yellow
            'high': '#fd7e14',     # Orange
            'critical': '#dc3545'  # Red
        }
        
        for incident in incidents:
            markers.append({
                'id': str(incident.id),
                'type': 'incident',
                'title': incident.title,
                'lat': incident.location.y,
                'lng': incident.location.x,
                'icon': icon_mapping.get(incident.incident_type, 'exclamation-circle'),
                'color': color_mapping.get(incident.severity, '#ffc107'),
                'severity': incident.severity,
                'verified': incident.verified,
                'popup_content': f"""
                    <strong>{incident.title}</strong><br/>
                    <small>{incident.get_severity_display()}</small><br/>
                    <p>{incident.description[:100]}...</p>
                    <small>Reported: {incident.created_at.strftime('%Y-%m-%d %H:%M')}</small>
                """,
                'data': {
                    'category': incident.incident_type,
                    'reported_at': incident.created_at.isoformat(),
                    'address': incident.address
                }
            })
        
        return markers
    
    @staticmethod
    def generate_service_markers(services) -> List[Dict]:
        """Convert emergency services to map markers"""
        markers = []
        
        icon_mapping = {
            'police': 'shield-alt',
            'hospital': 'hospital',
            'fire': 'fire-extinguisher',
            'ambulance': 'ambulance',
            'rescue': 'life-ring',
            'clinic': 'clinic-medical',
            'pharmacy': 'pills',
            'helpline': 'phone-alt'
        }
        
        for service in services:
            markers.append({
                'id': str(service.id),
                'type': 'service',
                'title': service.name,
                'lat': service.location.y,
                'lng': service.location.x,
                'icon': icon_mapping.get(service.service_type, 'map-marker-alt'),
                'color': '#0066cc',  # Blue for services
                'popup_content': f"""
                    <strong>{service.name}</strong><br/>
                    <small>{service.get_service_type_display()}</small><br/>
                    <p>{service.address}</p>
                    <p>Phone: {service.phone_number}</p>
                    <small>Rating: {service.average_rating:.1f}/5</small>
                """,
                'data': {
                    'service_type': service.service_type,
                    'phone': service.phone_number,
                    'rating': service.average_rating
                }
            })
        
        return markers
