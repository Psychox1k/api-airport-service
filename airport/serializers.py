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
        read_only_fields = ("order",)


class TicketSeatsSerializer(TicketSerializer):
    class Meta:
        model = Ticket
        fields = ("row", "seat")


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


class RouteListSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="__str__", read_only=True)

    class Meta:
        model = Route
        fields = (
            "id",
            "name",
            "distance",
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


class AirplaneListSerializer(AirplaneSerializer):
    airplane_type = serializers.CharField(
        source="airplane_type.name", read_only=True
    )


class AirplaneDetailSerializer(serializers.ModelSerializer):
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
        flights = Flight.objects.filter(airplane=obj)
        return [str(flight.route) for flight in flights]


class AirportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airport
        fields = ("id", "name", "closest_big_city")


class AirportDetailSerializer(serializers.ModelSerializer):
    routes_from = RouteListSerializer(many=True, read_only=True,
                                      )
    routes_to = RouteListSerializer(
        many=True,
        read_only=True
    )
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
        flights = Flight.objects.filter(
            Q(route__source=obj) | Q(route__destination=obj)
        )
        airplanes = [flight.airplane for flight in flights]
        return [airplane.name for airplane in airplanes]


class RouteDetailSerializer(serializers.ModelSerializer):
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
    airport_name_departure = serializers.CharField(
        source="route.source.name", read_only=True
    )
    airplane_name = serializers.CharField(
        source="airplane.name", read_only=True
    )
    route_name = serializers.StringRelatedField(
        source="route", read_only=True
    )

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
    flight = FlightListSerializer(many=False, read_only=True)


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(
        many=True,
        read_only=False,
        allow_empty=False
    )

    class Meta:
        model = Order
        fields = ("id", "tickets", "created_at")

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(**validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)
            return order


class OrderListSerializer(OrderSerializer):
    tickets = TicketSerializer(many=True, read_only=True)
