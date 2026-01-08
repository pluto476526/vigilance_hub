from django.core.files.base import ContentFile
from django.utils import timezone
from django.db.models import Count, Q
from .models import Incident, IncidentCategory
from datetime import timedelta
from typing import List, Dict
from PIL import Image
import io
import re

class IncidentValidation:
    """Validate incident reports"""
    
    @staticmethod
    def validate_incident_data(data: Dict) -> Dict:
        """Validate incident submission data"""
        errors = {}
        
        # Title validation
        if not data.get('title') or len(data['title']) < 5:
            errors['title'] = 'Title must be at least 5 characters'
        
        # Description validation
        if not data.get('description') or len(data['description']) < 10:
            errors['description'] = 'Description must be at least 10 characters'
        
        # Location validation
        # if not data.get('location') or not data['location'].get('coordinates'):
        #     errors['location'] = 'Valid location is required'
        
        # Severity validation
        valid_severities = ['low', 'medium', 'high', 'critical']
        if data.get('severity') not in valid_severities:
            errors['severity'] = f'Severity must be one of: {", ".join(valid_severities)}'
        
        return errors
    
    @staticmethod
    def check_spam(user, data: Dict) -> bool:
        """Check if report might be spam"""
        # Check if same user reported similar incident recently
        recent_reports = Incident.objects.filter(
            Q(reporter=user) | Q(anonymous=False),
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        if recent_reports >= 5:
            return True
        
        # Check for suspicious patterns in description
        description = data.get('description', '').lower()
        spam_keywords = ['make money', 'earn cash', 'click here', 'http://', 'www.']
        
        for keyword in spam_keywords:
            if keyword in description:
                return True
        
        return False


class IncidentAnalyzer:
    """Analyze incident patterns"""
    
    @staticmethod
    def detect_patterns(location: str, time_range_days: int = 30) -> Dict:
        """
        Detect incident patterns in a location
        """
        cutoff_date = timezone.now() - timedelta(days=time_range_days)
        
        incidents = Incident.objects.filter(
            address__icontains=location,
            created_at__gte=cutoff_date
        )
        
        # Group by type and time
        by_type = incidents.values('incident_type').annotate(
            count=Count('id'),
            avg_severity=Count('id', filter=Q(severity='high') | Q(severity='critical'))
        ).order_by('-count')
        
        # Group by hour of day
        by_hour = incidents.extra(
            {'hour': "EXTRACT(HOUR FROM created_at)"}
        ).values('hour').annotate(count=Count('id')).order_by('hour')
        
        # Calculate trend
        recent = incidents.filter(created_at__gte=cutoff_date - timedelta(days=time_range_days))
        older = incidents.filter(
            created_at__gte=cutoff_date - timedelta(days=time_range_days * 2),
            created_at__lt=cutoff_date - timedelta(days=time_range_days)
        )
        
        trend = 'stable'
        if recent.count() > older.count() * 1.5:
            trend = 'increasing'
        elif recent.count() < older.count() * 0.7:
            trend = 'decreasing'
        
        return {
            'total_incidents': incidents.count(),
            'by_type': list(by_type),
            'by_hour': list(by_hour),
            'trend': trend,
            'hotspots': IncidentAnalyzer._find_hotspots(incidents)
        }
    
    @staticmethod
    def _find_hotspots(incidents, cluster_distance_km: float = 1) -> List[Dict]:
        """
        Find incident hotspots using simple clustering
        """
        if not incidents:
            return []
        
        # Simple grid-based clustering
        hotspots = []
        incidents_list = list(incidents)
        
        while incidents_list:
            incident = incidents_list.pop(0)
            cluster = [incident]
            
            # Find nearby incidents
            for other in incidents_list[:]:  # Copy for safe removal
                distance = incident.location.distance(other.location) * 100  # Approx km
                if distance < cluster_distance_km:
                    cluster.append(other)
                    incidents_list.remove(other)
            
            if len(cluster) >= 2:  # Only report clusters of 2+ incidents
                # Calculate cluster center
                avg_lat = sum(i.location.y for i in cluster) / len(cluster)
                avg_lng = sum(i.location.x for i in cluster) / len(cluster)
                
                hotspots.append({
                    'lat': avg_lat,
                    'lng': avg_lng,
                    'incident_count': len(cluster),
                    'severity': max(i.severity for i in cluster),
                    'types': list(set(i.incident_type for i in cluster))
                })
        
        return hotspots

class IncidentCategorySelector:
    """Automatically assign categories based on incident data and keywords"""

    KEYWORD_MAP = {
        "crime": ["robbery", "theft", "assault", "murder", "burglary", "crime"],
        "accident": ["accident", "crash", "collision", "injury", "car accident"],
        "hazard": ["hazard", "fire", "flood", "pollution", "spill", "hazardous"],
        "emergency": ["sos", "emergency", "critical", "help", "urgent"],
        "police_interaction": ["police", "checkpoint", "officer", "arrest"]
    }

    @staticmethod
    def assign_category(incident: Incident) -> IncidentCategory:
        """
        Assign category based on:
        1. Incident type
        2. Severity for critical emergencies
        3. Keywords in title or description
        4. Fallback to 'Other'
        """
        # 1. Based on type
        type_map = {
            'crime': 'Crime',
            'accident': 'Accident',
            'hazard': 'Hazard',
            'sos': 'Emergency',
            'police_interaction': 'Police Interaction'
        }

        if incident.incident_type in type_map:
            return IncidentCategory.objects.filter(name__iexact=type_map[incident.incident_type]).first()

        # 2. Critical emergency override
        if incident.severity in ('critical', 'high') and incident.incident_type == 'sos':
            return IncidentCategory.objects.filter(name__iexact='Emergency').first()

        # 3. Keyword matching
        text = f"{incident.title} {incident.description}".lower()
        for key, keywords in IncidentCategorySelector.KEYWORD_MAP.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', text):
                    category_name = key.capitalize() if key != "emergency" else "Emergency"
                    category = IncidentCategory.objects.filter(name__iexact=category_name).first()
                    if category:
                        return category

        # 4. Fallback
        return IncidentCategory.objects.filter(name__iexact='Other').first()


class MediaProcessor:
    """Process incident media files"""
    
    @staticmethod
    def process_image(image_file, blur_faces: bool = False):
        """Process uploaded image"""
        img = Image.open(image_file)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Auto-rotate based on EXIF
        try:
            exif = img._getexif()
            if exif:
                orientation = exif.get(0x0112)
                if orientation == 3:
                    img = img.rotate(180, expand=True)
                elif orientation == 6:
                    img = img.rotate(270, expand=True)
                elif orientation == 8:
                    img = img.rotate(90, expand=True)
        except:
            pass
        
        # Resize if too large
        max_size = (1920, 1080)
        if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Blur faces if requested
        if blur_faces:
            # TODO: Integrate with face detection library
            # For now, blur the entire image
            img = img.filter(ImageFilter.GaussianBlur(radius=10))
        
        # Save processed image
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85)
        output.seek(0)
        
        return ContentFile(output.read(), name=image_file.name)
    
    @staticmethod
    def validate_file(file, max_size_mb: int = 10):
        """Validate uploaded file"""
        errors = []
        
        # Check file size
        if file.size > max_size_mb * 1024 * 1024:
            errors.append(f'File size must be less than {max_size_mb}MB')
        
        # Check file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'video/mp4', 'audio/mpeg']
        if file.content_type not in allowed_types:
            errors.append(f'File type {file.content_type} not allowed')
        
        # Check file extension
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mp3', '.m4a']
        if not any(file.name.lower().endswith(ext) for ext in allowed_extensions):
            errors.append('Invalid file extension')
        
        return errors
