from django.urls import path

from .views import EventCreateView
from .views import EventDetailView
from .views import EventExportView
from .views import EventListView
from .views import EventUpdateView
from .views import LocationCreateView
from .views import LocationDetailView
from .views import LocationListView
from .views import LocationUpdateView

urlpatterns = [
    path("events/", EventListView.as_view(), name="event_list"),
    path("events/add/", EventCreateView.as_view(), name="event_create"),
    path("events/<int:pk>/", EventDetailView.as_view(), name="event_detail"),
    path("events/<int:pk>/edit/", EventUpdateView.as_view(), name="event_edit"),
    path("events/<int:pk>/export/", EventExportView.as_view(), name="event_export"),
    path("locations/", LocationListView.as_view(), name="location_list"),
    path("locations/add/", LocationCreateView.as_view(), name="location_create"),
    path("locations/<int:pk>/", LocationDetailView.as_view(), name="location_detail"),
    path("locations/<int:pk>/edit/", LocationUpdateView.as_view(), name="location_edit"),
]
