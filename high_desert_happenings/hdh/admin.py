from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Event, Location, Tag


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ["name", "neighborhood", "website"]
    list_filter = ["neighborhood"]
    search_fields = ["name", "neighborhood", "phone_number"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "neighborhood",
                    "address",
                    "city",
                    "state",
                    "zip_code",
                    "phone_number",
                    "website",
                    "dogs_allowed",
                    "image",
                    "owner",
                ),
            },
        ),
        (
            _("Coordinates"),
            {
                "fields": ("latitude", "longitude"),
                "description": _(
                    "Coordinates are automatically geocoded when the location is saved.",
                ),
            },
        ),
    )


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "location",
        "start_datetime",
        "created_by",
        "series_display",
    ]
    list_filter = ["start_datetime", "location", "tags", "created_by"]
    search_fields = ["name", "description", "location__name", "created_by__username"]
    date_hierarchy = "start_datetime"
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "description",
                    "image",
                    "location",
                    "start_datetime",
                    "end_datetime",
                    "webpage_url",
                    "is_free",
                    "tags",
                ),
            },
        ),
        (
            _("Series Information"),
            {
                "fields": ("series_id", "parent_event"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Metadata"),
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(
        description="Series",
    )
    def series_display(self, obj):
        """Display whether event is part of a series."""
        if obj.is_part_of_series():
            series_events = obj.get_series_events()
            return f"Part of series ({series_events.count()} events)"
        return "-"

    @admin.display(
        description="Tags",
    )
    def tag_list(self, obj):
        return ", ".join(o.name for o in obj.tags.all())

    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by when creating a new event
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        readonly = ["created_at", "updated_at", "series_id", "parent_event"]
        if obj:  # Editing an existing object
            readonly.append("created_by")
        return readonly


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "description"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ["name"]}
    fields = ["name", "slug", "description"]
