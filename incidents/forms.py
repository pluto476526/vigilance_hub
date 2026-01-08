# incidents/forms.py
from django import forms
from django.contrib.gis.geos import Point
from .models import Incident

class IncidentReportForm(forms.ModelForm):
    use_current_location = forms.BooleanField(required=False)
    media_files = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput()
    )

    class Meta:
        model = Incident
        fields = [
            "title",
            "description",
            "incident_type",
            "severity",
            "county",
            "address",
            "constituency",
            "anonymous",
        ]

    def save(self, user=None, point=None, commit=True):
        incident = super().save(commit=False)

        if point:
            incident.location = point

        if user and not incident.anonymous:
            incident.reporter = user

        if commit:
            incident.save()

        return incident

