# accounts/models.py
"""Modelos de cuentas, perfiles de cliente y consumo mensual."""

from __future__ import annotations

import calendar

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from . import months


def sumar_meses(fecha, cantidad: int):
    """Suma meses a una fecha respetando el fin de mes.

    31/01 + 1 mes = 28/02 (o 29 en bisiesto), no un dia invalido.
    """
    if not fecha:
        return None
    indice = fecha.month - 1 + int(cantidad or 0)
    anio = fecha.year + indice // 12
    mes = indice % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return fecha.replace(year=anio, month=mes, day=dia)


# ---------------------------------------------------------------------------
class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "admin", "Administrador"
        USER = "user", "Usuario"

    role = models.CharField(
        "Rol",
        max_length=32,
        choices=Roles.choices,
        default=Roles.USER,
    )

    def is_admin(self) -> bool:
        return self.role == self.Roles.ADMIN

    def is_user(self) -> bool:
        return self.role in (self.Roles.USER, self.Roles.ADMIN)


# ---------------------------------------------------------------------------
class Profile(models.Model):
    """Datos del sitio del cliente, incluido el link del equipo Wecon."""

    class FrecuenciaReporte(models.TextChoices):
        NUNCA = "off", "Nunca"
        MENSUAL = "m", "Mensual"
        TRIMESTRAL = "q", "Trimestral"

    class FormatoReporte(models.TextChoices):
        PDF = "pdf", "PDF"
        CSV = "csv", "CSV"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    # Datos del sitio
    location = models.CharField("Ubicación", max_length=120, blank=True)
    external_id = models.CharField("ID", max_length=50, blank=True)
    manager_name = models.CharField("Encargado", max_length=120, blank=True)
    phone = models.CharField("Teléfono", max_length=30, blank=True)
    address = models.CharField("Dirección", max_length=200, blank=True)

    # Enlace al panel de monitoreo del equipo (Wecon).
    # Es un dato por cliente, no una constante del sistema: cuando Wecon
    # migra de servidor se actualiza aqui, no en el codigo.
    link = models.URLField("Link del equipo", max_length=500, blank=True)

    # Mantenciones
    last_maintenance = models.DateField("Última mantención", null=True, blank=True)
    next_maintenance = models.DateField("Próxima mantención", null=True, blank=True)
    maintenance_interval_months = models.PositiveSmallIntegerField(
        "Intervalo mantención (meses)", default=12
    )

    # Reportes automaticos
    report_frequency = models.CharField(
        "Frecuencia de reporte", max_length=10,
        choices=FrecuenciaReporte.choices, default=FrecuenciaReporte.NUNCA,
    )
    report_format = models.CharField(
        "Formato de reporte", max_length=4,
        choices=FormatoReporte.choices, default=FormatoReporte.PDF,
    )
    report_email = models.EmailField("Email para reportes", blank=True)

    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfiles"

    def save(self, *args, **kwargs):
        if self.last_maintenance and not self.next_maintenance:
            self.next_maintenance = sumar_meses(
                self.last_maintenance, self.maintenance_interval_months
            )
        if not self.report_email:
            self.report_email = self.user.email or ""
        super().save(*args, **kwargs)

    @property
    def days_to_next_maintenance(self) -> int | None:
        """Días hasta la próxima mantención. Negativo si está vencida."""
        if not self.next_maintenance:
            return None
        return (self.next_maintenance - timezone.localdate()).days

    @property
    def tiene_link(self) -> bool:
        return bool(self.link)

    def __str__(self) -> str:
        return f"Perfil de {self.user.username}"


# ---------------------------------------------------------------------------
class GasConsumption(models.Model):
    """Consumo de agua y gas de un usuario en un mes concreto.

    ``month`` guarda siempre la abreviatura canonica de tres letras
    ("ene".."dic"). La normalizacion la hace accounts.months.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gas_consumptions",
    )
    year = models.PositiveIntegerField("Año")
    month = models.CharField("Mes", max_length=10, choices=months.CHOICES)
    day = models.PositiveSmallIntegerField("Día", null=True, blank=True)

    m3_water = models.DecimalField(
        "M³ agua", max_digits=10, decimal_places=2, null=True, blank=True
    )
    m3_gas = models.DecimalField(
        "M³ gas", max_digits=10, decimal_places=2, null=True, blank=True
    )
    cost = models.DecimalField(
        "Costo", max_digits=12, decimal_places=2, null=True, blank=True
    )

    class Meta:
        verbose_name = "Consumo"
        verbose_name_plural = "Consumos"
        ordering = ["-year", "id"]
        constraints = [
            # Un registro por usuario y mes. Cierra la condicion de carrera
            # del patron filter().first() + create() que habia antes.
            models.UniqueConstraint(
                fields=["user", "year", "month"],
                name="consumo_unico_por_usuario_y_mes",
            )
        ]
        indexes = [
            models.Index(fields=["user", "year"], name="consumo_usuario_anio_idx"),
        ]

    @property
    def month_label(self) -> str:
        return months.etiqueta(self.month, defecto=self.month or "—")

    def __str__(self) -> str:
        dia = f"-{self.day:02d}" if self.day else ""
        return f"{self.user.username} · {self.month}{dia} {self.year}"
