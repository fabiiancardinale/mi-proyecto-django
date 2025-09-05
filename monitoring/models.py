# monitoring/models.py
from django.db import models

class Consumption(models.Model):
    date = models.DateField(db_column="fecha")
    boiler = models.CharField(max_length=100, db_column="caldera")
    water_m3 = models.DecimalField(max_digits=12, decimal_places=2, db_column="agua_m3")
    gas_m3 = models.DecimalField(max_digits=12, decimal_places=2, db_column="gas_m3")

    class Meta:
        db_table = "consumos_calderas"
