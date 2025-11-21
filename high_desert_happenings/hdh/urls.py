from django.urls import path

from .views import (
    EventCreateView,
    EventDeleteView,
    EventDetailView,
    EventExportView,
    EventListView,
    EventUpdateView,
    LocationCreateView,
    LocationDeleteView,
    LocationDetailView,
    LocationListView,
    LocationUpdateView,
)

urlpatterns = [
    path("events/", EventListView.as_view(), name="event_list"),
    path("events/add/", EventCreateView.as_view(), name="event_create"),
    path("events/<int:pk>/", EventDetailView.as_view(), name="event_detail"),
    path("events/<int:pk>/edit/", EventUpdateView.as_view(), name="event_edit"),
    path("events/<int:pk>/delete/", EventDeleteView.as_view(), name="event_delete"),
    path("events/<int:pk>/export/", EventExportView.as_view(), name="event_export"),
    path("locations/", LocationListView.as_view(), name="location_list"),
    path("locations/add/", LocationCreateView.as_view(), name="location_create"),
    path("locations/<int:pk>/", LocationDetailView.as_view(), name="location_detail"),
    path("locations/<int:pk>/edit/", LocationUpdateView.as_view(), name="location_edit"),
    path("locations/<int:pk>/delete/", LocationDeleteView.as_view(), name="location_delete"),
]
