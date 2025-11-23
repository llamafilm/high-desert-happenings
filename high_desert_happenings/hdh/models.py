import logging
import uuid
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import requests
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from localflavor.us.models import USStateField
from markdownx.models import MarkdownxField

logger = logging.getLogger(__name__)


def location_image_path(instance, filename):
    """Generate upload path for location images."""
    ext = Path(filename).suffix
    slug = slugify(instance.name)
    return f"locations/{instance.pk}_{slug}{ext}"


def image_upload(instance, filename):
    """Return a path for uploading image attachments."""

    # Rename the file and preserve the extension
    extension = filename.rsplit(".")[-1].lower()
    filename = instance.name or "no-name"
    if extension in ["bmp", "gif", "jpeg", "jpg", "png", "webp"]:
        filename = f"{instance.name}.{extension}"

    return f"image-attachments/{instance.object_type.name}_{instance.object_id}_{filename}"


class Tag(models.Model):
    """Tag model for categorizing events."""

    name = models.CharField(_("Name"), max_length=100, unique=True)
    slug = models.SlugField(_("Slug"), max_length=100, unique=True)
    description = models.TextField(_("Description"), blank=True)

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Location(models.Model):
    """Model for event locations."""

    name = models.CharField(_("Name"), max_length=100)
    address = models.CharField(_("Street Address"), max_length=200, blank=True)
    city = models.CharField(_("City"), max_length=100, blank=True)
    state = USStateField(_("State"), blank=True)
    zip_code = models.CharField(_("ZIP Code"), max_length=10, blank=True)
    latitude = models.DecimalField(
        _("Latitude"),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        _("Longitude"),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    phone_number = models.CharField(_("Phone Number"), max_length=20, blank=True)
    website = models.URLField(_("Website"), max_length=500, blank=True)
    image = models.ImageField(
        _("Image"),
        upload_to=location_image_path,
        blank=True,
        null=True,
        help_text=_("Location image"),
    )

    NEIGHBORHOOD_CHOICES = [
        ("", ""),
        ("joshua-tree", _("Joshua Tree")),
        ("29-palms", _("29 Palms")),
        ("wonder-valley", _("Wonder Valley")),
        ("pioneertown", _("Pioneertown")),
        ("landers", _("Landers")),
        ("yucca-valley", _("Yucca Valley")),
        ("morongo-valley", _("Morongo Valley")),
        ("mcagcc", _("20 Palms Marine Corps Base")),
    ]
    neighborhood = models.CharField(
        _("Neighborhood"),
        max_length=30,
        choices=NEIGHBORHOOD_CHOICES,
        blank=True,
    )
    dogs_allowed = models.BooleanField(
        _("Dogs Allowed"),
        null=True,
        blank=True,
        help_text=_("Check if dogs are allowed at this location"),
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_locations",
        verbose_name=_("Owner"),
    )

    class Meta:
        verbose_name = _("Location")
        verbose_name_plural = _("Locations")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """Return the URL to view this location."""
        return reverse("location_detail", kwargs={"pk": self.pk})

    @property
    def full_address(self) -> str:
        """Return formatted full address string."""
        full_address = ""
        if self.address:
            full_address += f"{self.address}"
        if self.city:
            full_address += f", {self.city}"
        if self.state:
            full_address += f", {self.state}"
        if self.zip_code:
            full_address += f" {self.zip_code}"
        return full_address

    def save(self, *args, **kwargs):  # noqa: DJ012
        """Automatically geocode location if coordinates are missing."""
        if not self.latitude or not self.longitude:
            self._geocode()
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        """Validate and round coordinates to 6 decimal places."""
        if self.latitude is not None:
            self.latitude = Decimal(str(self.latitude)).quantize(
                Decimal("0.000001"),
                rounding=ROUND_HALF_UP,
            )

        if self.longitude is not None:
            self.longitude = Decimal(str(self.longitude)).quantize(
                Decimal("0.000001"),
                rounding=ROUND_HALF_UP,
            )

    def _geocode(self):
        """Geocode the location using OpenStreetMap Nominatim."""

        logger.debug("Geocoding location %s: %s, %s", self.pk, self.name, self.address)

        url = "https://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": "HighDesertHappenings/1.0"}
        params = {
            "street": self.address,
            "city": self.city,
            "state": self.state,
            "postalcode": self.zip_code,
            "countrycodes": "us",
            "format": "json",
            "limit": 1,
        }

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.debug("Geocoding response data: %s", data)

        except requests.RequestException as e:
            logger.warning("Failed to geocode location '%s': %s", self.name, str(e))
            return

        if data:
            self.latitude = Decimal(data[0]["lat"])
            self.longitude = Decimal(data[0]["lon"])
            logger.info("Geocoded location: %s -> (%s, %s)", self.name, self.latitude, self.longitude)


class Event(models.Model):
    """Model for events."""

    name = models.CharField(_("Name"), max_length=100)
    description = MarkdownxField(_("Description"), blank=True)
    image = models.ImageField(
        _("Image"),
        upload_to="events/images/%Y/%m/",
        blank=True,
        null=True,
        help_text=_("Event image"),
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
        verbose_name=_("Location"),
    )
    start_datetime = models.DateTimeField(_("Start Date & Time"))
    end_datetime = models.DateTimeField(_("End Date & Time"), blank=True, null=True)
    webpage_url = models.URLField(_("Webpage URL"), max_length=500, blank=True)
    is_free = models.BooleanField(
        _("Free Event"),
        null=True,
        blank=True,
        help_text=_("Check if event is free to attend"),
    )

    age_restriction = models.CharField(
        _("Age Restriction"),
        max_length=10,
        choices=[("children", _("Children")), ("21plus", _("21+"))],
        blank=True,
        help_text=_("Age requirement for this event (blank = all ages)"),
    )

    # User tracking and permissions
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_events",
        verbose_name=_("Created By"),
    )
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name="events",
        verbose_name=_("Tags"),
    )

    # Series tracking for recurring events
    series_id = models.UUIDField(
        _("Series ID"),
        default=uuid.uuid4,
        editable=False,
        help_text=_("UUID identifying which events belong to the same recurring series"),
    )
    parent_event = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="recurrence_instances",
        verbose_name=_("Parent Event"),
        help_text=_("If this is a recurring event instance, reference to the parent event"),
    )

    class Meta:
        verbose_name = _("Event")
        verbose_name_plural = _("Events")
        ordering = ["start_datetime"]
        indexes = [
            models.Index(fields=["series_id"]),
            models.Index(fields=["start_datetime"]),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """Return the URL to view this event."""
        return reverse("event_detail", kwargs={"pk": self.pk})

    def is_part_of_series(self):
        """Check if this event is part of a recurring series."""
        return self.parent_event is not None or self.recurrence_instances.exists()

    def get_series_events(self):
        """Get all events in this series (including self)."""
        if self.parent_event:
            # This is a child event, get all siblings including parent
            return Event.objects.filter(
                models.Q(pk=self.parent_event.pk) | models.Q(parent_event=self.parent_event),
            ).order_by("start_datetime")
        # This is a parent event or standalone, get all children
        return Event.objects.filter(
            models.Q(pk=self.pk) | models.Q(parent_event=self),
        ).order_by("start_datetime")

    def get_future_series_events_including_self(self):
        """Get all future events in this series starting from and including this event."""
        series_events = self.get_series_events()
        return series_events.filter(start_datetime__gte=self.start_datetime)

    def get_future_series_events(self):
        """Get all future events in this series after this event."""
        series_events = self.get_series_events()
        return series_events.filter(start_datetime__gt=self.start_datetime)
