# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "admin", "Administrador"
        USER  = "user", "Usuario"

    role = models.CharField(
        max_length=32,
        choices=Roles.choices,
        default=Roles.USER
    )

    # Opcional: helpers
    def is_admin(self):
        return self.role == self.Roles.ADMIN

    def is_user(self):
        return self.role in (self.Roles.USER, self.Roles.ADMIN)

# apps/tu_app/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone
import calendar

def _add_months(d, months):
    """Suma meses a una fecha sin dependencias externas."""
    if d is None:
        return None
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return d.replace(year=y, month=m, day=day)


# accounts/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone
import calendar

def _add_months(d, months: int):
    """Suma 'months' meses a la fecha 'd' respetando fin de mes."""
    if not d:
        return None
    m = d.month - 1 + int(months)
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return d.replace(year=y, month=m, day=day)

class Profile(models.Model):
    # Usuario
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    # Datos existentes
    location = models.CharField("Ubicación", max_length=120, blank=True)
    external_id = models.CharField("ID", max_length=50, blank=True)
    manager_name = models.CharField("Encargado", max_length=120, blank=True)
    phone = models.CharField("Teléfono", max_length=30, blank=True)
    address = models.CharField("Dirección", max_length=200, blank=True)
    link = models.URLField("Link", blank=True)

    # Mantenciones
    last_maintenance = models.DateField("Última mantención", null=True, blank=True)
    next_maintenance = models.DateField("Próxima mantención", null=True, blank=True)
    maintenance_interval_months = models.PositiveSmallIntegerField(
        "Intervalo mantención (meses)", default=12
    )

    # Reportes automáticos
    REPORT_FREQ = (('off', 'Nunca'), ('m', 'Mensual'), ('q', 'Trimestral'))
    REPORT_FMT  = (('pdf', 'PDF'), ('csv', 'CSV'))

    report_frequency = models.CharField(
        "Frecuencia de reporte", max_length=10, choices=REPORT_FREQ, default='off'
    )
    report_format = models.CharField(
        "Formato de reporte", max_length=4, choices=REPORT_FMT, default='pdf'
    )
    report_email = models.EmailField("Email para reportes", blank=True)

    def save(self, *args, **kwargs):
        # Calcula próxima mantención si falta
        if self.last_maintenance and not self.next_maintenance:
            self.next_maintenance = _add_months(
                self.last_maintenance, self.maintenance_interval_months
            )
        # Usa el email del usuario si no se definió el de reportes
        if not self.report_email:
            self.report_email = self.user.email or ""
        super().save(*args, **kwargs)

    @property
    def days_to_next_maintenance(self):
        """Días para la próxima mantención (negativo si vencida)."""
        if not self.next_maintenance:
            return None
        today = timezone.localdate()
        return (self.next_maintenance - today).days

    def __str__(self):
        return f"Perfil de {self.user.username}"


from django.db import models
from django.conf import settings
# accounts/models.py
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator

MONTH_CHOICES = (
    (1, "ene"), (2, "feb"), (3, "mar"), (4, "abr"),
    (5, "may"), (6, "jun"), (7, "jul"), (8, "ago"),
    (9, "sep"), (10, "oct"), (11, "nov"), (12, "dic"),
)
from django.conf import settings
from django.db import models

class GasConsumption(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gas_consumptions",
    )
    year = models.IntegerField()
    month = models.CharField(max_length=10)  # ej: "may-24"
    day = models.PositiveSmallIntegerField(null=True, blank=True)  # <-- NUEVO

    m3_water = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    m3_gas   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cost     = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["year", "id"]

    def __str__(self):
        dia = f"-{self.day:02d}" if self.day else ""
        return f"{self.user.username} - {self.month}{dia} {self.year}"
