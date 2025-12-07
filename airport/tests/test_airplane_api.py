from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from airport.models import AirplaneType, Airplane
from airport.serializers import AirplaneListSerializer, AirplaneDetailSerializer
from airport.views import AirplaneViewSet

AIRPLANE_URL = reverse("airport:airplane-list")


def detail_url(airplane_id):
    """Helper to generate the URL for a specific airplane detail view."""
    return reverse("airport:airplane-detail", args=[airplane_id])


def sample_airplane(**params):
    """
    Helper function to create an Airplane instance.
    If 'airplane_type' is not provided, it gets or creates a default one
    to avoid IntegrityError (unique constraint violations).
    """
    defaults = {
        "name": "test boeing",
        "rows": 12,
        "seats_in_row": 12,
    }

    if "airplane_type" not in params:
        airplane_type, _ = AirplaneType.objects.get_or_create(
            name="Test TypeBoeing"
        )
        defaults["airplane_type"] = airplane_type

    defaults.update(params)

    return Airplane.objects.create(**defaults)


class UnauthenticatedAirplaneApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required to access the airplane list."""
        res = self.client.get(AIRPLANE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAirplaneApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass123"
        )
        self.client.force_authenticate(self.user)

    def test_list_airplane(self):
        """Test retrieving a list of airplanes."""
        sample_airplane()
        sample_airplane()

        res = self.client.get(AIRPLANE_URL)

        # Retrieve expected data from DB, ordered by ID
        airplanes = Airplane.objects.all().order_by("id")
        serializer = AirplaneListSerializer(airplanes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_airplane_detail(self):
        """Test retrieving the details of a specific airplane."""
        airplane = sample_airplane()

        url = detail_url(airplane.id)
        res = self.client.get(url)

        serializer = AirplaneDetailSerializer(airplane)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_airplane_by_airplane_type(self):
        """Test filtering airplanes by their type name."""
        type1 = AirplaneType.objects.create(name="Boeing")
        type2 = AirplaneType.objects.create(name="Airbus")

        airplane1 = sample_airplane(airplane_type=type1, name="Plane 1")
        airplane2 = sample_airplane(airplane_type=type2, name="Plane 2")

        # Filter by 'Boeing'
        res = self.client.get(AIRPLANE_URL, {"airplane_type": type1.name})

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        serializer1 = AirplaneListSerializer(airplane1)
        serializer2 = AirplaneListSerializer(airplane2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_airplane_by_name(self):
        """Test filtering airplanes by their name."""
        airplane1 = sample_airplane(name="Mriya")
        airplane2 = sample_airplane(name="Cornpicker")

        res = self.client.get(AIRPLANE_URL, {"name": airplane1.name})

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        serializer1 = AirplaneListSerializer(airplane1)
        serializer2 = AirplaneListSerializer(airplane2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_create_airplane_forbidden(self):
        """Test that regular users cannot create airplanes."""
        airplane_type = AirplaneType.objects.create(name="Test")
        payload = {
            "name": "Forbidden Plane",
            "rows": 10,
            "seats_in_row": 6,
            "airplane_type": airplane_type.id,
        }

        res = self.client.post(AIRPLANE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAirplaneApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com", "testpass", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_airplane_allowed(self):
        """Test that admin users can create airplanes."""
        airplane_type = AirplaneType.objects.create(name="Embraer")

        payload = {
            "name": "Embraer E195",
            "rows": 20,
            "seats_in_row": 4,
            "airplane_type": airplane_type.id,
        }

        res = self.client.post(AIRPLANE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        airplane = Airplane.objects.get(id=res.data["id"])

        self.assertEqual(airplane.name, payload["name"])
        self.assertEqual(airplane.rows, payload["rows"])
        self.assertEqual(airplane.seats_in_row, payload["seats_in_row"])
        self.assertEqual(airplane.airplane_type.id, airplane_type.id)

    def test_create_airplane_invalid_data(self):
        """Test that creating an airplane with invalid data (e.g., rows=0) fails."""
        airplane_type = AirplaneType.objects.create(name="Embraer Invalid")

        payload = {
            "name": "Bad Plane",
            "rows": 0,  # Invalid: must be at least 1
            "seats_in_row": 4,
            "airplane_type": airplane_type.id,
        }

        res = self.client.post(AIRPLANE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_airplane_not_allowed(self):
        """
        Test that PUT requests are not allowed.
        The ViewSet does not have UpdateModelMixin, so it should return 405.
        """
        airplane = sample_airplane()

        url = detail_url(airplane.id)

        payload = {
            "name": "Updated Name",
        }

        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_airplane_not_allowed(self):
        """
        Test that DELETE requests are not allowed.
        The ViewSet does not have DestroyModelMixin, so it should return 405.
        """
        airplane = sample_airplane()
        url = detail_url(airplane.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)