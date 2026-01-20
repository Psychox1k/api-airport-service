from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from airport.models import (
    Airport,
    Route,
    AirplaneType,
    Airplane,
    Flight,
    Order,
    Ticket
)
from airport.serializers import OrderListSerializer
from airport.views import OrderViewSet

# URL for the order list endpoint
ORDER_URL = reverse("airport:order-list")


def detail_url(order_id):
    """Helper to return the detail URL (if it existed)."""
    return reverse("airport:order-detail", args=[order_id])


def sample_airplane():
    """Helper to create a sample Airplane instance with specific capacity."""
    type_ = AirplaneType.objects.create(name="Boeing 737")
    return Airplane.objects.create(
        name="SkyWarrior",
        rows=10,
        seats_in_row=6,
        airplane_type=type_
    )


def sample_route():
    """Helper to create a sample Route between two airports."""
    a1 = Airport.objects.create(name="KBP", closest_big_city="Kyiv")
    a2 = Airport.objects.create(name="WAW", closest_big_city="Warsaw")
    return Route.objects.create(source=a1, destination=a2, distance=800)


def sample_flight(route, airplane):
    """Helper to create a flight scheduled for tomorrow."""
    return Flight.objects.create(
        route=route,
        airplane=airplane,
        departure_time=timezone.now() + timedelta(days=1),
        arrival_time=timezone.now() + timedelta(days=1, hours=2)
    )


class UnauthenticatedOrderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required to access orders."""
        res = self.client.get(ORDER_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedOrderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create and authenticate a user
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass123"
        )
        self.client.force_authenticate(self.user)

        # Prepare background data for tests
        self.airplane = sample_airplane()
        self.route = sample_route()
        self.flight = sample_flight(self.route, self.airplane)

    def test_create_order_with_valid_tickets(self):
        """Test creating an order with valid ticket data."""
        payload = {
            "tickets": [
                {"row": 1, "seat": 1, "flight": self.flight.id},
                {"row": 1, "seat": 2, "flight": self.flight.id},
            ]
        }

        # format='json' is required for nested lists
        res = self.client.post(ORDER_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Verify Order creation
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()

        # Verify Tickets creation
        self.assertEqual(order.tickets.count(), 2)
        tickets = order.tickets.all()

        # Check specific ticket details
        self.assertEqual(tickets[0].row, 1)
        self.assertEqual(tickets[0].seat, 1)

    def test_create_order_invalid_seat_range(self):
        """
        Test that validation fails if the seat number
         exceeds the airplane's capacity.
        Airplane has 10 rows, we try to book row 11.
        """
        payload = {
            "tickets": [
                {"row": 11, "seat": 1, "flight": self.flight.id}
            ]
        }

        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify transaction atomic: No order or tickets should be created
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(Ticket.objects.count(), 0)

    def test_create_order_duplicate_seat(self):
        """Test that booking an already taken seat is not allowed."""
        # 1. Create an initial order with a taken seat
        order1 = Order.objects.create(user=self.user)
        Ticket.objects.create(order=order1, flight=self.flight, row=1, seat=1)

        # 2. Try to book the same seat again
        payload = {
            "tickets": [
                {"row": 1, "seat": 1, "flight": self.flight.id}
            ]
        }

        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Ensure no new order was created
        self.assertEqual(Order.objects.count(), 1)

    def test_order_list(self):
        """Test retrieving the list of orders for the authenticated user."""
        order1 = Order.objects.create(user=self.user)
        order2 = Order.objects.create(user=self.user)

        Ticket.objects.create(order=order1, flight=self.flight, row=1, seat=1)
        Ticket.objects.create(order=order2, flight=self.flight, row=2, seat=3)

        res = self.client.get(ORDER_URL)

        # We must filter by user manually to match the ViewSet's get_queryset logic
        orders = Order.objects.filter(user=self.user).order_by("id")
        serializers = OrderListSerializer(orders, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializers.data)

    def test_put_order_not_allowed(self):
        """
        Test that updating a specific order is impossible.
        Since we don't have RetrieveModelMixin, the URL doesn't exist (404).
        """
        order1 = Order.objects.create(user=self.user)
        Ticket.objects.create(order=order1, flight=self.flight, row=1, seat=1)

        payload = {"tickets": []}

        # Manually construct URL since the router didn't create it
        url = f"{ORDER_URL}{order1.id}/"

        res = self.client.put(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_order_not_allowed(self):
        """
        Test that deleting a specific order is impossible.
        Since we don't have RetrieveModelMixin, the URL doesn't exist (404).
        """
        order1 = Order.objects.create(user=self.user)
        Ticket.objects.create(order=order1, flight=self.flight, row=1, seat=1)

        url = f"{ORDER_URL}{order1.id}/"

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        # Verify that the order still exists in the database
        self.assertTrue(Order.objects.filter(id=order1.id).exists())
