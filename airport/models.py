from django.core.validators import MinValueValidator
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


class AirplaneType(models.Model):
    """
    Represents the type or model of an airplane (e.g., Boeing 747, Airbus A320).
    """
    name = models.CharField(max_length=55)

    def __str__(self):
        return self.name


class Airplane(models.Model):
    """
    Represents a specific physical aircraft with a configured seating layout.
    """
    name = models.CharField(max_length=55)
    rows = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    seats_in_row = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])

    airplane_type = models.ForeignKey(
        AirplaneType,
        on_delete=models.PROTECT,
        related_name="airplanes",
    )

    @property
    def capacity(self):
        """
        Calculates the total number of seats in the airplane.
        """
        return self.rows * self.seats_in_row

    def __str__(self):
        return self.name


class Airport(models.Model):
    """
    Represents an airport facility.
    """
    name = models.CharField(max_length=100)
    closest_big_city = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Route(models.Model):
    """
    Represents a direct travel path between two airports.
    """
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
        """
        Validates the route data before saving.
        Ensures the source is not the same as the destination and
        checks logic constraints on distance.
        """
        # Prevent self-loops (flying to the same airport)
        if self.source == self.destination:
            raise ValidationError(
                "It can't be a route with the same source and destination"
            )

        # Logical constraint: no commercial flight is longer than 20,000 km
        if self.distance > 20000:
            raise ValidationError(
                "Route distance cannot exceed 20,000 km."
            )

    def __str__(self):
        return f"{self.source} → {self.destination}"


class Crew(models.Model):
    """
    Represents a flight crew member (pilot, flight attendant, etc.).
    """
    first_name = models.CharField(max_length=55)
    last_name = models.CharField(max_length=55)

    @property
    def full_name(self):
        """Returns the full name of the crew member."""
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Flight(models.Model):
    """
    Represents a scheduled flight instance on a specific route with an assigned airplane.
    """
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
        """
        Performs validation to ensure flight integrity:
        1. Checks for scheduling overlaps for the assigned airplane.
        2. Ensures departure is before arrival.
        3. Ensures the flight is not scheduled in the past.
        """

        # Check if the airplane is already flying during this time window.
        # We look for flights where:
        # (Start A < End B) and (End A > Start B) - standard overlap logic.
        overlapping = Flight.objects.filter(
            airplane=self.airplane,
            departure_time__lt=self.arrival_time,
            arrival_time__gt=self.departure_time
        ).exclude(id=self.id)  # Exclude current flight if editing

        if overlapping.exists():
            raise ValidationError(
                f"Flight times overlap with"
                f" existing flight: {overlapping.first()}"
            )

        # Validate time logic
        if self.departure_time >= self.arrival_time:
            raise ValidationError(
                "Departure time must be before arrival time"
            )

        # Validate future scheduling
        if self.departure_time < timezone.now():
            raise ValidationError(
                "Departure time cannot be in the past"
            )

    class Meta:
        ordering = ["departure_time"]


class Order(models.Model):
    """
    Represents a user's order containing one or more tickets.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    def __str__(self):
        return f"Order {self.id} at {self.created_at:%Y-%m-%d %H:%M}"

    class Meta:
        ordering = ["-created_at"]


class Ticket(models.Model):
    """
    Represents a specific seat reservation for a flight.
    """
    row = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)]
    )
    seat = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)]
    )
    flight = models.ForeignKey(
        Flight, on_delete=models.CASCADE, related_name="tickets"
    )
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="tickets"
    )

    @staticmethod
    def validate_ticket(row, seat, airplane, error_to_raise):
        """
        Checks if the requested seat exists within the airplane's layout.

        Args:
            row (int): The row number.
            seat (int): The seat number in the row.
            airplane (Airplane): The airplane instance.
            error_to_raise (Exception): Exception class to raise if validation fails.
        """
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
        """
        Validates the ticket before saving:
        1. Checks for double booking (seat already taken).
        2. Validates that the seat exists on the plane.
        """
        # Skip validation if flight is not set (handled by required fields later)
        if not self.flight_id:
            return

        # Check for duplicate tickets
        if Ticket.objects.filter(
                flight=self.flight,
                row=self.row,
                seat=self.seat
        ).exists():
            raise ValidationError(
                "This seat is already booked on the selected flight."
            )

        # Check physical bounds of the airplane
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
        """
        Overrides the save method to enforce validation (full_clean)
        before writing to the database.
        """
        self.full_clean()
        return super(Ticket, self).save(
            force_insert, force_update, using, update_fields
        )

    def __str__(self):
        return f"{self.flight} row:{self.row}, seat:{self.seat}"

    class Meta:
        unique_together = ("flight", "row", "seat")
        ordering = ["row", "seat"]
