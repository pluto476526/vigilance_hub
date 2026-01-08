## system_reports/models.py

from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.utils import timezone
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from accounts.models import User
import uuid
import json
from datetime import timedelta


class DataSource(models.Model):
    """Sources for automated incident reports"""
    SOURCE_TYPES = (
        ('social_media', 'Social Media'),
        ('news', 'News Website'),
        ('official', 'Official Source'),
        ('crowdsourced', 'Crowdsourced Platform'),
        ('scanner', 'Radio/Scanner'),
    )
    
    PLATFORMS = (
        ('twitter', 'Twitter/X'),
        ('facebook', 'Facebook'),
        ('whatsapp', 'WhatsApp'),
        ('citizen', 'Citizen App'),
        ('standard', 'Standard Digital'),
        ('nation', 'Nation Africa'),
        ('star', 'The Star'),
        ('nps', 'National Police Service'),
        ('ntsa', 'NTSA'),
        ('krcs', 'Kenya Red Cross'),
        ('other', 'Other'),
    )
    
    name = models.CharField(max_length=100)
    platform = models.CharField(max_length=30, choices=PLATFORMS)
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPES)
    base_url = models.URLField(max_length=500, blank=True, null=True)
    api_endpoint = models.URLField(max_length=500, blank=True, null=True)
    credibility_score = models.FloatField(default=0.5)  # 0-1
    is_active = models.BooleanField(default=True)
    requires_auth = models.BooleanField(default=False)
    auth_config = models.JSONField(default=dict, blank=True)  # API keys, tokens
    last_fetched = models.DateTimeField(null=True, blank=True)
    fetch_interval = models.IntegerField(default=15)  # minutes
    rate_limit = models.IntegerField(default=100)  # requests per hour
    
    class Meta:
        db_table = 'data_sources'
    
    def __str__(self):
        return f"{self.get_platform_display()}: {self.name}"


class AutomatedReport(models.Model):
    """
    System-generated incident reports from automated sources.
    Separate from user-submitted Incident model for moderation.
    """
    
    STATUS_CHOICES = (
        ('raw', 'Raw - Unprocessed'),
        ('processed', 'Processed'),
        ('geocoded', 'Geocoded'),
        ('scored', 'Credibility Scored'),
        ('pending_review', 'Pending Review'),
        ('approved', 'Approved for Map'),
        ('rejected', 'Rejected'),
        ('merged', 'Merged with Existing'),
    )
    
    CONFIDENCE_LEVELS = (
        ('low', 'Low Confidence'),
        ('medium', 'Medium Confidence'),
        ('high', 'High Confidence'),
        ('verified', 'Verified Source'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Source information
    source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, related_name='reports')
    source_identifier = models.CharField(max_length=500, db_index=True)  # URL, tweet ID, etc.
    source_metadata = models.JSONField(default=dict, blank=True)  # Raw API response
    
    # Content
    raw_content = models.TextField()  # Original text
    processed_content = models.TextField(blank=True, null=True)  # Cleaned text
    extracted_title = models.CharField(max_length=200, blank=True, null=True)
    extracted_description = models.TextField(blank=True, null=True)
    
    # Location extraction
    location_text = models.CharField(max_length=500, blank=True, null=True)  # "Along Thika Road near Garden City"
    county = models.CharField(max_length=100, blank=True, null=True)
    constituency = models.CharField(max_length=100, blank=True, null=True)
    ward = models.CharField(max_length=100, blank=True, null=True)
    road = models.CharField(max_length=200, blank=True, null=True)
    landmark = models.CharField(max_length=200, blank=True, null=True)
    
    # Geocoded location
    location = gis_models.PointField(null=True, blank=True)
    address = models.CharField(max_length=500, blank=True, null=True)
    location_accuracy = models.CharField(
        max_length=20,
        choices=[('exact', 'Exact'), ('approximate', 'Approximate'), ('county', 'County Level')],
        default='approximate'
    )
    
    # Incident classification
    incident_type = models.CharField(max_length=30, choices=models.Incident.INCIDENT_TYPES, blank=True, null=True)
    category = models.ForeignKey('IncidentCategory', on_delete=models.SET_NULL, null=True, blank=True)
    severity = models.CharField(max_length=20, choices=models.Incident.SEVERITY_LEVELS, default='medium')
    
    # Keywords detected (Swahili & English)
    detected_keywords = models.JSONField(default=list, blank=True)
    
    # Credibility scoring
    confidence_score = models.FloatField(default=0.0)  # 0-1
    confidence_level = models.CharField(max_length=20, choices=CONFIDENCE_LEVELS, default='low')
    
    # Verification metrics
    cross_source_mentions = models.IntegerField(default=1)  # How many sources report same incident
    source_reliability = models.FloatField(default=0.5)  # Based on source credibility
    temporal_recency = models.FloatField(default=1.0)  # How recent is the report
    language_certainty = models.FloatField(default=0.5)  # Certainty in NLP extraction
    
    # Moderation
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='raw')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, null=True)
    
    # Link to official Incident if approved
    incident = models.ForeignKey('Incident', on_delete=models.SET_NULL, null=True, blank=True, related_name='automated_sources')
    
    # Timestamps
    reported_at = models.DateTimeField()  # When incident reportedly occurred
    fetched_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Search optimization
    search_vector = SearchVectorField(null=True, blank=True)
    
    class Meta:
        db_table = 'automated_reports'
        indexes = [
            models.Index(fields=['status', 'confidence_level']),
            models.Index(fields=['county', 'reported_at']),
            models.Index(fields=['incident_type', 'reported_at']),
            GinIndex(fields=['search_vector']),
        ]
        ordering = ['-reported_at']
    
    def __str__(self):
        return f"{self.extracted_title or self.raw_content[:50]}... ({self.get_confidence_level_display()})"
    
    def calculate_confidence(self):
        """Calculate overall confidence score based on multiple factors"""
        # Weighted average of various signals
        weights = {
            'source_reliability': 0.3,
            'cross_source_mentions': 0.25,
            'temporal_recency': 0.2,
            'language_certainty': 0.15,
            'location_accuracy': 0.1,
        }
        
        # Normalize cross_source_mentions (cap at 5)
        mentions_score = min(self.cross_source_mentions / 5, 1.0)
        
        # Location accuracy scoring
        location_scores = {'exact': 1.0, 'approximate': 0.7, 'county': 0.3}
        location_score = location_scores.get(self.location_accuracy, 0.5)
        
        total_score = (
            weights['source_reliability'] * self.source_reliability +
            weights['cross_source_mentions'] * mentions_score +
            weights['temporal_recency'] * self.temporal_recency +
            weights['language_certainty'] * self.language_certainty +
            weights['location_accuracy'] * location_score
        )
        
        self.confidence_score = total_score
        
        # Set confidence level
        if total_score >= 0.8:
            self.confidence_level = 'high'
        elif total_score >= 0.6:
            self.confidence_level = 'medium'
        else:
            self.confidence_level = 'low'
        
        if self.source and self.source.source_type == 'official':
            self.confidence_level = 'verified'
        
        return total_score


