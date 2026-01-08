from rest_framework import serializers
from .models import User, UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'bio', 'profile_picture', 'address', 'city', 'county', 'country',
            'email_notifications', 'sms_notifications', 'push_notifications',
            'show_location', 'show_reports',
            'emergency_contact_name', 'emergency_contact_phone'
        ]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)  # Include related profile
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'full_name',
            'email', 'phone_number', 'user_type', 'email_verified',
            'phone_verified', 'is_trusted_reporter', 'trust_score',
            'reports_count', 'location', 'notification_preferences',
            'created_at', 'updated_at', 'profile'
        ]
        read_only_fields = ['id', 'trust_score', 'reports_count', 'created_at', 'updated_at']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

