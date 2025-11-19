import logging
from decimal import ROUND_HALF_UP
from decimal import Decimal
from pathlib import Path

import requests
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from localflavor.us.models import USStateField
from markdownx.models import MarkdownxField
from recurrence.fields import RecurrenceField

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

    name = models.CharField(_("Name"), max_length=200)
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

        logger.info("Geocoding location %s: %s, %s", self.pk, self.name, self.address)

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
            logger.info("Geocoding response data: %s", data)

        except requests.RequestException as e:
            logger.warning("Failed to geocode location '%s': %s", self.name, str(e))
            return

        if data:
            self.latitude = Decimal(data[0]["lat"])
            self.longitude = Decimal(data[0]["lon"])
            logger.info("Geocoded location: %s -> (%s, %s)", self.name, self.latitude, self.longitude)


class Event(models.Model):
    """Model for events."""

    title = models.CharField(_("Title"), max_length=200)
    description = models.TextField(_("Description"), blank=True)
    styled_description = MarkdownxField(_("Styled Description"), blank=True)
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
    recurrences = RecurrenceField(
        _("Recurrences"),
        blank=True,
        null=True,
        help_text=_("Define recurring event pattern (e.g., daily, weekly, monthly)"),
    )

    class Meta:
        verbose_name = _("Event")
        verbose_name_plural = _("Events")
        ordering = ["-start_datetime"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        """Return the URL to view this event."""
        return reverse("event_detail", kwargs={"pk": self.pk})
