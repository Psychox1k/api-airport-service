from datetime import datetime

from django.db.models import F, Count, Prefetch, Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
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
    AirplaneDetailSerializer,
    TicketListSerializer,
)


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "type_name",
                type=OpenApiTypes.STR,
                description="Filter by airplane type name (ex. ?type_name=Boeing)",
            ),
        ]
    )
)
class AirplaneTypeViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for managing Airplane Types.
    Allows listing and creating types.
    Restricted to Admin for creation; Read-only for authenticated users.
    """
    queryset = AirplaneType.objects.all()
    serializer_class = AirplaneTypeSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        """
        Filters airplane types by name or ID.
        """
        type_name = self.request.query_params.get("type_name")
        type_id = self.request.query_params.get("id")

        queryset = self.queryset

        if type_name:
            queryset = queryset.filter(name__icontains=type_name)

        if type_id:
            queryset = queryset.filter(id=type_id)

        return queryset


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "airplane_type",
                type=OpenApiTypes.STR,
                description="Filter by airplane type name (ex. ?airplane_type=Boeing)",
            ),
            OpenApiParameter(
                "name",
                type=OpenApiTypes.STR,
                description="Filter by airplane name (ex. ?name=Mriya)",
            ),
        ]
    )
)
class AirplaneViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for Airplanes.
    Optimized to fetch related 'AirplaneType' to prevent N+1 queries.
    """
    # Use select_related because 'airplane_type' is a ForeignKey (One-to-Many)
    queryset = Airplane.objects.all().select_related(
        "airplane_type"
    )
    serializer_class = AirplaneSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        """
        Applies filters and conditional prefetching for detailed views.
        """
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

        # Optimization: Only load full flight history when viewing a single airplane (Retrieve)
        # This prevents loading huge amounts of data for simple list views.
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


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "airplane",
                type=OpenApiTypes.INT,
                description="Filter by airplane ID (ex. ?airplane=1)",
            ),
            OpenApiParameter(
                "arrival_time",
                type=OpenApiTypes.DATE,
                description="Filter by arrival date (ex. ?arrival_time=2024-10-25)",
            ),
            OpenApiParameter(
                "departure_time",
                type=OpenApiTypes.DATE,
                description="Filter by departure date (ex. ?departure_time=2024-10-25)",
            ),
            OpenApiParameter(
                "source",
                type=OpenApiTypes.STR,
                description="Filter by source airport name (ex. ?source=Kyiv)",
            ),
            OpenApiParameter(
                "destination",
                type=OpenApiTypes.STR,
                description="Filter by destination airport name (ex. ?destination=Paris)",
            ),
        ]
    )
)
class FlightViewSet(
    viewsets.ModelViewSet
):
    """
    ViewSet for Flights.
    Contains complex logic for calculating available tickets on the DB level.
    """
    # We join Routes, Airports, and Airplane details to the initial query.
    queryset = Flight.objects.all().select_related(
        "route__source",
        "route__destination",
        "airplane__airplane_type",
    ).annotate(
            # Calculate available tickets dynamically using F expressions.
            # Logic: (Rows * Seats_per_row) - (Count of sold tickets)
            tickets_available=(
                F("airplane__rows") * F("airplane__seats_in_row")
                - Count("tickets")
            )
        )
    serializer_class = FlightSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        """
        Extensive filtering capabilities for flight search.
        """
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


        # When viewing details, we also need to know exactly WHICH tickets are taken
        # and who the crew is. We prefetch this to avoid N+1 queries.
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


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "name",
                type=OpenApiTypes.STR,
                description="Filter by airport name (ex. ?name=Heathrow)",
            ),
            OpenApiParameter(
                "city",
                type=OpenApiTypes.STR,
                description="Filter by closest big city (ex. ?city=London)",
            ),
        ]
    )
)
class AirportViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    """
    ViewSet for Airports.
    """
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

        # In retrieve view, we show ALL flights connected to this airport.
        # This requires complex prefetching to get flight details (airplanes)
        # without killing the database.
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


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "distance_min",
                type=OpenApiTypes.INT,
                description="Filter by minimum distance (ex. ?distance_min=500)",
            ),
            OpenApiParameter(
                "distance_max",
                type=OpenApiTypes.INT,
                description="Filter by maximum distance (ex. ?distance_max=2000)",
            ),
        ]
    )
)
class RouteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Routes between airports.
    """
    # Always load source and destination airports to show names, not just IDs.
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


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "name",
                type=OpenApiTypes.STR,
                description="Filter by crew member name (first or last) (ex. ?name=John)",
            ),
        ]
    )
)
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
            # Filter by First Name OR Last Name
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
    """
    ViewSet for User Orders.
    Ensures data privacy: Users can only access their own orders.
    """
    # Optimize query by fetching all nested ticket/flight info in one go
    queryset = Order.objects.prefetch_related(
        "tickets__flight__route__source",
        "tickets__flight__route__destination",
        "tickets__flight__airplane__airplane_type"
    )
    serializer_class = OrderSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        """
        Override to strictly filter orders by the current authenticated user.
        """
        return (
            self.queryset
            .filter(user=self.request.user)
        )

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        """
        Automatically assign the logged-in user to the order.
        """
        serializer.save(user=self.request.user)