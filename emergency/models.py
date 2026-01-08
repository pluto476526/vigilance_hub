from django.db import models
from django.contrib.gis.db import models as gis_models
from django.core.validators import MinValueValidator, MaxValueValidator
from incidents.models import Incident
import uuid


class EmergencyService(models.Model):
    """Emergency Services Directory"""
    SERVICE_TYPES = (
        ('police', 'Police Station'),
        ('hospital', 'Hospital'),
        ('fire', 'Fire Station'),
        ('ambulance', 'Ambulance Service'),
        ('rescue', 'Rescue Service'),
        ('clinic', 'Clinic'),
        ('pharmacy', '24/7 Pharmacy'),
        ('helpline', 'Helpline'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES)
    
    # Contact Information
    phone_number = models.CharField(max_length=15)
    phone_number_2 = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    
    # Location
    location = gis_models.PointField()
    address = models.TextField()
    county = models.CharField(max_length=100)
    constituency = models.CharField(max_length=100, blank=True, null=True)
    ward = models.CharField(max_length=100, blank=True, null=True)
    
    # Service Details
    operational_hours = models.CharField(max_length=100, default='24/7')
    is_24_7 = models.BooleanField(default=True)
    services_offered = models.TextField(blank=True, null=True)
    capacity = models.IntegerField(blank=True, null=True)  # For hospitals: beds
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Ratings
    average_rating = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    total_ratings = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'emergency_services'
        indexes = [
            models.Index(fields=['service_type', 'county']),
            models.Index(fields=['location'], name='service_location_idx'),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_service_type_display()})"


class ServiceReview(models.Model):
    """Reviews for emergency services"""
    service = models.ForeignKey(EmergencyService, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='service_reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)
    response_time_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    professionalism_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'service_reviews'
        unique_together = ['service', 'user']
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update service average rating
        self.service.total_ratings = self.service.reviews.count()
        if self.service.total_ratings > 0:
            self.service.average_rating = self.service.reviews.aggregate(
                avg=models.Avg('rating')
            )['avg']
        self.service.save()


class PoliceInteraction(models.Model):
    """Police interaction reports"""
    INTERACTION_TYPES = (
        ('positive', 'Positive Interaction'),
        ('negative', 'Negative Interaction'),
        ('neutral', 'Neutral Interaction'),
        ('harassment', 'Harassment'),
        ('bribery', 'Bribery Request'),
        ('professional', 'Professional Service'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    description = models.TextField()
    
    # Location
    location = gis_models.PointField()
    address = models.TextField()
    police_station = models.CharField(max_length=200, blank=True, null=True)
    
    # Officer details (optional)
    officer_badge = models.CharField(max_length=50, blank=True, null=True)
    officer_name = models.CharField(max_length=100, blank=True, null=True)
    officer_description = models.TextField(blank=True, null=True)
    
    # Reporting
    anonymous = models.BooleanField(default=True)
    reporter = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='police_interactions')
    
    # Verification
    verified = models.BooleanField(default=False)
    verification_count = models.IntegerField(default=0)
    
    # Timestamps
    incident_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'police_interactions'
        ordering = ['-incident_date']
    
    def __str__(self):
        return f"{self.get_interaction_type_display()} - {self.incident_date.strftime('%Y-%m-%d')}"


class SafetyTip(models.Model):
    """Safety tips and preventive information"""
    TIP_CATEGORIES = (
        ('general', 'General Safety'),
        ('home', 'Home Safety'),
        ('travel', 'Travel Safety'),
        ('cyber', 'Cyber Safety'),
        ('emergency', 'Emergency Preparedness'),
        ('health', 'Health Safety'),
    )
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=20, choices=TIP_CATEGORIES)
    severity = models.CharField(max_length=20, choices=Incident.SEVERITY_LEVELS, default='low')
    icon = models.CharField(max_length=50, default='lightbulb')
    is_active = models.BooleanField(default=True)
    views_count = models.IntegerField(default=0)
    
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'safety_tips'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
