from rest_framework import serializers
from .models import EmergencyService, ServiceReview, PoliceInteraction, SafetyTip
from apps.accounts.serializers import UserSerializer


class EmergencyServiceSerializer(serializers.ModelSerializer):
    distance = serializers.SerializerMethodField()
    
    class Meta:
        model = EmergencyService
        fields = [
            'id', 'name', 'service_type', 'phone_number', 'phone_number_2',
            'email', 'website', 'location', 'address', 'county',
            'operational_hours', 'is_24_7', 'services_offered',
            'capacity', 'is_verified', 'average_rating', 'total_ratings',
            'distance'
        ]
    
    def get_distance(self, obj):
        if hasattr(obj, 'distance'):
            return round(obj.distance.km, 2) if hasattr(obj.distance, 'km') else None
        return None


class ServiceReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    service = serializers.PrimaryKeyRelatedField(queryset=EmergencyService.objects.all())
    
    class Meta:
        model = ServiceReview
        fields = [
            'id', 'service', 'user', 'rating', 'comment',
            'response_time_rating', 'professionalism_rating',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user']
    
    def validate(self, data):
        service = data.get('service')
        user = self.context['request'].user
        
        # Check if user already reviewed this service
        if ServiceReview.objects.filter(service=service, user=user).exists():
            raise serializers.ValidationError('You have already reviewed this service.')
        
        return data


class PoliceInteractionSerializer(serializers.ModelSerializer):
    reporter = UserSerializer(read_only=True)
    
    class Meta:
        model = PoliceInteraction
        fields = [
            'id', 'interaction_type', 'description',
            'location', 'address', 'police_station',
            'officer_badge', 'officer_name', 'officer_description',
            'anonymous', 'reporter', 'verified', 'verification_count',
            'incident_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['verified', 'verification_count']


class SafetyTipSerializer(serializers.ModelSerializer):
    class Meta:
        model = SafetyTip
        fields = [
            'id', 'title', 'content', 'category', 'severity',
            'icon', 'views_count', 'created_by', 'created_at', 'updated_at'
        ]
