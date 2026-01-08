## system_reports/ingestion.py

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
from django.utils import timezone
from django.contrib.gis.geos import Point
from django.db import transaction
from django.conf import settings

from models import (
    AutomatedReport, DataSource, KenyanGazetteer, 
    IncidentKeyword, ReportProcessingLog, CrossSourceMatch
)

logger = logging.getLogger(__name__)

class NLPProcessor:
    """Natural Language Processing for incident reports"""
    
    def __init__(self):
        # Common Kenyan location patterns
        self.location_patterns = [
            r'along\s+([A-Za-z\s]+Road|Way|Avenue|Street)',
            r'near\s+([A-Za-z\s]+Mall|Market|Hospital|School)',
            r'in\s+([A-Za-z\s]+County)',
            r'at\s+([A-Za-z\s]+Roundabout|Junction)',
        ]
        
        # Time patterns
        self.time_patterns = [
            r'(\d{1,2}:\d{2}\s*(AM|PM|am|pm))',
            r'(\d{1,2}\s*(hours|hrs|o\'clock))',
        ]
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove URLs, mentions, hashtags (keep text)
        text = re.sub(r'http\S+|@\w+|#\w+', '', text)
        # Remove special characters but keep Swahili characters
        text = re.sub(r'[^\w\s\d\u00C0-\u017F]', ' ', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text.lower()
    
    def detect_keywords(self, text: str) -> List[str]:
        """Detect incident-related keywords"""
        keywords = []
        text_lower = text.lower()
        
        # Get all active keywords
        incident_keywords = IncidentKeyword.objects.filter(is_active=True)
        
        for keyword_obj in incident_keywords:
            if keyword_obj.is_regex and keyword_obj.regex_pattern:
                if re.search(keyword_obj.regex_pattern, text_lower, re.IGNORECASE):
                    keywords.append(keyword_obj.keyword)
            elif keyword_obj.keyword.lower() in text_lower:
                keywords.append(keyword_obj.keyword)
        
        return keywords
    
    def classify_incident(self, text: str, keywords: List[str]) -> Tuple[str, Optional]:
        """Classify incident type based on keywords and text"""
        from incidents.models import IncidentCategory
        
        # Map keywords to incident types
        keyword_mapping = {
            'accident': 'accident',
            'ajali': 'accident',
            'crash': 'accident',
            'robbery': 'crime',
            'wizi': 'crime',
            'theft': 'crime',
            'shooting': 'crime',
            'risasi': 'crime',
            'fire': 'hazard',
            'moto': 'hazard',
            'police': 'police_interaction',
            'checkpoint': 'checkpoint',
            'sos': 'sos',
            'emergency': 'sos',
        }
        
        # Find most common incident type from keywords
        incident_counts = {}
        for keyword in keywords:
            for kw, incident_type in keyword_mapping.items():
                if kw in keyword.lower():
                    incident_counts[incident_type] = incident_counts.get(incident_type, 0) + 1
        
        if incident_counts:
            incident_type = max(incident_counts.items(), key=lambda x: x[1])[0]
        else:
            incident_type = 'other'
        
        # Try to find matching category
        category = None
        try:
            if incident_type == 'accident':
                category = IncidentCategory.objects.filter(name__icontains='accident').first()
            elif incident_type == 'crime':
                category = IncidentCategory.objects.filter(name__icontains='crime').first()
            elif incident_type == 'hazard':
                category = IncidentCategory.objects.filter(name__icontains='hazard').first()
        except:
            pass
        
        return incident_type, category
    
    def extract_location(self, text: str) -> Dict:
        """Extract location information from text"""
        result = {
            'text': '',
            'county': None,
            'constituency': None,
            'ward': None,
            'road': None,
            'landmark': None
        }
        
        # Check Kenyan counties first
        counties = [
            'nairobi', 'mombasa', 'kisumu', 'nakuru', 'kiambu', 'kakamega',
            'bungoma', 'migori', 'kisii', 'nyamira', 'laikipia', 'nyeri',
            'kilifi', 'kwale', 'lamu', 'taita taveta', 'garissa', 'wajir',
            'mandera', 'marsabit', 'isiolo', 'meru', 'tharaka nithi', 'embu',
            'kitui', 'machakos', 'makueni', 'nyandarua', 'kirinyaga', 'muranga',
            'bomet', 'kericho', 'narok', 'kajiado', 'turkana', 'west pokot',
            'samburu', 'trans nzoia', 'uasin gishu', 'elgeyo marakwet', 'nandi',
            'baringo', 'vihiga', 'busia', 'siaya', 'homa bay', 'nyanza'
        ]
        
        text_lower = text.lower()
        for county in counties:
            if county in text_lower:
                result['county'] = county.title()
                break
        
        # Extract road names
        road_patterns = [
            r'(thika\s+road|mombasa\s+road|waiyaki\s+way|ngong\s+road|',
            r'jogoo\s+road|langata\s+road|kasarani|eastern\s+bypass)'
        ]
        
        for pattern in self.location_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                result['text'] = matches[0]
                if 'road' in pattern.lower():
                    result['road'] = matches[0]
                elif 'near' in pattern.lower():
                    result['landmark'] = matches[0]
                break
        
        return result
    
    def calculate_certainty(self, text: str) -> float:
        """Calculate certainty based on language patterns"""
        certainty_indicators = [
            (r'\bconfirmed\b|\bverified\b', 0.3),
            (r'\breported\b|\bsaid\b', 0.1),
            (r'\bralleged\b|\bunconfirmed\b', -0.2),
            (r'\brumour\b|\bheard\b', -0.3),
            (r'\bmultiple\s+witnesses\b', 0.2),
            (r'\bpolice\s+confirm\b', 0.4),
        ]
        
        certainty = 0.5  # Base certainty
        
        for pattern, weight in certainty_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                certainty += weight
        
        return max(0.0, min(1.0, certainty))


class KenyanGeocoder:
    """Geocode Kenyan locations"""
    
    def __init__(self):
        self.nominatim_url = "https://nominatim.openstreetmap.org/search"
    
    def geocode(self, location_text: str) -> Optional[Dict]:
        """Geocode a location string to coordinates"""
        if not location_text:
            return None
        
        try:
            # Add Kenya context to improve results
            query = f"{location_text}, Kenya"
            
            params = {
                'q': query,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'ke',
            }
            
            headers = {
                'User-Agent': 'SafetyApp/1.0 (your-email@example.com)'
            }
            
            response = requests.get(self.nominatim_url, params=params, headers=headers)
            
            if response.status_code == 200:
                results = response.json()
                if results:
                    result = results[0]
                    
                    # Determine accuracy
                    accuracy = 'approximate'
                    if 'road' in result.get('type', '') or 'highway' in result.get('type', ''):
                        accuracy = 'exact'
                    elif 'city' in result.get('type', '') or 'town' in result.get('type', ''):
                        accuracy = 'approximate'
                    else:
                        accuracy = 'county'
                    
                    return {
                        'point': Point(float(result['lon']), float(result['lat'])),
                        'address': result.get('display_name', ''),
                        'accuracy': accuracy
                    }
        except Exception as e:
            logger.error(f"Geocoding failed for {location_text}: {e}")
        
        # Fallback: Use county centroid if we know the county
        county_match = re.search(r'\b(nairobi|mombasa|kisumu|nakuru)\b', location_text.lower())
        if county_match:
            county_centroids = {
                'nairobi': (36.8219, -1.2921),
                'mombasa': (39.6682, -4.0435),
                'kisumu': (34.7616, -0.1022),
                'nakuru': (36.0737, -0.3031),
            }
            county = county_match.group(1)
            if county in county_centroids:
                lon, lat = county_centroids[county]
                return {
                    'point': Point(lon, lat),
                    'address': f"{county.title()} County, Kenya",
                    'accuracy': 'county'
                }
        
        return None


class ConfidenceScorer:
    """Score report confidence"""
    
    def calculate_overall_score(self, report: AutomatedReport) -> float:
        """Calculate overall confidence score"""
        return report.calculate_confidence()  # Uses the model method


class IncidentIngestionPipeline:
    """Main pipeline for ingesting and processing automated reports"""
    
    def __init__(self):
        self.nlp_processor = NLPProcessor()
        self.geocoder = KenyanGeocoder()
        self.confidence_scorer = ConfidenceScorer()
        
    def run_pipeline(self):
        """Main pipeline execution"""
        logger.info("Starting automated incident ingestion pipeline")
        
        # 1. Fetch from all active sources
        reports = self.fetch_from_sources()
        
        # 2. Process each report
        for raw_report in reports:
            try:
                self.process_single_report(raw_report)
            except Exception as e:
                logger.error(f"Failed to process report: {e}", exc_info=True)
        
        # 3. Find cross-source matches
        self.find_cross_source_matches()
        
        # 4. Auto-approve high confidence reports
        self.auto_approve_high_confidence()
        
        logger.info("Pipeline completed")
    
    def fetch_from_sources(self) -> List[Dict]:
        """Fetch reports from all configured sources"""
        active_sources = DataSource.objects.filter(is_active=True)
        all_reports = []
        
        for source in active_sources:
            try:
                reports = self.fetch_from_source(source)
                all_reports.extend(reports)
                source.last_fetched = timezone.now()
                source.save()
            except Exception as e:
                logger.error(f"Failed to fetch from {source.name}: {e}")
        
        return all_reports
    
    def fetch_from_source(self, source: DataSource) -> List[Dict]:
        """Fetch reports from a specific source"""
        if source.platform == 'twitter':
            return self.fetch_twitter(source)
        elif source.platform in ['standard', 'nation', 'star']:
            return self.fetch_news_rss(source)
        elif source.platform == 'citizen':
            return self.fetch_citizen_app(source)
        elif source.platform == 'nps':
            return self.fetch_nps_alerts(source)
        else:
            return []
    
    def fetch_twitter(self, source: DataSource) -> List[Dict]:
        """Fetch tweets based on keywords"""
        # Keywords for Kenya incidents (English & Swahili)
        keywords = [
            'accident', 'robbery', 'shooting', 'fire', 'crash', 'theft',
            'ajali', 'wizi', 'moto', 'risasi', 'mgomo', 'maandamano',
            'Nairobi', 'Mombasa', 'Kisumu', 'Nakuru'
        ]
        
        # Twitter API v2
        # For now, return mock data
        return [
            {
                'source': source,
                'source_identifier': '123456789',
                'raw_content': 'Major accident along Thika Road near Garden City. Traffic building up. #NairobiTraffic',
                'reported_at': timezone.now() - timedelta(minutes=30),
                'metadata': {'author': '@NairobiTraffic', 'retweets': 15}
            }
        ]
    
    def fetch_news_rss(self, source: DataSource) -> List[Dict]:
        """Fetch from Kenyan news RSS feeds"""
        # RSS feeds for major Kenyan newspapers
        rss_feeds = {
            'standard': 'https://www.standardmedia.co.ke/rss/headlines.php',
            'nation': 'https://nation.africa/kenya/rss',
            'star': 'https://www.the-star.co.ke/rss'
        }
        
        # Parse RSS and extract incident-related news
        return []
    
    def process_single_report(self, raw_data: Dict):
        """Process a single raw report through the pipeline"""
        
        with transaction.atomic():
            # Check for duplicates
            if AutomatedReport.objects.filter(
                source_identifier=raw_data['source_identifier'],
                source=raw_data['source']
            ).exists():
                return
            
            # Create report
            report = AutomatedReport.objects.create(
                source=raw_data['source'],
                source_identifier=raw_data['source_identifier'],
                source_metadata=raw_data.get('metadata', {}),
                raw_content=raw_data['raw_content'],
                reported_at=raw_data['reported_at'],
                status='raw'
            )
            
            # Stage 1: Text cleaning
            self.log_processing(report, 'text_cleaning')
            cleaned_text = self.nlp_processor.clean_text(raw_data['raw_content'])
            report.processed_content = cleaned_text
            
            # Stage 2: Keyword detection
            self.log_processing(report, 'keyword_detection')
            keywords = self.nlp_processor.detect_keywords(cleaned_text)
            report.detected_keywords = keywords
            
            # Stage 3: Incident classification
            self.log_processing(report, 'classification')
            incident_type, category = self.nlp_processor.classify_incident(cleaned_text, keywords)
            report.incident_type = incident_type
            if category:
                report.category = category
            
            # Stage 4: Location extraction
            self.log_processing(report, 'location_extraction')
            location_data = self.nlp_processor.extract_location(cleaned_text)
            report.location_text = location_data.get('text')
            report.county = location_data.get('county')
            report.constituency = location_data.get('constituency')
            report.ward = location_data.get('ward')
            report.road = location_data.get('road')
            report.landmark = location_data.get('landmark')
            
            # Stage 5: Geocoding
            self.log_processing(report, 'geocoding')
            if location_data.get('text'):
                geocode_result = self.geocoder.geocode(location_data['text'])
                if geocode_result:
                    report.location = geocode_result['point']
                    report.address = geocode_result['address']
                    report.location_accuracy = geocode_result['accuracy']
                    report.status = 'geocoded'
            
            # Stage 6: Confidence scoring
            self.log_processing(report, 'confidence_scoring')
            report.source_reliability = report.source.credibility_score
            report.temporal_recency = self.calculate_recency_score(report.reported_at)
            report.language_certainty = self.nlp_processor.calculate_certainty(cleaned_text)
            report.calculate_confidence()
            report.status = 'scored'
            
            # Stage 7: Check for similar existing reports
            similar = self.find_similar_reports(report)
            if similar:
                report.cross_source_mentions = len(similar) + 1
                report.calculate_confidence()  # Recalculate with new mentions
            
            report.processed_at = timezone.now()
            report.status = 'pending_review'
            report.save()
    
    def log_processing(self, report: AutomatedReport, stage: str, success: bool = True, error: str = None, processing_time: float = 0.0):
        """Log processing step"""
        ReportProcessingLog.objects.create(
            report=report,
            stage=stage,
            success=success,
            error_message=error,
            processing_time=processing_time
        )
    
    def calculate_recency_score(self, reported_at) -> float:
        """Calculate score based on how recent the report is"""
        hours_ago = (timezone.now() - reported_at).total_seconds() / 3600
        
        if hours_ago < 1:
            return 1.0
        elif hours_ago < 3:
            return 0.8
        elif hours_ago < 6:
            return 0.6
        elif hours_ago < 12:
            return 0.4
        elif hours_ago < 24:
            return 0.2
        else:
            return 0.1
    
    def find_similar_reports(self, report: AutomatedReport) -> List[AutomatedReport]:
        """Find similar reports based on location and time"""
        if not report.location:
            return []
        
        # Find reports within 5km and 2 hours
        time_window = report.reported_at - timedelta(hours=2)
        
        similar = AutomatedReport.objects.filter(
            location__distance_lte=(report.location, 5000),  # 5km
            reported_at__gte=time_window,
            incident_type=report.incident_type,
            status__in=['scored', 'pending_review', 'approved']
        ).exclude(id=report.id)
        
        return list(similar)
    
    def find_cross_source_matches(self):
        """Find and group reports that likely refer to same incident"""
        recent_reports = AutomatedReport.objects.filter(
            status='scored',
            reported_at__gte=timezone.now() - timedelta(hours=6)
        )
        
        # Simple clustering by location and time
        for report in recent_reports:
            similar = self.find_similar_reports(report)
            if similar:
                # Create or update cross-source match
                match, created = CrossSourceMatch.objects.get_or_create(incident=report.incident)
                match.automated_reports.add(report, *similar)
                match.match_score = len(similar) * 0.2  # Simple scoring
                match.save()
    
    def auto_approve_high_confidence(self):
        """Auto-approve reports with very high confidence"""
        high_confidence = AutomatedReport.objects.filter(
            confidence_level__in=['high', 'verified'],
            status='pending_review',
            location__isnull=False
        )
        
        for report in high_confidence:
            # Create official Incident from high-confidence automated report
            from incidents.models import Incident
            
            incident = Incident.objects.create(
                title=report.extracted_title or f"Reported {report.get_incident_type_display()}",
                description=report.extracted_description or report.processed_content,
                category=report.category,
                incident_type=report.incident_type,
                severity=report.severity,
                location=report.location,
                address=report.address or report.location_text,
                county=report.county or '',
                constituency=report.constituency,
                ward=report.ward,
                anonymous=True,
                verified=False,  # Still needs human verification
                status='reported',
                media_files=[],  # No media from automated reports
                expires_at=timezone.now() + timedelta(days=30)
            )
            
            report.incident = incident
            report.status = 'approved'
            report.review_notes = 'Auto-approved due to high confidence score'
            report.save()
            
            logger.info(f"Auto-approved report {report.id} as incident {incident.id}")

