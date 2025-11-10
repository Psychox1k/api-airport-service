from django.core.validators import MinValueValidator
from django.db import models
from django.conf import settings

from django.core.exceptions import ValidationError
from django.utils import timezone


class AirplaneType(models.Model):
    name = models.CharField(max_length=55)

    def __str__(self):
        return self.name


class Airplane(models.Model):
    name = models.CharField(max_length=55)
    rows = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    seats_in_row = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])

    airplane_type = models.ForeignKey(
        AirplaneType, on_delete=models.PROTECT, related_name="airplanes"
    )

    @property
    def capacity(self):
        return self.rows * self.seats_in_row

    def __str__(self):
        return self.name


class Airport(models.Model):
    name = models.CharField(max_length=100)
    closest_big_city = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Route(models.Model):
    source = models.ForeignKey(
        Airport,
        on_delete=models.PROTECT,
        related_name="routes_from"
    )
    destination = models.ForeignKey(
        Airport,
        on_delete=models.PROTECT,
        related_name="routes_to",
    )
    distance = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    def clean(self):
        if self.source == self.destination:
            raise ValidationError("It can't be a route with the same source and destination")
        if self.distance > 20000:
            raise ValidationError("Route distance cannot exceed 20,000 km.")

    def __str__(self):
        return f"{self.source} → {self.destination}"


class Crew(models.Model):
    first_name = models.CharField(max_length=55)
    last_name = models.CharField(max_length=55)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Flight(models.Model):
    route = models.ForeignKey(
        Route,
        on_delete=models.PROTECT,
        related_name="flights",
        blank=False,
        null=False
    )
    airplane = models.ForeignKey(
        Airplane,
        on_delete=models.PROTECT,
        related_name="flights",
        blank=False,
        null=False
    )
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()

    crew = models.ManyToManyField(Crew, related_name="flights", blank=True)

    def __str__(self):
        return f"{self.route} @ {self.departure_time:%Y-%m-%d %H:%M}"

    def clean(self):

        overlapping_flight = Flight.objects.filter(
            airplane=self.airplane
        ).exclude(id=self.id)

        for flight in overlapping_flight:
            if (
                    self.departure_time < flight.arrival_time and
                    self.arrival_time > flight.departure_time):
                raise ValidationError(
                    f"Flight times overlap with an existing flight: {flight}"
                )

        if self.departure_time >= self.arrival_time:
            raise ValidationError("Departure time must be before arrival time")
        if self.departure_time < timezone.now():
            raise ValidationError("Departure time cannot be in the past")

    class Meta:
        ordering = ["departure_time"]


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders"
    )

    def __str__(self):
        return f"Order {self.id} at {self.created_at:%Y-%m-%d %H:%M}"

    class Meta:
        ordering = ["-created_at"]


class Ticket(models.Model):
    row = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    seat = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name="tickets")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="tickets")

    @staticmethod
    def validate_ticket(row, seat, airplane, error_to_raise):
        for value, field, max_field in [
            (row, "row", "rows"),
            (seat, "seat", "seats_in_row"),
        ]:
            limit = getattr(airplane, max_field)
            if not (1 <= value <= limit):
                raise error_to_raise({
                    field: f"{field} must be within 1..{limit}"
                })

    def clean(self):

        if not self.flight_id:
            return

        if Ticket.objects.filter(
            flight=self.flight,
            row=self.row,
            seat=self.seat
        ).exists():
            raise ValidationError("This seat is already booked on the selected flight.")

        Ticket.validate_ticket(
            self.row,
            self.seat,
            self.flight.airplane,
            ValidationError
        )

    def save(
        self,
        *args,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        self.full_clean()
        return super(Ticket, self).save(
            force_insert, force_update, using, update_fields
        )

    def __str__(self):
        return f"{self.flight} row:{self.row}, seat:{self.seat}"

    class Meta:
        unique_together = ("flight", "row", "seat")
        ordering = ["row", "seat"]


