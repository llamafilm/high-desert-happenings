from django import forms
from markdownx.fields import MarkdownxFormField
from markdownx.widgets import MarkdownxWidget
from recurrence.forms import RecurrenceField

from .models import Event
from .models import Location


class EventForm(forms.ModelForm):
    """Form for creating and editing events."""

    styled_description = MarkdownxFormField(
        required=False,
        widget=MarkdownxWidget(attrs={"rows": 10, "cols": 80}),
    )

    # Recurrence field uses its own nice UI
    recurrence_pattern = RecurrenceField(
        required=False,
        label="Recurrence Pattern",
        help_text="Define a recurring pattern to create multiple events. Leave blank for a single event.",
    )

    class Meta:
        model = Event
        fields = [
            "title",
            "description",
            "styled_description",
            "image",
            "location",
            "start_datetime",
            "end_datetime",
            "recurrence_pattern",
            "webpage_url",
            "is_free",
            "age_restriction",
            "tags",
        ]
        widgets = {
            "start_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "end_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "description": forms.Textarea(attrs={"cols": 40, "rows": 10}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["styled_description"].help_text = "Markdown syntax is supported"
        # Set input formats to exclude seconds
        self.fields["start_datetime"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["end_datetime"].input_formats = ["%Y-%m-%dT%H:%M"]

        # Hide recurrence field when editing an existing event
        if self.instance.pk:
            self.fields.pop("create_recurrence", None)


class LocationForm(forms.ModelForm):
    """Form for creating and editing locations."""

    class Meta:
        model = Location
        fields = [
            "name",
            "address",
            "city",
            "state",
            "zip_code",
            "neighborhood",
            "phone_number",
            "website",
            "image",
            "dogs_allowed",
            "latitude",
            "longitude",
        ]
        widgets = {
            "latitude": forms.NumberInput(attrs={"step": "0.000001"}),
            "longitude": forms.NumberInput(attrs={"step": "0.000001"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["latitude"].help_text = "Leave blank to geocode from address"
        self.fields["longitude"].help_text = "Leave blank to geocode from address"
