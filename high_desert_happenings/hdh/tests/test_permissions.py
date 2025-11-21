# ruff: noqa: S106

"""
Tests for event and location permissions.
"""

from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from high_desert_happenings.hdh.models import Event, Location
from high_desert_happenings.hdh.views import EventUpdateView, LocationUpdateView

User = get_user_model()


class PermissionsTestBase(TestCase):
    """Base class with common test data setup."""

    @classmethod
    def setUpTestData(cls):
        """Set up test users, location, and event that are shared across all tests."""
        # Create test users
        cls.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="testpass123",
        )
        cls.other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="testpass123",
        )
        cls.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )

        # Create a test location
        cls.test_location = Location.objects.create(
            name="Test Location",
            address="123 Test St",
            city="Joshua Tree",
            state="CA",
        )

        # Create a test event
        cls.test_event = Event.objects.create(
            name="Test Event",
            description="Test Description",
            location=cls.test_location,
            start_datetime=timezone.now() + timezone.timedelta(days=1),
            end_datetime=timezone.now() + timezone.timedelta(days=1, hours=2),
            created_by=cls.owner,
        )

    def setUp(self):
        """Set up request factory for each test."""
        self.factory = RequestFactory()


class EventPermissionsTest(PermissionsTestBase):
    """Test permissions for event management."""

    def test_owner_can_edit_own_event(self):
        """Test that event owner can edit their own event."""
        request = self.factory.get(reverse("event_edit", kwargs={"pk": self.test_event.pk}))
        request.user = self.owner

        view = EventUpdateView()
        view.request = request
        view.kwargs = {"pk": self.test_event.pk}
        view.object = self.test_event

        assert view.test_func()

    def test_other_user_cannot_edit_event(self):
        """Test that users cannot edit events created by others."""
        request = self.factory.get(reverse("event_edit", kwargs={"pk": self.test_event.pk}))
        request.user = self.other_user

        view = EventUpdateView()
        view.request = request
        view.kwargs = {"pk": self.test_event.pk}
        view.object = self.test_event

        assert not view.test_func()

    def test_staff_can_edit_any_event(self):
        """Test that staff users can edit any event."""
        request = self.factory.get(reverse("event_edit", kwargs={"pk": self.test_event.pk}))
        request.user = self.staff_user

        view = EventUpdateView()
        view.request = request
        view.kwargs = {"pk": self.test_event.pk}
        view.object = self.test_event

        assert view.test_func()

    def test_unauthenticated_user_cannot_edit_event(self):
        """Test that unauthenticated users cannot edit events."""
        request = self.factory.get(reverse("event_edit", kwargs={"pk": self.test_event.pk}))
        request.user = AnonymousUser()

        view = EventUpdateView()
        view.request = request
        view.kwargs = {"pk": self.test_event.pk}
        view.object = self.test_event

        assert not view.test_func()

    def test_authenticated_user_can_create_event(self):
        """Test that any authenticated user can create a new event."""
        request = self.factory.get(reverse("event_create"))
        request.user = self.other_user

        view = EventUpdateView()
        view.request = request
        view.kwargs = {}  # No pk means create

        assert view.test_func()

    def test_unauthenticated_user_cannot_create_event(self):
        """Test that unauthenticated users cannot create events."""
        request = self.factory.get(reverse("event_create"))
        request.user = AnonymousUser()

        view = EventUpdateView()
        view.request = request
        view.kwargs = {}  # No pk means create

        assert not view.test_func()


