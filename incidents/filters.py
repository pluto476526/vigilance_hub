import django_filters
from django.utils import timezone
from .models import Incident

class IncidentFilter(django_filters.FilterSet):
    # Filter by severity, incident_type, county
    severity = django_filters.CharFilter(field_name='severity', lookup_expr='iexact')
    incident_type = django_filters.CharFilter(field_name='incident_type', lookup_expr='iexact')
    county = django_filters.CharFilter(field_name='county', lookup_expr='iexact')
    
    # Filter by date range
    start_date = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    
    # Filter by reporter
    reporter_id = django_filters.UUIDFilter(field_name='reporter__id')
    
    class Meta:
        model = Incident
        fields = ['severity', 'incident_type', 'county', 'reporter_id', 'start_date', 'end_date']

