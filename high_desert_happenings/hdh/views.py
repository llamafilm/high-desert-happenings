import logging
import zoneinfo
from datetime import datetime
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import EmptyPage
from django.core.paginator import PageNotAnInteger
from django.core.paginator import Paginator
from django.http import Http404
from django.http import HttpResponse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView
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
from .utils import get_occurrence_start

logger = logging.getLogger(__name__)


class EventListView(LoginRequiredMixin, ListView):
    model = Event
    template_name = "hdh/event_list.html"
    context_object_name = "events"
    paginate_by = 20

    def get_queryset(self):
        """Return list of event occurrences based on filters.
        We can't return a QuerySet because we need to expand recurring events,
        so we return a list of occurrence dicts instead.
        This requires overriding the pagination method as well."""
        queryset = (
            Event.objects.select_related("location", "created_by")
            .prefetch_related("tags")
        )

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
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                start_dt = timezone.make_aware(start_dt)
            except ValueError:
                pass

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                end_dt = timezone.make_aware(end_dt)
            except ValueError:
                pass

        # If no date range specified, default to showing upcoming events (next 90 days)
        if not start_dt:
            start_dt = timezone.now()
        if not end_dt:
            end_dt = start_dt + timedelta(days=90)

        # Filter events that either:
        # 1. Start within the date range, OR
        # 2. Have recurrences (we'll expand these later)
        queryset = queryset.filter(
            start_datetime__gte=start_dt,
            start_datetime__lte=end_dt,
        )

        # Get all events and expand recurring ones
        events = list(queryset.distinct())
        event_occurrences = []

        for event in events:
            # Check if event has recurrences
            if event.recurrences:
                # Generate occurrences within the date range
                occurrences = event.recurrences.between(
                    start_dt,
                    end_dt,
                    inc=True,
                    dtstart=event.start_datetime,
                )

                # Calculate event duration for end_datetime
                duration = None
                if event.end_datetime:
                    duration = event.end_datetime - event.start_datetime

                # Create an occurrence object for each recurrence
                for occ_dt in occurrences:
                    # Make occ_dt timezone-aware if needed
                    if timezone.is_naive(occ_dt):
                        aware_dt = timezone.make_aware(occ_dt)
                    else:
                        aware_dt = occ_dt

                    # Create a copy of the event with updated datetime
                    occurrence = {
                        "event": event,
                        "start_datetime": aware_dt,
                        "end_datetime": aware_dt + duration if duration else None,
                        "is_occurrence": True,
                    }
                    event_occurrences.append(occurrence)
            else:
                # Non-recurring events have a single occurrence
                occurrence = {
                    "event": event,
                    "start_datetime": event.start_datetime,
                    "end_datetime": event.end_datetime,
                    "is_occurrence": False,
                }
                event_occurrences.append(occurrence)

        # Sort all occurrences by start_datetime
        event_occurrences.sort(key=lambda x: x["start_datetime"])

        return event_occurrences

    def paginate_queryset(self, queryset, page_size):
        """Override pagination to handle list instead of QuerySet."""
        paginator = Paginator(queryset, page_size)
        page = self.request.GET.get("page", 1)

        try:
            occurrences = paginator.page(page)
        except PageNotAnInteger:
            occurrences = paginator.page(1)
        except EmptyPage:
            occurrences = paginator.page(paginator.num_pages)

        return (
            paginator,
            occurrences,
            occurrences.object_list,
            occurrences.has_other_pages(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tags"] = Tag.objects.all().order_by("name")
        context["neighborhoods"] = Location.NEIGHBORHOOD_CHOICES

        # Generate day buttons (today + next 6 days)
        today = timezone.now().date()
        day_buttons = []
        for i in range(7):
            day = today + timedelta(days=i)
            day_buttons.append({
                "date": day,
                "display": day.strftime("%a %d") if i > 0 else "Today",
                "is_selected": (
                    self.request.GET.get("start_date") == day.isoformat()
                    and self.request.GET.get("end_date") == day.isoformat()
                ),
            })
        context["day_buttons"] = day_buttons

        return context


class EventDetailView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = "hdh/event_detail.html"
    context_object_name = "event"

    def get_queryset(self):
        return Event.objects.select_related("location", "created_by").prefetch_related("tags")

    def get_context_data(self, **kwargs):
        """Add occurrence date if provided in URL."""
        context = super().get_context_data(**kwargs)

        # Check if an occurrence date was provided
        occurrence_date = self.request.GET.get("occurrence")
        if occurrence_date and self.object.recurrences:
            try:
                # Parse the occurrence date
                occ_dt = datetime.strptime(occurrence_date, "%Y-%m-%d")

                # Get the original event's datetime in its timezone
                original_start = self.object.start_datetime

                # Create the occurrence datetime by replacing the date part
                # while preserving the time and timezone
                occ_datetime = original_start.replace(
                    year=occ_dt.year,
                    month=occ_dt.month,
                    day=occ_dt.day,
                )

                # Validate that this date is actually an occurrence
                # Check within a reasonable range (10 years from original event)
                validation_end = self.object.start_datetime + timedelta(days=3650)
                occurrences = self.object.recurrences.between(
                    self.object.start_datetime,
                    validation_end,
                    inc=True,
                    dtstart=self.object.start_datetime,
                )

                # Check if the requested date matches any occurrence
                is_valid_occurrence = False
                for occ in occurrences:
                    # Make timezone-aware if needed
                    if timezone.is_naive(occ):
                        aware_occ = timezone.make_aware(occ)
                    else:
                        aware_occ = occ
                    # Compare dates (ignore time differences)
                    if aware_occ.date() == occ_datetime.date():
                        is_valid_occurrence = True
                        break

                if is_valid_occurrence:
                    # Calculate end datetime if event has duration
                    occ_end_datetime = None
                    if self.object.end_datetime:
                        duration = self.object.end_datetime - self.object.start_datetime
                        occ_end_datetime = occ_datetime + duration

                    # Override the displayed dates with occurrence dates
                    context["occurrence_start_datetime"] = occ_datetime
                    context["occurrence_end_datetime"] = occ_end_datetime
                    context["is_occurrence_view"] = True
                else:
                    # Invalid occurrence date - return 404
                    msg = "This date is not a valid occurrence of this event."
                    raise Http404(msg)
            except (ValueError, AttributeError):
                pass

        # Render styled_description markdown to HTML
        if self.object.styled_description:
            context["styled_description_html"] = markdownify(self.object.styled_description)

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
            self.object.events.select_related("created_by")
            .prefetch_related("tags")
            .order_by("start_datetime")
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

        # Check if exporting a specific occurrence
        occurrence_date = request.GET.get("date")
        if occurrence_date and event.recurrences:
            try:
                start_dt = get_occurrence_start(event, occurrence_date)
            except ValueError:
                return Http404("%s is not a valid date for recurring event '%e': '%s'", occurrence_date, event.name)

            end_dt = None
            if event.end_datetime:
                duration = event.end_datetime - event.start_datetime
                end_dt = start_dt + duration

        else:
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
                ics_lines.append(f"GEO:{event.location.latitude};{event.location.longitude}")
                # Add map link for Apple devices
                apple_location = (
                    f'X-APPLE-STRUCTURED-LOCATION;VALUE=URI;'
                    f'X-ADDRESS="{location_str.replace("\\n", " ").replace("\\,", ",")}";'
                    f'X-TITLE={event.location.name}:'
                    f'geo:{event.location.latitude},{event.location.longitude}'
                )
                ics_lines.append(apple_location)

        if event.webpage_url:
            ics_lines.append(f"URL:{event.webpage_url}")

        # Add recurrence rule if this is a recurring event
        if event.recurrences and event.recurrences.rrules:
            rrule = event.recurrences.rrules[0].to_dateutil_rrule()
            ics_lines.append(str(rrule).split("\n")[1])

        ics_lines.extend([
            "END:VEVENT",
            "END:VCALENDAR",
        ])

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

    def form_valid(self, form):
        """Set the created_by field to the current user."""
        form.instance.created_by = self.request.user
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
        return context
