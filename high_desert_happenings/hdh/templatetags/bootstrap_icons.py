from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()

icon_dir = f"{settings.STATICFILES_DIRS[0]}/icons"


@register.simple_tag
def icon(name, css_class="", style=""):
    """Renders an inline SVG icon from static/icons/ with optional custom class and style"""

    with open(f"{icon_dir}/{name}.svg") as f:  # noqa: PTH123
        svg_content = f.read()

    if css_class:
        svg_content = svg_content.replace("<svg ", f'<svg class="{css_class}" ', 1)

    if style:
        svg_content = svg_content.replace("<svg ", f'<svg style="{style}" ', 1)

    return mark_safe(svg_content)  # noqa: S308
