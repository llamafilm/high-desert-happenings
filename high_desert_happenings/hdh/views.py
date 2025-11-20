import logging
import uuid
import zoneinfo
from datetime import datetime
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import UpdateView
from markdownx.utils import markdownify

from .forms import EventForm
from .forms import LocationForm
from .models import Event
from .models import Location
from .models import Tag
from .permissions import CanManageEventMixin
from .permissions import CanManageLocationMixin

logger = logging.getLogger(__name__)


class EventListView(LoginRequiredMixin, ListView):
    model = Event
    template_name = "hdh/event_list.html"
    context_object_name = "events"
    paginate_by = 20

    def get_queryset(self):
        """Return list of events based on filters."""
        queryset = Event.objects.select_related(
            "location",
            "created_by",
        ).prefetch_related("tags")

        # Filter by tag if provided
        tag_slug = self.request.GET.get("tag")
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)

        # Filter by neighborhood if provided
        neighborhood = self.request.GET.get("neighborhood")
        if neighborhood:
            queryset = queryset.filter(location__neighborhood=neighborhood)

        # Filter by age restriction if provided
        age_restriction = self.request.GET.get("age_restriction")
        if age_restriction:
            queryset = queryset.filter(age_restriction=age_restriction)

        # Filter by dogs allowed if provided
        dogs_allowed = self.request.GET.get("dogs_allowed")
        if dogs_allowed == "true":
            queryset = queryset.filter(location__dogs_allowed=True)
        elif dogs_allowed == "false":
            queryset = queryset.filter(location__dogs_allowed=False)

        # Determine date range for filtering
        start_date = self.request.GET.get("start_date")
        end_date = self.request.GET.get("end_date")

        start_dt = None
        end_dt = None

        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")  # noqa: DTZ007
                start_dt = timezone.make_aware(start_dt)
            except ValueError:
                pass

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")  # noqa: DTZ007
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                end_dt = timezone.make_aware(end_dt)
            except ValueError:
                pass

        # If no date range specified, default to showing upcoming events (next 90 days)
        if not start_dt:
            start_dt = timezone.now()
        if not end_dt:
            end_dt = start_dt + timedelta(days=90)

        # Filter events within the date range
        queryset = queryset.filter(
            start_datetime__gte=start_dt,
            start_datetime__lte=end_dt,
        )

        return queryset.distinct().order_by("start_datetime")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tags"] = Tag.objects.all().order_by("name")
        context["neighborhoods"] = Location.NEIGHBORHOOD_CHOICES

        # Generate day buttons (today + next 6 days)
        today = timezone.now().date()
        day_buttons = []
        for i in range(7):
            day = today + timedelta(days=i)
            day_buttons.append(
                {
                    "date": day,
                    "display": day.strftime("%a %d") if i > 0 else "Today",
                    "is_selected": (
                        self.request.GET.get("start_date") == day.isoformat()
                        and self.request.GET.get("end_date") == day.isoformat()
                    ),
                },
            )
        context["day_buttons"] = day_buttons

        return context


class EventDetailView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = "hdh/event_detail.html"
    context_object_name = "event"

    def get_queryset(self):
        return Event.objects.select_related("location", "created_by").prefetch_related(
            "tags",
        )

    def get_context_data(self, **kwargs):
        """Add series information if this event is part of a recurring series."""
        context = super().get_context_data(**kwargs)

        # Add series information
        if self.object.is_part_of_series():
            context["is_part_of_series"] = True
            context["series_events"] = self.object.get_series_events()

        # Render styled_description markdown to HTML
        if self.object.styled_description:
            context["styled_description_html"] = markdownify(
                self.object.styled_description,
            )

        return context


