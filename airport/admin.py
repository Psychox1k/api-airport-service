from django.contrib import admin

from airport.models import (
    Route,
    Flight,
    Airport,
    Airplane,
    Order,
    Crew
)

# Register your models here.
admin.site.register(Order)
admin.site.register(Airplane)
admin.site.register(Airport)
admin.site.register(Flight)
admin.site.register(Route)
admin.site.register(Crew)
