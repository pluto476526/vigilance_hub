from django.db import models
from django.core.files.base import ContentFile
from django.contrib.gis.db import models as gis_models
from django.utils import timezone
from accounts.models import User
from PIL import Image, ImageFilter
from io import BytesIO
import uuid
import os


class IncidentCategory(models.Model):
    """Categories for incidents"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, default='exclamation-triangle')
    color = models.CharField(max_length=20, default='#ff6b6b')
    severity_weight = models.IntegerField(default=1)  # 1-10
    requires_verification = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'incident_categories'
        verbose_name_plural = 'Incident Categories'
    
    def __str__(self):
        return self.name


class Incident(models.Model):
    """Core Incident Model"""
    INCIDENT_TYPES = (
        ('crime', 'Criminal Activity'),
        ('accident', 'Road Accident'),
        ('hazard', 'Public Hazard'),
        ('checkpoint', 'Police Checkpoint'),
        ('sos', 'SOS/Emergency'),
        ('police_interaction', 'Police Interaction'),
        ('other', 'Other Incident'),
    )
    
    SEVERITY_LEVELS = (
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Emergency'),
    )
    
    STATUS_CHOICES = (
        ('reported', 'Reported'),
        ('verified', 'Verified'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved'),
        ('false_report', 'False Report'),
        ('closed', 'Closed'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(IncidentCategory, on_delete=models.PROTECT, null=True, blank=True, related_name='incidents')
    incident_type = models.CharField(max_length=30, choices=INCIDENT_TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='medium')
    
    # Location data
    location = gis_models.PointField(null=True)
    address = models.CharField(max_length=500)
    county = models.CharField(max_length=100)
    constituency = models.CharField(max_length=100, blank=True, null=True)
    ward = models.CharField(max_length=100, blank=True, null=True)
    
    # Reporting info
    anonymous = models.BooleanField(default=True)
    reporter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reported_incidents')
    
    # Verification system
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_incidents')
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_count = models.IntegerField(default=0)
    false_report_count = models.IntegerField(default=0)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='reported')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_incidents')
    resolution_notes = models.TextField(blank=True, null=True)
    
    # Media
    media_files = models.JSONField(default=list, blank=True)  # Store list of file paths
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Indexing
    class Meta:
        db_table = 'incidents'
        indexes = [
            models.Index(fields=['status', 'severity']),
            models.Index(fields=['county', 'created_at']),
            models.Index(fields=['location'], name='incident_location_idx'),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.get_severity_display()}"
    
    def save(self, *args, **kwargs):
        # Set expiration date for non-critical incidents (30 days)
        if not self.expires_at and self.severity != 'critical':
            self.expires_at = timezone.now() + timezone.timedelta(days=30)
        super().save(*args, **kwargs)
    
    def verify(self, user):
        """Verify an incident"""
        self.verified = True
        self.verified_by = user
        self.verified_at = timezone.now()
        self.verification_count += 1
        self.save()
    
    def mark_false_report(self):
        """Mark as false report"""
        self.false_report_count += 1
        if self.false_report_count >= 3:
            self.status = 'false_report'
        self.save()


class IncidentMedia(models.Model):
    """Media files for incidents"""
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='incident_media/%Y/%m/%d/')
    file_type = models.CharField(max_length=20)  # image, video, audio, document
    thumbnail = models.ImageField(upload_to='incident_thumbnails/', blank=True, null=True)
    blurred = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'incident_media'
    
    def save(self, *args, **kwargs):
        if self.file_type == 'image' and not self.thumbnail:
            # Generate thumbnail
            img = Image.open(self.file)
            img.thumbnail((300, 300))
            thumb_io = BytesIO()
            img.save(thumb_io, format='JPEG')
            self.thumbnail.save(
                f'{os.path.splitext(self.file.name)[0]}_thumb.jpg',
                ContentFile(thumb_io.getvalue()),
                save=False
            )
            
            # Auto-blur faces if needed
            if self.blurred:
                img = Image.open(self.file)
                img = img.filter(ImageFilter.GaussianBlur(radius=10))
                blurred_io = BytesIO()
                img.save(blurred_io, format='JPEG')
                self.file.save(
                    f'{os.path.splitext(self.file.name)[0]}_blurred.jpg',
                    ContentFile(blurred_io.getvalue()),
                    save=False
                )
        super().save(*args, **kwargs)


class IncidentVerification(models.Model):
    """Track incident verifications by users"""
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='verifications')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incident_verifications')
    is_verified = models.BooleanField(default=True)  # True for verify, False for dispute
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'incident_verifications'
        unique_together = ['incident', 'user']  # One vote per user per incident


class SafetyAlert(models.Model):
    """Safety alerts for users"""
    ALERT_TYPES = (
        ('incident', 'New Incident'),
        ('trend', 'Area Trend'),
        ('emergency', 'Emergency Alert'),
        ('system', 'System Update'),
    )
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    severity = models.CharField(max_length=20, choices=Incident.SEVERITY_LEVELS)
    
    # Target area
    location = gis_models.PointField(null=True, blank=True)
    radius_km = models.FloatField(default=5.0)  # Alert radius in kilometers
    counties = models.JSONField(default=list, blank=True)  # List of counties
    
    # Targeting
    target_user_types = models.JSONField(default=list, blank=True)
    send_email = models.BooleanField(default=True)
    send_sms = models.BooleanField(default=False)
    send_push = models.BooleanField(default=True)
    
    # Tracking
    sent_count = models.IntegerField(default=0)
    delivered_count = models.IntegerField(default=0)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'safety_alerts'
        ordering = ['-created_at']