class LocationListView(LoginRequiredMixin, ListView):
    model = Location
    template_name = "hdh/location_list.html"
    context_object_name = "locations"
    paginate_by = 20

    def get_queryset(self):
        queryset = Location.objects.all().order_by("name")

        # Filter by neighborhood if provided
        neighborhood = self.request.GET.get("neighborhood")
        if neighborhood:
            queryset = queryset.filter(neighborhood=neighborhood)

        # Filter by dogs allowed if provided
        dogs_allowed = self.request.GET.get("dogs_allowed")
        if dogs_allowed == "true":
            queryset = queryset.filter(dogs_allowed=True)
        elif dogs_allowed == "false":
            queryset = queryset.filter(dogs_allowed=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["neighborhoods"] = Location.NEIGHBORHOOD_CHOICES
        return context


class LocationDetailView(LoginRequiredMixin, DetailView):
    model = Location
    template_name = "hdh/location_detail.html"
    context_object_name = "location"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["events"] = (
            self.object.events.select_related("created_by").prefetch_related("tags").order_by("start_datetime")
        )
        return context


class LocationCreateView(LoginRequiredMixin, CanManageLocationMixin, CreateView):
    """View for creating a new location."""

    model = Location
    form_class = LocationForm
    template_name = "hdh/location_form.html"

    def get_success_url(self):
        """Redirect to location detail page after successful creation."""
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        """Add additional context for the template."""
        context = super().get_context_data(**kwargs)
        context["is_edit"] = False
        return context


class LocationUpdateView(LoginRequiredMixin, CanManageLocationMixin, UpdateView):
    """View for editing an existing location."""

    model = Location
    form_class = LocationForm
    template_name = "hdh/location_form.html"

    def get_success_url(self):
        """Redirect to location detail page after successful update."""
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        """Add additional context for the template."""
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True
        return context


class EventExportView(LoginRequiredMixin, View):
    """Export an event as an ICS calendar file."""

    def format_dt(self, dt: datetime, include_tz=True) -> str:
        """Format datetime for ICS in local timezone"""
        tz_name = settings.TIME_ZONE
        tz = zoneinfo.ZoneInfo(tz_name)
        local_dt = dt.astimezone(tz)
        return f"TZID={tz_name}:{local_dt.strftime('%Y%m%dT%H%M%S')}"

    def get(self, request, pk):
        event = Event.objects.select_related("location").get(pk=pk)

        # Use the event's start and end datetime
        start_dt = event.start_datetime
        end_dt = event.end_datetime

        # Build ICS content
        ics_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//High Desert Happenings//Event//EN",
            "BEGIN:VEVENT",
            f"UID:{event.pk}@highdeserthappenings",
            f"SUMMARY:{event.title}",
            f"DTSTAMP:{self.format_dt(timezone.now(), include_tz=False)}",
            f"DTSTART;{self.format_dt(start_dt)}",
        ]

        if end_dt:
            ics_lines.append(f"DTEND;{self.format_dt(end_dt)}")

        if event.description:
            # Escape description per RFC2445: backslash, semicolon, comma, newline
            desc = event.description.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
            ics_lines.append(f"DESCRIPTION:{desc}")

        if event.location:
            location_str = event.location.name
            if event.location.full_address:
                location_str += f"\\n{event.location.full_address}".replace(",", "\\,")
            ics_lines.append(f"LOCATION:{location_str}")

            # Add geographic coordinates if available
            if event.location.latitude and event.location.longitude:
                ics_lines.append(
                    f"GEO:{event.location.latitude};{event.location.longitude}",
                )
                # Add map link for Apple devices
                apple_location = (
                    f"X-APPLE-STRUCTURED-LOCATION;VALUE=URI;"
                    f'X-ADDRESS="{location_str.replace("\\n", " ").replace("\\,", ",")}";'
                    f"X-TITLE={event.location.name}:"
                    f"geo:{event.location.latitude},{event.location.longitude}"
                )
                ics_lines.append(apple_location)

        if event.webpage_url:
            ics_lines.append(f"URL:{event.webpage_url}")

        ics_lines.extend(
            [
                "END:VEVENT",
                "END:VCALENDAR",
            ],
        )

        # Join with CRLF as per ICS spec
        ics_content = "\r\n".join(ics_lines)

        # In debug mode, return as plain text for easier inspection
        # response = HttpResponse(ics_content, content_type="text/plain")
        filename = f"{event.title.replace(' ', '_')}.ics"
        response = HttpResponse(ics_content, content_type="text/calendar")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class EventCreateView(LoginRequiredMixin, CanManageEventMixin, CreateView):
    """View for creating a new event."""

    model = Event
    form_class = EventForm
    template_name = "hdh/event_form.html"

    def get_success_url(self):
        """Redirect to event detail page after successful creation."""
        return self.object.get_absolute_url()

    def _generate_recurrence_dates(self, recurrence, start_date, max_occurrences=100):
        """Generate list of dates from recurrence rule."""
        if not recurrence:
            return [start_date]

        # Calculate reasonable end date for between() if none specified
        end_date = start_date + timedelta(days=365 * 3)  # 3 years max

        try:
            occurrences = recurrence.between(
                start_date,
                end_date,
                inc=True,
                dtstart=start_date,
            )
            # Limit to prevent abuse
            return list(occurrences)[:max_occurrences]
        except Exception as e:
            msg = f"Error generating recurrence dates: {e}"
            raise ValidationError(msg) from e

    def form_valid(self, form):
        """Set the created_by field to the current user and create recurring events if needed."""
        form.instance.created_by = self.request.user

        # Check if recurrence was specified
        recurrence = form.cleaned_data.get("recurrence_pattern")

        if recurrence:
            # Generate unique series_id for all events in this series
            series_id = uuid.uuid4()

            # Get occurrence dates
            try:
                occurrence_dates = self._generate_recurrence_dates(
                    recurrence,
                    form.cleaned_data["start_datetime"],
                )
            except (ValueError, AttributeError) as e:
                form.add_error("recurrence_pattern", f"Error creating recurrence: {e}")
                return self.form_invalid(form)

            # Calculate duration
            duration = None
            if form.cleaned_data.get("end_datetime"):
                duration = form.cleaned_data["end_datetime"] - form.cleaned_data["start_datetime"]

            # Create first event (parent)
            form.instance.series_id = series_id
            parent_event = form.save()

            # Store for get_success_url
            self.object = parent_event

            # Create child events for remaining occurrences
            tags = list(form.cleaned_data.get("tags", []))

            for occurrence_dt in occurrence_dates[1:]:  # Skip first as it's the parent
                child_event = Event(
                    title=parent_event.title,
                    description=parent_event.description,
                    styled_description=parent_event.styled_description,
                    image=parent_event.image,
                    location=parent_event.location,
                    start_datetime=occurrence_dt,
                    end_datetime=occurrence_dt + duration if duration else None,
                    webpage_url=parent_event.webpage_url,
                    is_free=parent_event.is_free,
                    age_restriction=parent_event.age_restriction,
                    created_by=self.request.user,
                    series_id=series_id,
                    parent_event=parent_event,
                )
                child_event.save()
                child_event.tags.set(tags)

            return super().form_valid(form)

        # No recurrence - just save normally
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Add additional context for the template."""
        context = super().get_context_data(**kwargs)
        context["is_edit"] = False
        return context


class EventUpdateView(LoginRequiredMixin, CanManageEventMixin, UpdateView):
    """View for editing an existing event."""

    model = Event
    form_class = EventForm
    template_name = "hdh/event_form.html"

    def get_success_url(self):
        """Redirect to event detail page after successful update."""
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        """Add additional context for the template."""
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True
        context["is_part_of_series"] = self.object.is_part_of_series()

        # If editing a series event, show update scope options
        if context["is_part_of_series"]:
            context["show_update_scope"] = True
            context["update_scope"] = self.request.POST.get("update_scope", "single")

        return context

    def form_valid(self, form):
        """Handle updating single event or entire series."""
        update_scope = self.request.POST.get("update_scope", "single")

        # If not part of series or updating only this event, use default behavior
        if update_scope == "single" or not self.object.is_part_of_series():
            return super().form_valid(form)

        # Update all future events in the series
        if update_scope == "future":
            events_to_update = self.object.get_future_series_events_including_self()
        # Update all events in the series
        elif update_scope == "all":
            events_to_update = self.object.get_series_events()
        else:
            return super().form_valid(form)

        # Get the fields that changed
        tags = list(form.cleaned_data.get("tags", []))
        updated_fields = {
            "title": form.cleaned_data.get("title"),
            "description": form.cleaned_data.get("description"),
            "styled_description": form.cleaned_data.get("styled_description"),
            "image": form.cleaned_data.get("image"),
            "location": form.cleaned_data.get("location"),
            "webpage_url": form.cleaned_data.get("webpage_url"),
            "is_free": form.cleaned_data.get("is_free"),
            "age_restriction": form.cleaned_data.get("age_restriction"),
        }

        # Update all events in scope (preserve individual start/end times)
        for event in events_to_update:
            for field, value in updated_fields.items():
                setattr(event, field, value)
            event.save()
            event.tags.set(tags)

        # Refresh the current object
        self.object.refresh_from_db()
        return super().form_valid(form)


class EventDeleteView(LoginRequiredMixin, CanManageEventMixin, DeleteView):
    """View for deleting an event."""

    model = Event
    template_name = "hdh/event_confirm_delete.html"

    def get_success_url(self):
        """Redirect to event list after successful deletion."""
        return reverse("event_list")

    def get_context_data(self, **kwargs):
        """Add additional context for the template."""
        context = super().get_context_data(**kwargs)
        context["is_part_of_series"] = self.object.is_part_of_series()

        # If deleting a series event, show delete scope options
        if context["is_part_of_series"]:
            context["show_delete_scope"] = True
            context["delete_scope"] = self.request.POST.get("delete_scope", "single")

        return context

    def post(self, request, *args, **kwargs):
        """Handle deleting single event or entire series."""
        self.object = self.get_object()
        delete_scope = request.POST.get("delete_scope", "single")

        # If not part of series or deleting only this event, use default behavior
        if delete_scope == "single" or not self.object.is_part_of_series():
            return super().post(request, *args, **kwargs)

        # Delete all future events in the series
        if delete_scope == "future":
            events_to_delete = self.object.get_future_series_events_including_self()
        # Delete all events in the series
        elif delete_scope == "all":
            events_to_delete = self.object.get_series_events()
        else:
            return super().post(request, *args, **kwargs)

        # Delete all events in scope
        events_to_delete.delete()

        return self.form_valid(None)


class LocationDeleteView(LoginRequiredMixin, CanManageLocationMixin, DeleteView):
    """View for deleting a location."""

    model = Location
    template_name = "hdh/location_confirm_delete.html"

    def get_success_url(self):
        """Redirect to location list after successful deletion."""
        return reverse("location_list")
