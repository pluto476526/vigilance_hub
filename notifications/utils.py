from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
import requests
import json
from typing import List, Dict
from twilio.rest import Client
import logging

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manage notifications for the platform"""
    
    @staticmethod
    def send_email_notification(user_email: str, subject: str, template_name: str, 
                               context: Dict, from_email: str = None):
        """Send email notification"""
        try:
            html_message = render_to_string(f'notifications/email/{template_name}.html', context)
            text_message = render_to_string(f'notifications/email/{template_name}.txt', context)
            
            send_mail(
                subject=subject,
                message=text_message,
                from_email=from_email or settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                html_message=html_message,
                fail_silently=False
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {user_email}: {str(e)}")
            return False
    
    @staticmethod
    def send_sms_notification(phone_number: str, message: str):
        """Send SMS notification via Africa's Talking or Twilio"""
        if not phone_number or not message:
            return False
        
        try:
            # Africa's Talking implementation
            if hasattr(settings, 'AFRICASTALKING_API_KEY'):
                headers = {
                    'ApiKey': settings.AFRICASTALKING_API_KEY,
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/json'
                }
                
                data = {
                    'username': settings.AFRICASTALKING_USERNAME,
                    'to': phone_number,
                    'message': message,
                    'from': settings.AFRICASTALKING_SENDER_ID
                }
                
                response = requests.post(
                    'https://api.africastalking.com/version1/messaging',
                    headers=headers,
                    data=data
                )
                
                if response.status_code == 201:
                    return True
            
            # Twilio fallback
            elif hasattr(settings, 'TWILIO_ACCOUNT_SID'):
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                
                message = client.messages.create(
                    body=message,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=phone_number
                )
                
                if message.sid:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
            return False
    
    @staticmethod
    def send_push_notification(user, title: str, body: str, data: Dict = None):
        """Send push notification (placeholder)"""
        # TODO: Implement Firebase Cloud Messaging or similar
        logger.info(f"Push notification for {user.username}: {title} - {body}")
        return True
    
    @staticmethod
    def send_incident_alert(incident, radius_km: float = 5):
        """Send alert for new incident to nearby users"""
        from apps.accounts.models import User
        from django.contrib.gis.geos import Point
        from django.contrib.gis.db.models.functions import Distance
        
        # Get users within radius who want notifications
        users = User.objects.filter(
            location__distance_lte=(incident.location, radius_km * 1000),
            profile__push_notifications=True
        ).annotate(
            distance=Distance('location', incident.location)
        )
        
        for user in users:
            # Email
            if user.profile.email_notifications and user.email:
                NotificationManager.send_email_notification(
                    user.email,
                    f"New Incident Alert: {incident.title}",
                    'incident_alert',
                    {
                        'user': user,
                        'incident': incident,
                        'distance': user.distance.km if hasattr(user.distance, 'km') else None
                    }
                )
            
            # SMS
            if user.profile.sms_notifications and user.phone_number:
                message = f"Alert: {incident.title} near you. Severity: {incident.get_severity_display()}. Stay safe."
                NotificationManager.send_sms_notification(user.phone_number, message)
            
            # Push
            NotificationManager.send_push_notification(
                user,
                f"Incident Alert: {incident.get_severity_display()}",
                incident.description[:100]
            )
    
    @staticmethod
    def send_safety_tip(user):
        """Send daily safety tip"""
        from apps.emergency.models import SafetyTip
        
        # Get random safety tip
        tip = SafetyTip.objects.filter(is_active=True).order_by('?').first()
        
        if tip and user.profile.email_notifications and user.email:
            NotificationManager.send_email_notification(
                user.email,
                f"Daily Safety Tip: {tip.title}",
                'safety_tip',
                {'user': user, 'tip': tip}
            )
