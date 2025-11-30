from datetime import datetime

from django.db.models import F, Count, Prefetch, Q
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated

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
from airport.permissions import IsAdminOrIfAuthenticatedReadOnly
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
    AirplaneDetailSerializer, TicketListSerializer,
)


class AirplaneTypeViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = AirplaneType.objects.all()
    serializer_class = AirplaneTypeSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        type_name = self.request.query_params.get("type_name")
        type_id = self.request.query_params.get("id")

        queryset = self.queryset

        if type_name:
            queryset = queryset.filter(name__icontains=type_name)

        if type_id:
            queryset = queryset.filter(id=type_id)

        return queryset


class AirplaneViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Airplane.objects.all().select_related(
        "airplane_type"
    )
    serializer_class = AirplaneSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        queryset = self.queryset

        airplanes_type = self.request.query_params.get("airplane_type")
        airplane_id = self.request.query_params.get("id")
        airplane_name = self.request.query_params.get("name")

        if airplane_id:
            queryset = queryset.filter(id=airplane_id)

        if airplanes_type:
            queryset = queryset.filter(
                airplane_type__name__icontains=airplanes_type
            )
        if airplane_name:
            queryset = queryset.filter(name__icontains=airplane_name)

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


class FlightViewSet(
    viewsets.ModelViewSet
):
    queryset = Flight.objects.all().select_related(
        "route__source",
        "route__destination",
        "airplane__airplane_type",
    ).annotate(
            tickets_available=(
                F("airplane__rows") * F("airplane__seats_in_row")
                - Count("tickets")
            )
        )
    serializer_class = FlightSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):

        flight_id = self.request.query_params.get("id")
        airplane_id = self.request.query_params.get("airplane")
        arrival_time = self.request.query_params.get("arrival_time")
        departure_time = self.request.query_params.get("departure_time")
        source_name = self.request.query_params.get("source")
        dest_name = self.request.query_params.get("destination")

        queryset = self.queryset

        if flight_id:
            queryset = queryset.filter(id=flight_id)

        if airplane_id:
            queryset = queryset.filter(airplane_id=int(airplane_id))

        if arrival_time:
            date_obj = datetime.strptime(arrival_time, "%Y-%m-%d").date()
            queryset = queryset.filter(arrival_time__date=date_obj)

        if departure_time:
            date_obj = datetime.strptime(departure_time, "%Y-%m-%d").date()
            queryset = queryset.filter(departure_time__date=date_obj)

        if source_name:
            queryset = queryset.filter(route__source__name__icontains=source_name)

        if dest_name:
            queryset = queryset.filter(route__destination__name__icontains=dest_name)



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


class AirportViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        airport_name = self.request.query_params.get("name")
        airport_id = self.request.query_params.get("id")
        city = self.request.query_params.get("city")

        queryset = self.queryset

        if airport_name:
            queryset = queryset.filter(name__icontains=airport_name)

        if airport_id:
            queryset = queryset.filter(id=airport_id)

        if city:
            queryset = queryset.filter(closest_big_city__icontains=city)

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
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):

        route_id = self.request.query_params.get("id")
        distance_min = self.request.query_params.get("distance_min")
        distance_max = self.request.query_params.get("distance_max")

        queryset = self.queryset

        if route_id:
            queryset = queryset.filter(id=route_id)

        if distance_min:
            queryset = queryset.filter(distance__gte=int(distance_min))

        if distance_max:
            queryset = queryset.filter(distance__lte=int(distance_max))

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return RouteListSerializer
        if self.action == "retrieve":
            return RouteDetailSerializer
        return RouteSerializer


class CrewViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    queryset = Crew.objects.all()
    serializer_class = CrewSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):

        full_name = self.request.query_params.get("name")
        crew_id = self.request.query_params.get("id")

        queryset = self.queryset

        if full_name:
            queryset = queryset.filter(
                Q(first_name__icontains=full_name)
                | Q(last_name__icontains=full_name)
            )

        if crew_id:
            queryset = queryset.filter(id=crew_id)

        return queryset


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Order.objects.prefetch_related(
        "tickets__flight__route__source",
        "tickets__flight__route__destination",
        "tickets__flight__airplane__airplane_type"
    )
    serializer_class = OrderSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return (
            self.queryset
            .filter(user=self.request.user)
        )

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
