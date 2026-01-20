from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APIClient
from rest_framework import status

from airport.models import AirplaneType, Airplane, Route, Flight, Airport, Crew
from airport.serializers import FlightListSerializer, FlightDetailSerializer
from airport.views import FlightViewSet

# URL for the flight list endpoint
FLIGHT_URL = reverse("airport:flight-list")


def detail_url(flight_id):
    """Helper to generate the URL for a specific flight detail view."""
    return reverse("airport:flight-detail", args=[flight_id])


def sample_airplane(**params):
    """
    Helper to create an Airplane.
    Uses get_or_create for AirplaneType to avoid unique constraint violations.
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


def sample_route(**params):
    """
    Helper to create a Route.
    Uses get_or_create for Airports to avoid unique constraint violations.
    """
    airport1, _ = Airport.objects.get_or_create(
        name="Testa aiport1",
        defaults={"closest_big_city": "test city1"}
    )
    airport2, _ = Airport.objects.get_or_create(
        name="Testa aiport2",
        defaults={"closest_big_city": "test city2"}
    )

    defaults = {
        "source": airport1,
        "destination": airport2,
        "distance": 1234
    }
    defaults.update(params)

    return Route.objects.create(**defaults)


def sample_flight(**params):
    """
    Helper to create a Flight.
    Automatically creates dependencies (Route, Airplane) if not provided.
    """
    route = sample_route()
    airplane = sample_airplane()

    defaults = {
        "route": route,
        "airplane": airplane,
        "departure_time": timezone.make_aware(
            datetime(2026, 6, 2, 14, 0, 0)
        ),
        "arrival_time": timezone.make_aware(
            datetime(2026, 6, 2, 16, 0, 0)
        ),
    }
    defaults.update(params)

    return Flight.objects.create(**defaults)


class UnauthenticatedFlightApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required to access the flight list."""
        res = self.client.get(FLIGHT_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedFlightApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass123"
        )
        self.client.force_authenticate(self.user)

    def test_list_flights(self):
        """Test retrieving a list of flights."""
        sample_flight()
        sample_flight()

        res = self.client.get(FLIGHT_URL)

        # Retrieve expected data from DB
        flights = FlightViewSet.queryset.order_by("id")
        serializer = FlightListSerializer(flights, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_flight_by_airplane_id(self):
        """Test filtering flights by the airplane ID."""
        airplane1 = sample_airplane(name="Plane One")
        airplane2 = sample_airplane(name="Plane Two")

        flight1 = sample_flight(airplane=airplane1)
        flight2 = sample_flight(airplane=airplane2)

        res = self.client.get(FLIGHT_URL, {"airplane": f"{airplane1.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        returned_ids = [item["id"] for item in res.data]

        self.assertIn(flight1.id, returned_ids)
        self.assertNotIn(flight2.id, returned_ids)

    def test_filter_flight_by_source_name(self):
        """Test filtering flights by the source airport name."""
        airport_src1 = Airport.objects.create(
            name="Source 1", closest_big_city="City 1"
        )
        airport_src2 = Airport.objects.create(
            name="Source 2", closest_big_city="City 2"
        )

        route1 = sample_route(source=airport_src1)
        route2 = sample_route(source=airport_src2)

        flight1 = sample_flight(route=route1)
        flight2 = sample_flight(route=route2)

        res = self.client.get(FLIGHT_URL, {"source": route1.source.name})

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        returned_ids = [item["id"] for item in res.data]

        self.assertIn(flight1.id, returned_ids)
        self.assertNotIn(flight2.id, returned_ids)

    def test_filter_flight_by_destination_name(self):
        """Test filtering flights by the destination airport name."""
        airport_dest1 = Airport.objects.create(
            name="Dest 1", closest_big_city="City 1"
        )
        airport_dest2 = Airport.objects.create(
            name="Dest 2", closest_big_city="City 2"
        )

        route1 = sample_route(destination=airport_dest1)
        route2 = sample_route(destination=airport_dest2)

        flight1 = sample_flight(route=route1)
        flight2 = sample_flight(route=route2)

        res = self.client.get(FLIGHT_URL, {"destination": route1.destination.name})

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        returned_ids = [item["id"] for item in res.data]

        self.assertIn(flight1.id, returned_ids)
        self.assertNotIn(flight2.id, returned_ids)

    def test_retrieve_flight_detail(self):
        """Test retrieving the details of a specific flight."""
        flight = sample_flight()

        url = detail_url(flight.id)
        res = self.client.get(url)

        serializer = FlightDetailSerializer(flight)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_flight_forbidden(self):
        """Test that regular users cannot create flights."""
        route = sample_route()
        airplane = sample_airplane()

        payload = {
            "route": route.id,
            "airplane": airplane.id,
            "departure_time": "2026-06-02T14:00:00Z",
            "arrival_time": "2026-06-02T16:00:00Z",
        }

        res = self.client.post(FLIGHT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminFlightApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com", "testpass", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_flight(self):
        """Test that admin users can create flights."""
        route = sample_route()
        airplane = sample_airplane()

        payload = {
            "route": route.id,
            "airplane": airplane.id,
            "departure_time": "2026-06-02T14:00:00Z",
            "arrival_time": "2026-06-02T16:00:00Z",
        }

        res = self.client.post(FLIGHT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        flight = Flight.objects.get(id=res.data["id"])

        self.assertEqual(flight.route.id, payload["route"])
        self.assertEqual(flight.airplane.id, payload["airplane"])

    def test_create_flight_with_crew(self):
        """Test creating a flight and assigning crew members to it."""
        route = sample_route()
        airplane = sample_airplane()
        crew1 = Crew.objects.create(first_name="Ivan", last_name="Petrovich")
        crew2 = Crew.objects.create(first_name="Alina", last_name="Vasilievna")

        payload = {
            "route": route.id,
            "airplane": airplane.id,
            "departure_time": "2026-06-02T14:00:00Z",
            "arrival_time": "2026-06-02T16:00:00Z",
            "crew": [crew1.id, crew2.id],
        }

        res = self.client.post(FLIGHT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        flight = Flight.objects.get(id=res.data["id"])

        # Check that crew members were correctly assigned
        crew_ids = flight.crew.values_list("id", flat=True)
        self.assertEqual(list(crew_ids), payload["crew"])
        self.assertEqual(flight.crew.count(), 2)

    def test_put_flight_allowed(self):
        """Test that admin users can update flight details."""
        new_airport = Airport.objects.create(
            name="Testa matros2", closest_big_city="test kobalt"
        )
        route = sample_route(destination=new_airport)
        airplane = sample_airplane(name="Testing Kaktus JO")

        payload = {
            "route": route.id,
            "airplane": airplane.id,
            "departure_time": "2026-06-02T14:00:00Z",
            "arrival_time": "2026-06-02T16:00:00Z",
        }

        flight = sample_flight()
        url = detail_url(flight.id)

        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        flight.refresh_from_db()

        self.assertEqual(flight.route.id, route.id)
        self.assertEqual(flight.airplane.id, airplane.id)

    def test_delete_flight_allowed(self):
        """Test that admin users can delete flights."""
        flight = sample_flight()
        url = detail_url(flight.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Flight.objects.filter(id=flight.id).exists())