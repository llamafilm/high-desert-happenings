import re

from django import template
from django.utils import timezone

register = template.Library()


def autolink_urls(text):
    """Convert plain URLs to HTML links before markdown processing."""
    # Pattern to match URLs that aren't already in markdown link format
    # Looks for http(s):// URLs not preceded by ]( or followed by )
    url_pattern = r'(?<!\]\()(?<!\()(https?://[^\s<>"{}|\\^`\[\]]+)(?!\))'
    return re.sub(url_pattern, r"<\1>", text)


@register.filter(name="first_word")
def first_word(value):
    """Return the first word of a string, removing any commas."""
    if not value:
        return ""
    first = str(value).split()[0] if value.split() else ""
    return first.replace(",", "")


@register.filter(name="friendly_time")
def friendly_time(datetime_value):
    """Format time as '3pm' or '3:30pm' (omit minutes if :00)."""
    if not datetime_value:
        return ""
    hour = datetime_value.strftime("%I").lstrip("0")
    minute = datetime_value.strftime("%M")
    period = datetime_value.strftime("%p").lower()

    if minute == "00":
        return f"{hour}{period}"
    return f"{hour}:{minute}{period}"


@register.filter(name="friendly_datetime")
def friendly_datetime(datetime_value):
    """Format datetime as 'November 19 at 3pm' or 'November 19 at 3:30pm'.
    Converts to local timezone before formatting."""
    if not datetime_value:
        return ""
    # Convert to local timezone
    local_datetime = timezone.localtime(datetime_value)
    date_part = local_datetime.strftime("%B %-d")
    time_part = friendly_time(local_datetime)
    return f"{date_part} at {time_part}"
