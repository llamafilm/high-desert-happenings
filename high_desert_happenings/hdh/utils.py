"""Utility functions for the HDH app."""

from datetime import datetime

from django.utils import timezone

from .models import Event


def get_occurrence_start(event: Event, occurrence_date: str) -> datetime | None:
    """Return the starting datetime for this occurrence of this Event.
    Raises ValueError if not found.
    """

    occurrences = event.recurrences.between(
        timezone.make_aware(datetime.strptime(occurrence_date, "%Y-%m-%d")),  # noqa: DTZ007
        timezone.make_aware(datetime.strptime(occurrence_date, "%Y-%m-%d")),  # noqa: DTZ007
        inc=True,
        dtstart=event.start_datetime,
    )

    if len(occurrences) != 1:
        msg = f"Found {len(occurrences)} occurrences for date {occurrence_date}."
        raise ValueError(msg)

    return occurrences[0]
