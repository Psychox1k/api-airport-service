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


class AirplaneTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirplaneType
        fields = ("id", "name")


class AirplaneSerializer(serializers.ModelSerializer):
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


class AirportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airport
        fields = ("id", "name", "closest_big_city")


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")

    def validate(self, attrs):
        source = attrs.get("source")
        destination = attrs.get("destination")

        if source == destination:
            raise serializers.ValidationError(
                {"source": "Source and destination can't be the same"}
            )

        return attrs


class CrewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = ("id", "first_name", "last_name", "full_name")


class FlightSerializer(serializers.ModelSerializer):
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

    airplane_capacity = serializers.IntegerField(
        source="airplane.capacity", read_only=True
    )
    airport_name = serializers.CharField(
        source="airport.name", read_only=True
    )
    airplane_name = serializers.CharField(
        source="airplane.name", read_only=True
    )

    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        fields = (
            "id",
            "route",
            "departure_time",
            "airport_name"
            "airplane_name",
            "airplane_capacity"
            "arrival_time",
            "tickets_available"
        )



class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ("id", "created_at", "user")


class TicketSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        row = attrs.get("row")
        seat = attrs.get("seat")
        flight = attrs.get("flight")

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
