from django.urls import path, include
from rest_framework import routers

from airport.views import (
    AirplaneViewSet,
    FlightViewSet,
    AirportViewSet,
    OrderViewSet,
    TicketViewSet,
    CrewViewSet,
    RouteViewSet,
    AirplaneTypeViewSet
)

router = routers.DefaultRouter()
router.register("airplanes", AirplaneViewSet)
router.register("airplane-types", AirplaneTypeViewSet)
router.register("flights", FlightViewSet)
router.register("airports", AirportViewSet)
router.register("orders", OrderViewSet)
router.register("tickets", TicketViewSet)
router.register("crews", CrewViewSet)
router.register("routes", RouteViewSet)

urlpatterns = [path("", include(router.urls))]

app_name = "airport"