class KenyanGazetteer(models.Model):
    """Database of Kenyan locations for NLP matching"""
    LOCATION_TYPES = (
        ('county', 'County'),
        ('constituency', 'Constituency'),
        ('ward', 'Ward'),
        ('town', 'Town/City'),
        ('estate', 'Estate/Suburb'),
        ('road', 'Road/Highway'),
        ('landmark', 'Landmark'),
        ('market', 'Market'),
        ('school', 'School'),
        ('hospital', 'Hospital'),
    )
    
    name = models.CharField(max_length=200)
    alternate_names = models.JSONField(default=list, blank=True)  # Common misspellings, abbreviations
    location_type = models.CharField(max_length=30, choices=LOCATION_TYPES)
    county = models.CharField(max_length=100)
    constituency = models.CharField(max_length=100, blank=True, null=True)
    ward = models.CharField(max_length=100, blank=True, null=True)
    location = gis_models.PointField(null=True, blank=True)
    geometry = gis_models.GeometryField(null=True, blank=True)  # For polygons (counties, constituencies)
    importance = models.IntegerField(default=1)  # 1-10, for disambiguation
    population = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'kenyan_gazetteer'
        indexes = [
            models.Index(fields=['name', 'county']),
            models.Index(fields=['location_type', 'county']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_location_type_display()}) - {self.county}"


class IncidentKeyword(models.Model):
    """Keywords for detecting incidents in text (English & Swahili)"""
    LANGUAGE_CHOICES = (
        ('en', 'English'),
        ('sw', 'Swahili'),
        ('both', 'Both'),
    )
    
    keyword = models.CharField(max_length=100)
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES)
    incident_type = models.CharField(max_length=30, choices=models.Incident.INCIDENT_TYPES)
    severity_weight = models.IntegerField(default=1)  # 1-5
    is_regex = models.BooleanField(default=False)
    regex_pattern = models.CharField(max_length=500, blank=True, null=True)
    context_words = models.JSONField(default=list, blank=True)  # Words that should appear nearby
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'incident_keywords'
        unique_together = ['keyword', 'language', 'incident_type']
    
    def __str__(self):
        return f"{self.keyword} ({self.get_language_display()}) → {self.incident_type}"


class ReportProcessingLog(models.Model):
    """Log for automated report processing"""
    report = models.ForeignKey(AutomatedReport, on_delete=models.CASCADE, related_name='processing_logs')
    stage = models.CharField(max_length=50)
    input_data = models.TextField(blank=True, null=True)
    output_data = models.JSONField(default=dict, blank=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)
    processing_time = models.FloatField()  # Seconds
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'report_processing_logs'
        ordering = ['-created_at']


class CrossSourceMatch(models.Model):
    """Track when multiple sources report the same incident"""
    incident = models.ForeignKey('Incident', on_delete=models.CASCADE, related_name='cross_source_matches', null=True, blank=True)
    automated_reports = models.ManyToManyField(AutomatedReport)
    match_score = models.FloatField(default=0.0)
    is_confirmed_match = models.BooleanField(default=False)
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'cross_source_matches'
