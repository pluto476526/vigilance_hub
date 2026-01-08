import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vigilance_hub.settings")
django.setup()

from incidents.models import IncidentCategory

categories = [
    {"name": "Crime", "severity_weight": 5},
    {"name": "Accident", "severity_weight": 4},
    {"name": "Hazard", "severity_weight": 3},
    {"name": "Emergency", "severity_weight": 10},
    {"name": "Police Interaction", "severity_weight": 2},
    {"name": "Other", "severity_weight": 1},
]

for cat in categories:
    obj, created = IncidentCategory.objects.get_or_create(
        name=cat["name"],
        defaults=cat
    )
    if created:
        print(f"Created category: {cat['name']}")
    else:
        print(f"Category already exists: {cat['name']}")

