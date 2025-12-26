from django.db import transaction
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from airport.models import (
    AirplaneType,
    Airplane,
    Airport,
    Route,
    Crew,
    Flight,
    Order,
    Ticket,
)


class TicketSerializer(serializers.ModelSerializer):
    """
    Serializer for the Ticket model.
    Handles basic ticket information and validates seat availability.
    """

    def validate(self, attrs):
        """
        Custom validation to ensure the seat and row are within
        the physical bounds of the airplane.
        """
        data = super().validate(attrs)
        row = attrs.get("row")
        seat = attrs.get("seat")
        flight = attrs.get("flight")

        # Validate ticket position against airplane capacity
        if row is not None and seat is not None and flight is not None:
            Ticket.validate_ticket(
                row,
                seat,
                flight.airplane,
                ValidationError
            )
        return data

    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "flight", "order")
        # Order is handled automatically when creating via OrderSerializer
        read_only_fields = ("order",)


class TicketSeatsSerializer(TicketSerializer):
    """
    Simplified serializer to show only seat details (Row/Seat).
    Used in Flight details to show which seats are taken.
    """

    class Meta:
        model = Ticket
        fields = ("row", "seat")


class RouteSerializer(serializers.ModelSerializer):
    """
    Standard CRUD serializer for Routes.
    """

    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")

    def validate(self, attrs):
        """
        Ensure that the source airport is not the same as the destination.
        """
        source = attrs.get("source")
        destination = attrs.get("destination")

        if source == destination:
            raise serializers.ValidationError(
                {"source": "Source and destination can't be the same"}
            )

        return attrs


class RouteListSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for listing routes with string representation.
    """
    name = serializers.CharField(source="__str__", read_only=True)

    class Meta:
        model = Route
        fields = (
            "id",
            "name",
            "distance",
        )


class AirplaneTypeSerializer(serializers.ModelSerializer):
    """
    Serializer for Airplane Types (e.g., Boeing 747).
    """

    class Meta:
        model = AirplaneType
        fields = ("id", "name")


class AirplaneSerializer(serializers.ModelSerializer):
    """
    Standard serializer for Airplanes with calculated capacity.
    """

    class Meta:
        model = Airplane
        fields = (
            "id",
            "name",
            "rows",
            "seats_in_row",
            "airplane_type",
            "capacity"
        )


class AirplaneListSerializer(AirplaneSerializer):
    """
    Used for list views: displays the airplane type name instead of ID.
    """
    airplane_type = serializers.CharField(
        source="airplane_type.name", read_only=True
    )


class AirplaneDetailSerializer(serializers.ModelSerializer):
    """
    Detailed view of an Airplane.
    Includes the full AirplaneType object and a list of routes served by this plane.
    """
    airplane_type = AirplaneTypeSerializer(many=False, read_only=True)
    routes_name = serializers.SerializerMethodField()

    class Meta:
        model = Airplane
        fields = (
            "id",
            "name",
            "rows",
            "seats_in_row",
            "airplane_type",
            "routes_name",
            "capacity"
        )

    def get_routes_name(self, obj):
        """Returns a list of string representations of routes flown by this airplane."""
        flights = Flight.objects.filter(airplane=obj)
        # Using set to avoid duplicates if needed, or list for all history
        return [str(flight.route) for flight in flights]


class AirportSerializer(serializers.ModelSerializer):
    """Basic Airport serializer."""

    class Meta:
        model = Airport
        fields = ("id", "name", "closest_big_city")


class AirportDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive Airport view.
    Shows incoming/outgoing routes and a list of airplanes that land here.
    """
    routes_from = RouteListSerializer(many=True, read_only=True)
    routes_to = RouteListSerializer(many=True, read_only=True)
    airplanes = serializers.SerializerMethodField()

    class Meta:
        model = Airport
        fields = (
            "id",
            "name",
            "closest_big_city",
            "airplanes",
            "routes_from",
            "routes_to",
        )

    def get_airplanes(self, obj):
        """
        Finds all airplanes that have visited this airport
        (either as a source or destination).
        """
        flights = Flight.objects.filter(
            Q(route__source=obj) | Q(route__destination=obj)
        )
        airplanes = [flight.airplane for flight in flights]
        # Return unique names
        return list(set([airplane.name for airplane in airplanes]))


class RouteDetailSerializer(serializers.ModelSerializer):
    """
    Route serializer with full nested Airport objects.
    """
    source = AirportSerializer(many=False, read_only=True)
    destination = AirportSerializer(many=False, read_only=True)

    class Meta:
        model = Route
        fields = (
            "id",
            "source",
            "destination",
            "distance"
        )


class CrewSerializer(serializers.ModelSerializer):
    """Serializer for Flight Crew members."""

    class Meta:
        model = Crew
        fields = ("id", "first_name", "last_name", "full_name")


class FlightSerializer(serializers.ModelSerializer):
    """
    Write-serializer for Flights (Create/Update).
    Uses IDs for relations.
    """

    class Meta:
        model = Flight
        fields = (
            "id",
            "route",
            "airplane",
            "departure_time",
            "arrival_time",
            "crew"
        )


class FlightListSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for listing flights.
    Flattens related data (airport names, capacity) for easier frontend consumption.
    """
    airplane_capacity = serializers.IntegerField(
        source="airplane.capacity", read_only=True
    )
    airport_name_departure = serializers.CharField(
        source="route.source.name", read_only=True
    )
    airplane_name = serializers.CharField(
        source="airplane.name", read_only=True
    )
    route_name = serializers.StringRelatedField(
        source="route", read_only=True
    )

    # This field expects the queryset to be annotated with 'tickets_available'
    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Flight
        fields = (
            "id",
            "route_name",
            "departure_time",
            "airport_name_departure",
            "airplane_name",
            "airplane_capacity",
            "arrival_time",
            "tickets_available"
        )


class FlightDetailSerializer(serializers.ModelSerializer):
    """
    Detailed Flight view.
    Includes full nested objects for Route, Airplane, and Crew.
    Also shows 'taken_place' (booked seats).
    """
    route = RouteDetailSerializer(read_only=True)
    airplane = AirplaneListSerializer(read_only=True)
    taken_place = TicketSeatsSerializer(source="tickets", many=True, read_only=True)
    crew = CrewSerializer(many=True, read_only=True)

    class Meta:
        model = Flight
        fields = (
            "id",
            "departure_time",
            "arrival_time",
            "airplane",
            "route",
            "taken_place",
            "crew"
        )


class TicketListSerializer(TicketSerializer):
    """
    Ticket serializer that shows full flight details (for user history).
    """
    flight = FlightListSerializer(many=False, read_only=True)


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for creating Orders.
    Supports writable nested serialization for tickets.
    """
    tickets = TicketSerializer(
        many=True,
        read_only=False,
        allow_empty=False
    )

    class Meta:
        model = Order
        fields = ("id", "tickets", "created_at")

    def create(self, validated_data):
        """
        Custom create method to handle writable nested 'tickets' data.
        Uses an atomic transaction to ensure either the whole order (with tickets)
        is created, or nothing is created if an error occurs.
        """
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(**validated_data)

            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)

            return order


class OrderListSerializer(OrderSerializer):
    """
    Read-only serializer for listing orders with nested ticket details.
    """
    tickets = TicketListSerializer(many=True, read_only=True)
