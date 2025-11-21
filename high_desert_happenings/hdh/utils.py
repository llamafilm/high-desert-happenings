"""Utility functions for the HDH app."""

import html
import re
from datetime import datetime

from django.utils import timezone
from markdownx.utils import markdownify

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


def markdown_to_text(markdown_content: str) -> str:
    """Convert markdown content to plain text by stripping HTML tags."""

    rendered_html = markdownify(markdown_content)
    # Create plain text version: convert HTML to text with preserved spacing
    text = rendered_html
    # Replace block-level tags with newlines
    text = re.sub(r"</?(p|div|h[1-6]|li|br)\s*/?>", "\n", text)
    # Remove all other HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities
    text = html.unescape(text)
    # Clean up multiple newlines
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()
