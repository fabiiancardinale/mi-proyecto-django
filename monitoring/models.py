"""Tabla legacy ``consumos_calderas``.

La alimentan los equipos fuera de esta aplicación. El panel la usa solo para
el gráfico global ("Todos los clientes").
"""

from django.db import models


class Consumption(models.Model):
    date = models.DateField("Fecha", db_column="fecha")
    boiler = models.CharField("Caldera", max_length=100, db_column="caldera")
    water_m3 = models.DecimalField("M³ agua", max_digits=12, decimal_places=2, db_column="agua_m3")
    gas_m3 = models.DecimalField("M³ gas", max_digits=12, decimal_places=2, db_column="gas_m3")

    class Meta:
        db_table = "consumos_calderas"
        verbose_name = "Consumo de caldera (legacy)"
        verbose_name_plural = "Consumos de calderas (legacy)"

    def __str__(self) -> str:
        return f"{self.boiler} · {self.date:%d/%m/%Y}"
