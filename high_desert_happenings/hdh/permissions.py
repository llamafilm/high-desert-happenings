"""
This module defines custom permission classes and mixins for controlling
access to events and locations.
"""

from django.contrib.auth.mixins import UserPassesTestMixin


class CanManageEventMixin(UserPassesTestMixin):
    """
    Mixin to check if user can manage (create/edit/delete) an event.

    Staff and superusers can manage any event.
    Event creators can edit/delete their own events.
    All authenticated users can create new events.
    """

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False

        # Staff and superusers can manage any event
        if user.is_staff or user.is_superuser:
            return True

        # Create
        if self.kwargs.get("pk") is None:
            return True

        # Edit/delete
        event = self.get_object()
        return event.created_by == user


class CanManageLocationMixin(UserPassesTestMixin):
    """
    Mixin to check if user can manage (create/edit/delete) locations.

    Staff and superusers can manage any location.
    Location owners can edit/delete their own locations.
    All authenticated users can create new locations.
    """

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False

        # Staff and superusers can manage any location
        if user.is_staff or user.is_superuser:
            return True

        # Create
        if self.kwargs.get("pk") is None:
            return True

        # Edit/delete
        location = self.get_object()
        return location.owner == user
