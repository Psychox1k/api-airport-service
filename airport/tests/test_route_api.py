from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from airport.models import Airport, Route
from airport.serializers import RouteListSerializer, RouteDetailSerializer
from airport.views import RouteViewSet

# URL for the route list endpoint
ROUTE_URL = reverse("airport:route-list")


def detail_url(route_id):
    """Helper to generate the URL for a specific route detail view."""
    return reverse("airport:route-detail", args=[route_id])


def sample_route(**params):
    """
    Helper function to create a Route instance.
    Uses get_or_create for airports to prevent UniqueConstraint errors
    if the function is called multiple times in one test.
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


class UnauthenticatedRouteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required to access the route list."""
        res = self.client.get(ROUTE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedRouteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass123"
        )
        self.client.force_authenticate(self.user)

    def test_list_routes(self):
        """Test retrieving a list of routes."""
        sample_route()
        sample_route()

        res = self.client.get(ROUTE_URL)

        # Retrieve expected data from DB, ordered by ID
        routes = Route.objects.all().order_by("id")
        serializer = RouteListSerializer(routes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_route_by_distance_min(self):
        """
        Test filtering routes by minimum distance.
        Routes with distance >= min should be returned.
        """
        route1 = sample_route(distance=1234) # Matches (> 900)
        route2 = sample_route(distance=900)  # Matches (= 900)
        route3 = sample_route(distance=800)  # Excluded (< 900)

        res = self.client.get(ROUTE_URL, {"distance_min": "900"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        serializer1 = RouteListSerializer(route1)
        serializer2 = RouteListSerializer(route2)
        serializer3 = RouteListSerializer(route3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_route_by_distance_max(self):
        """
        Test filtering routes by maximum distance.
        Routes with distance <= max should be returned.
        """
        route1 = sample_route(distance=1234) # Excluded (> 900)
        route2 = sample_route(distance=700)  # Matches (< 900)
        route3 = sample_route(distance=800)  # Matches (< 900)

        res = self.client.get(ROUTE_URL, {"distance_max": "900"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        serializer1 = RouteListSerializer(route1)
        serializer2 = RouteListSerializer(route2)
        serializer3 = RouteListSerializer(route3)

        self.assertIn(serializer3.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer1.data, res.data)

    def test_retrieve_route_detail(self):
        """Test retrieving the details of a specific route."""
        route = sample_route()

        url = detail_url(route.id)
        res = self.client.get(url)

        serializer = RouteDetailSerializer(route)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_route_forbidden(self):
        """Test that regular users cannot create routes."""
        airport1 = Airport.objects.create(
            name="Testa aiport1", closest_big_city="test city1"
        )
        airport2 = Airport.objects.create(
            name="Testa aiport2", closest_big_city="test city2"
        )

        payload = {
            "source": airport1.id,
            "destination": airport2.id,
            "distance": 900,
        }

        res = self.client.post(ROUTE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminRouteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com", "testpass", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_route_invalid_data(self):
        """Test validation: creating a route without a source should fail."""
        airport2 = Airport.objects.create(
            name="Testa aiport2", closest_big_city="test city2"
        )

        # Missing 'source' field
        payload = {
            "destination": airport2.id,
            "distance": 900,
        }

        res = self.client.post(ROUTE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_route(self):
        """Test that admin users can create routes."""
        airport1 = Airport.objects.create(
            name="Testa aiport1", closest_big_city="test city1"
        )
        airport2 = Airport.objects.create(
            name="Testa aiport2", closest_big_city="test city2"
        )

        payload = {
            "source": airport1.id,
            "destination": airport2.id,
            "distance": 900,
        }

        res = self.client.post(ROUTE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_put_route_allowed(self):
        """
        Test that admin users can update routes using PUT.
        Note: PUT requires all fields to be present.
        """
        route = sample_route()

        url = detail_url(route.id)

        payload = {
            "source": route.source.id,
            "destination": route.destination.id,
            "distance": 892,
        }
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_delete_route_allowed(self):
        """Test that admin users can delete routes."""
        route = sample_route()

        url = detail_url(route.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Route.objects.filter(id=route.id).exists())