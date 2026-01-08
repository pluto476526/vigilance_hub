from rest_framework import serializers
from .models import Incident, IncidentCategory, IncidentVerification, SafetyAlert
from accounts.serializers import UserSerializer


class IncidentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentCategory
        fields = ['id', 'name', 'description', 'icon', 'color', 'severity_weight']


class IncidentSerializer(serializers.ModelSerializer):
    category = IncidentCategorySerializer(read_only=True)
    reporter = UserSerializer(read_only=True)
    distance = serializers.SerializerMethodField()
    
    class Meta:
        model = Incident
        fields = [
            'id', 'title', 'description', 'category', 'incident_type', 'severity',
            'location', 'address', 'county', 'anonymous', 'reporter',
            'verified', 'verification_count', 'false_report_count',
            'status', 'media_files', 'created_at', 'updated_at',
            'distance'
        ]
        read_only_fields = ['verified', 'verification_count', 'false_report_count', 'status']
    
    def get_distance(self, obj):
        if hasattr(obj, 'distance'):
            return round(obj.distance.km, 2) if hasattr(obj.distance, 'km') else None
        return None


class IncidentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = [
            'title', 'description', 'category', 'incident_type', 'severity',
            'location', 'address', 'county', 'constituency', 'ward',
            'anonymous', 'media_files'
        ]
    
    def validate(self, data):
        # Additional validation
        from .utils import IncidentValidation
        errors = IncidentValidation.validate_incident_data(data)
        if errors:
            raise serializers.ValidationError(errors)
        
        # Check for spam
        user = self.context['request'].user
        if user.is_authenticated:
            if IncidentValidation.check_spam(user, data):
                raise serializers.ValidationError(
                    'Too many reports recently. Please wait before reporting again.'
                )
        
        return data


class IncidentVerificationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = IncidentVerification
        fields = ['id', 'incident', 'user', 'is_verified', 'comment', 'created_at']
        read_only_fields = ['user']


class SafetyAlertSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = SafetyAlert
        fields = [
            'id', 'title', 'message', 'alert_type', 'severity',
            'location', 'radius_km', 'counties', 'target_user_types',
            'send_email', 'send_sms', 'send_push',
            'sent_count', 'delivered_count', 'created_by',
            'created_at', 'scheduled_for', 'sent_at'
        ]
        read_only_fields = ['sent_count', 'delivered_count', 'created_by']
