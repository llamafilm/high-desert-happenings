from datetime import datetime, time

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Column, Div, Field, Layout, Submit
from django import forms
from django.utils import timezone
from markdownx.fields import MarkdownxFormField
from markdownx.widgets import MarkdownxWidget
from recurrence.forms import RecurrenceField

from .models import Event, Location


class EventForm(forms.ModelForm):
    """Form for creating and editing events."""

    description = MarkdownxFormField(
        required=False,
        widget=MarkdownxWidget(attrs={"rows": 10, "cols": 80}),
        help_text="Markdown syntax is supported",
    )

    # Recurrence field uses its own nice UI
    recurrence_pattern = RecurrenceField(
        required=False,
        label="Recurrence Pattern",
        help_text="Define a recurring pattern to create multiple events. Leave blank for a single event.",
    )

    # Display datetime as separate fields
    start_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="",
    )
    start_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
        label="",
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="",
    )
    end_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
        label="",
    )
    all_day = forms.BooleanField(
        required=False,
        label="All Day Event",
    )

    # For updating recurring event series
    update_scope = forms.ChoiceField(
        required=False,
        choices=[
            ("single", "Only this event"),
            ("future", "This and all future events in the series"),
            ("all", "All events in the series"),
        ],
        widget=forms.RadioSelect,
        initial="single",
        label="",
    )

    class Meta:
        model = Event
        fields = [
            "name",
            "description",
            "image",
            "location",
            "recurrence_pattern",
            "webpage_url",
            "is_free",
            "age_restriction",
            "tags",
        ]
        widgets = {
            "tags": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        show_update_scope = kwargs.pop("show_update_scope", False)
        super().__init__(*args, **kwargs)
        self.fields["image"].help_text = ""
        self.fields["is_free"].help_text = ""

        # Setup crispy forms helper
        self.helper = FormHelper()

        # Build layout fields
        layout_fields = [
            "name",
            "description",
            "location",
            Div(
                HTML("<h6>Starts</h6>"),
                Column("start_date", css_class="col-md-3"),
                Column("start_time", css_class="col-md-3"),
                Column("all_day", css_class="col-md-4"),
                css_class="row",
            ),
            Div(
                HTML("<h6>Ends</h6>"),
                Column("end_date", css_class="col-md-3"),
                Column("end_time", css_class="col-md-3"),
                css_class="row",
            ),
            "recurrence_pattern" if not self.instance.pk else None,
            "image",
            "webpage_url",
            Column("is_free", css_class="col-md-2"),
            Column("age_restriction", css_class="col-md-2"),
            "tags",
        ]

        # Add update scope field for recurring events
        if show_update_scope:
            layout_fields.append(
                Div(
                    HTML("<h6>This event is part of a recurring series. Choose which events to update:</h6>"),
                    Field("update_scope"),
                    css_class="alert alert-info",
                ),
            )

        layout_fields.append(Submit("submit", "Save Event", css_class="btn btn-primary"))

        self.helper.layout = Layout(*layout_fields)

        # Remove update_scope field for non-recurring events
        if not show_update_scope:
            self.fields.pop("update_scope", None)

        # Different appearance when editing an existing event
        if self.instance.pk:
            # Hide recurrence field
            self.fields.pop("recurrence_pattern", None)

            # Populate date/time fields
            local_start = timezone.localtime(self.instance.start_datetime)
            self.fields["start_date"].initial = local_start.date()
            # Format time without seconds
            self.fields["start_time"].initial = local_start.strftime("%H:%M")
            self.fields["all_day"].initial = self.instance.is_all_day

            if self.instance.end_datetime:
                local_end = timezone.localtime(self.instance.end_datetime)
                self.fields["end_date"].initial = local_end.date()
                # Format time without seconds
                self.fields["end_time"].initial = local_end.strftime("%H:%M")

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        start_time = cleaned_data.get("start_time")
        end_date = cleaned_data.get("end_date")
        end_time = cleaned_data.get("end_time")

        # start & end time will be 00:00 and 23:59 for all-day events
        # Combine date and time into datetime and make timezone-aware
        naive_dt = datetime.combine(start_date, start_time or time(0, 0))
        cleaned_data["start_datetime"] = timezone.make_aware(naive_dt)

        # Only use end_date if end_time is also provided
        if end_date and end_time:
            naive_dt = datetime.combine(end_date, end_time)
            cleaned_data["end_datetime"] = timezone.make_aware(naive_dt)
        else:
            cleaned_data["end_datetime"] = None

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.start_datetime = self.cleaned_data["start_datetime"]
        instance.end_datetime = self.cleaned_data["end_datetime"]
        if commit:
            instance.save()
        return instance


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
            "phone_number": forms.TextInput(attrs={"type": "tel"}),
            "latitude": forms.NumberInput(attrs={"step": "0.000001", "inputmode": "decimal"}),
            "longitude": forms.NumberInput(attrs={"step": "0.000001", "inputmode": "decimal"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["latitude"].help_text = "Leave blank to geocode from address"
        self.fields["longitude"].help_text = "Leave blank to geocode from address"

        # Disable autofill and password manager detection on all fields
        for field in self.fields.values():
            field.widget.attrs["autocomplete"] = "off"
            field.widget.attrs["data-1p-ignore"] = "true"  # 1Password
            field.widget.attrs["data-bwignore"] = "true"  # Bitwarden
            field.widget.attrs["data-lpignore"] = "true"  # LastPass
