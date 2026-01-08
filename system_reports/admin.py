## system_reports/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.contrib.gis.admin import OSMGeoAdmin
from system_reports.models import (
    AutomatedReport, DataSource, KenyanGazetteer,
    IncidentKeyword, ReportProcessingLog, CrossSourceMatch
)


@admin.register(AutomatedReport)
class AutomatedReportAdmin(OSMGeoAdmin):
    list_display = (
        'id_short', 'incident_type', 'county', 
        'confidence_level', 'status', 'reported_at', 'actions'
    )
    list_filter = ('status', 'confidence_level', 'incident_type', 'county')
    search_fields = ('raw_content', 'location_text', 'extracted_title')
    readonly_fields = ('fetched_at', 'processed_at', 'confidence_score')
    fieldsets = (
        ('Content', {
            'fields': ('raw_content', 'processed_content', 'extracted_title')
        }),
        ('Location', {
            'fields': ('location_text', 'county', 'constituency', 'ward', 'location')
        }),
        ('Classification', {
            'fields': ('incident_type', 'category', 'severity', 'detected_keywords')
        }),
        ('Scoring', {
            'fields': ('confidence_score', 'confidence_level', 'cross_source_mentions')
        }),
        ('Source', {
            'fields': ('source', 'source_identifier', 'source_metadata')
        }),
        ('Moderation', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'review_notes', 'incident')
        }),
        ('Timestamps', {
            'fields': ('reported_at', 'fetched_at', 'processed_at')
        }),
    )
    
    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'ID'
    
    def actions(self, obj):
        if obj.status == 'pending_review':
            return format_html(
                '<a href="/admin/approve_report/{}/" class="button">Approve</a> '
                '<a href="/admin/reject_report/{}/" class="button">Reject</a>',
                obj.id, obj.id
            )
        return ''
    actions.short_description = 'Actions'
    
    def has_add_permission(self, request):
        return False  # Reports should only come through pipeline


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'platform', 'source_type', 'credibility_score', 'is_active', 'last_fetched')
    list_filter = ('platform', 'source_type', 'is_active')
    search_fields = ('name', 'base_url')
    readonly_fields = ('last_fetched',)


@admin.register(KenyanGazetteer)
class KenyanGazetteerAdmin(OSMGeoAdmin):
    list_display = ('name', 'location_type', 'county', 'importance', 'is_active')
    list_filter = ('location_type', 'county', 'is_active')
    search_fields = ('name', 'alternate_names')


@admin.register(IncidentKeyword)
class IncidentKeywordAdmin(admin.ModelAdmin):
    list_display = ('keyword', 'language', 'incident_type', 'severity_weight', 'is_active')
    list_filter = ('language', 'incident_type', 'is_active')
    search_fields = ('keyword', 'context_words')


@admin.register(ReportProcessingLog)
class ReportProcessingLogAdmin(admin.ModelAdmin):
    list_display = ('report_id', 'stage', 'success', 'processing_time', 'created_at')
    list_filter = ('stage', 'success')
    search_fields = ('report__id', 'error_message')
    readonly_fields = ('created_at',)
    
    def report_id(self, obj):
        return str(obj.report.id)[:8]
    report_id.short_description = 'Report ID'


@admin.register(CrossSourceMatch)
class CrossSourceMatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'match_score', 'is_confirmed_match', 'reports_count', 'created_at')
    filter_horizontal = ('automated_reports',)
    
    def reports_count(self, obj):
        return obj.automated_reports.count()
    reports_count.short_description = 'Reports'