class EventPermissionsIntegrationTest(PermissionsTestBase):
    """Integration tests for event permissions using the actual views."""

    def test_owner_can_access_edit_page(self):
        """Test that event owner can access the edit page."""
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(reverse("event_edit", kwargs={"pk": self.test_event.pk}))
        assert response.status_code == HTTPStatus.OK

    @override_settings(DEBUG=False)
    def test_other_user_cannot_access_edit_page(self):
        """Test that other users are denied access to edit page."""
        with self.assertLogs("django.request", level="WARNING"):
            self.client.login(username="other", password="testpass123")
            response = self.client.get(reverse("event_edit", kwargs={"pk": self.test_event.pk}))
            assert response.status_code == HTTPStatus.FORBIDDEN

    def test_unauthenticated_user_redirected_from_edit_page(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(reverse("event_edit", kwargs={"pk": self.test_event.pk}))
        assert response.status_code == HTTPStatus.FOUND
        assert "/accounts/login/" in response.url


class LocationPermissionsTest(PermissionsTestBase):
    """Test permissions for location management."""

    def setUp(self):
        """Set up test location for each test."""
        super().setUp()
        # Create a test location with owner
        self.location = Location.objects.create(
            name="Test Location Owned",
            address="456 Owner St",
            city="Joshua Tree",
            state="CA",
            owner=self.owner,
        )

    def test_owner_can_edit_own_location(self):
        """Test that location owner can edit their own location."""
        request = self.factory.get(reverse("location_edit", kwargs={"pk": self.location.pk}))
        request.user = self.owner

        view = LocationUpdateView()
        view.request = request
        view.kwargs = {"pk": self.location.pk}
        view.object = self.location

        assert view.test_func()

    def test_other_user_cannot_edit_location(self):
        """Test that users cannot edit locations owned by others."""
        request = self.factory.get(reverse("location_edit", kwargs={"pk": self.location.pk}))
        request.user = self.other_user

        view = LocationUpdateView()
        view.request = request
        view.kwargs = {"pk": self.location.pk}
        view.object = self.location

        assert not view.test_func()

    def test_staff_can_edit_any_location(self):
        """Test that staff users can edit any location."""
        request = self.factory.get(reverse("location_edit", kwargs={"pk": self.location.pk}))
        request.user = self.staff_user

        view = LocationUpdateView()
        view.request = request
        view.kwargs = {"pk": self.location.pk}
        view.object = self.location

        assert view.test_func()

    def test_unauthenticated_user_cannot_edit_location(self):
        """Test that unauthenticated users cannot edit locations."""
        request = self.factory.get(reverse("location_edit", kwargs={"pk": self.location.pk}))
        request.user = AnonymousUser()

        view = LocationUpdateView()
        view.request = request
        view.kwargs = {"pk": self.location.pk}
        view.object = self.location

        assert not view.test_func()

    def test_authenticated_user_can_create_location(self):
        """Test that any authenticated user can create a new location."""
        request = self.factory.get(reverse("location_create"))
        request.user = self.other_user

        view = LocationUpdateView()
        view.request = request
        view.kwargs = {}  # No pk means create

        assert view.test_func()

    def test_unauthenticated_user_cannot_create_location(self):
        """Test that unauthenticated users cannot create locations."""
        request = self.factory.get(reverse("location_create"))
        request.user = AnonymousUser()

        view = LocationUpdateView()
        view.request = request
        view.kwargs = {}  # No pk means create

        assert not view.test_func()


class LocationPermissionsIntegrationTest(PermissionsTestBase):
    """Integration tests for location permissions using the actual views."""

    def setUp(self):
        """Set up test location for each test."""
        super().setUp()
        self.location = Location.objects.create(
            name="Test Location With Owner",
            address="456 Owner St",
            city="Joshua Tree",
            state="CA",
            owner=self.owner,
        )

    def test_owner_can_access_edit_page(self):
        """Test that location owner can access the edit page."""
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(reverse("location_edit", kwargs={"pk": self.location.pk}))
        assert response.status_code == HTTPStatus.OK

    @override_settings(DEBUG=False)
    def test_other_user_cannot_access_edit_page(self):
        """Test that other users are denied access to edit page."""
        with self.assertLogs("django.request", level="WARNING"):
            self.client.login(username="other", password="testpass123")
            response = self.client.get(reverse("location_edit", kwargs={"pk": self.location.pk}))
            assert response.status_code == HTTPStatus.FORBIDDEN

    def test_unauthenticated_user_redirected_from_edit_page(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(reverse("location_edit", kwargs={"pk": self.location.pk}))
        assert response.status_code == HTTPStatus.FOUND
        assert "/accounts/login/" in response.url
