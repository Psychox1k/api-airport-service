from django.db.models import F, Count, Prefetch
from django.shortcuts import render
from rest_framework import viewsets

from airport.models import (
    Flight,
    AirplaneType,
    Airport,
    Route,
    Crew,
    Order,
    Ticket,
    Airplane,
)
from airport.serializers import (
    FlightSerializer,
    AirportSerializer,
    AirplaneTypeSerializer,
    RouteSerializer,
    CrewSerializer,
    OrderSerializer,
    TicketSerializer,
    AirplaneSerializer,
    FlightListSerializer,
    FlightDetailSerializer,
    OrderListSerializer,
    AirportDetailSerializer,
    RouteListSerializer,
    RouteDetailSerializer,
    AirplaneListSerializer,
    AirplaneDetailSerializer,
)


class AirplaneTypeViewSet(viewsets.ModelViewSet):
    queryset = AirplaneType.objects.all()
    serializer_class = AirplaneTypeSerializer


class AirplaneViewSet(viewsets.ModelViewSet):
    queryset = Airplane.objects.all().select_related(
        "airplane_type"
    )
    serializer_class = AirplaneSerializer

    def get_queryset(self):
        queryset = self.queryset

        if self.action == "retrieve":
            queryset = queryset.prefetch_related(
                Prefetch(
                    "flights",
                    queryset=Flight.objects.select_related(
                        "route__source",
                        "route__destination"
                    )
                )
            )

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return AirplaneListSerializer
        if self.action == "retrieve":
            return AirplaneDetailSerializer
        return AirplaneSerializer


class FlightViewSet(viewsets.ModelViewSet):
    queryset = Flight.objects.all().select_related(
        "route__source__",
        "route__destination",
        "airplane__airplane_type",
    ).annotate(
            tickets_available=(
                F("airplane__rows") * F("airplane__seats_in_row")
                - Count("tickets")
            )
        )
    serializer_class = FlightSerializer

    def get_queryset(self):
        queryset = self.queryset
        if self.action == "retrieve":
            queryset = queryset.prefetch_related(
                Prefetch('tickets', queryset=Ticket.objects.select_related('order')),
                'crew'
            )
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return FlightListSerializer
        if self.action == "retrieve":
            return FlightDetailSerializer
        return FlightSerializer


class AirportViewSet(viewsets.ModelViewSet):
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer

    def get_queryset(self):
        queryset = self.queryset

        if self.action == "retrieve":

            queryset = queryset.prefetch_related(
                "routes_from__destination",
                "routes_to__source",
                Prefetch(
                    "routes_from__flights",
                    queryset=Flight.objects.select_related("airplane")
                ),
                Prefetch(
                    "routes_to__flights",
                    queryset=Flight.objects.select_related("airplane")
                )
            )

        return queryset

    def get_serializer_class(self):

        if self.action == "retrieve":
            return AirportDetailSerializer
        return AirportSerializer


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all().select_related(
        "source",
        "destination"
    )

    serializer_class = RouteSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return RouteListSerializer
        if self.action == "retrieve":
            return RouteDetailSerializer
        return RouteSerializer


class CrewViewSet(viewsets.ModelViewSet):
    queryset = Crew.objects.all()
    serializer_class = CrewSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related(
        "tickets__flight__route__source",
        "tickets__flight__route__destination",
        "tickets__flight__airplane__airplane_type"
    )
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.select_related(
        "flight__route__source",
        "flight__route__destination",
        "flight__airplane",
        "order"
    )
    serializer_class = TicketSerializer
