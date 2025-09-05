# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

class AdminCreateUserForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=get_user_model().Roles.choices,
        label="Rol",
        initial=get_user_model().Roles.USER,
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email", "role")  # password1/2 los añade el base class
        widgets = {
            "username": forms.TextInput(attrs={"class": "input"}),
            "email": forms.EmailInput(attrs={"class": "input"}),
        }



class CreateUserForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        help_texts = {k: "" for k in fields}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", "input")

from django import forms
from django.core.exceptions import ValidationError
from .models import Profile
import calendar


def _add_months(d, months):
    """Suma meses a una fecha (maneja fin de mes)."""
    if d is None:
        return None
    m = d.month - 1 + int(months or 0)
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return d.replace(year=y, month=m, day=day)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = (
            "location", "external_id", "manager_name", "phone", "address", "link",
            "last_maintenance", "next_maintenance", "maintenance_interval_months",
        )
        labels = {
            "location": "Ubicación",
            "external_id": "ID",
            "manager_name": "Encargado",
            "phone": "Teléfono",
            "address": "Dirección",
            "link": "Link",
            "last_maintenance": "Última mantención",
            "next_maintenance": "Próxima mantención",
            "maintenance_interval_months": "Intervalo mantención (meses)",
        }
        widgets = {
            "location": forms.TextInput(attrs={"class": "input"}),
            "external_id": forms.TextInput(attrs={"class": "input"}),
            "manager_name": forms.TextInput(attrs={"class": "input"}),
            "phone": forms.TextInput(attrs={"placeholder": "+56 9 7948 2430", "class": "input"}),
            "address": forms.TextInput(attrs={"placeholder": "BELLAVISTA 165", "class": "input"}),
            "link": forms.URLInput(attrs={"placeholder": "https://...", "class": "input"}),

            # Nuevos widgets
            "last_maintenance": forms.DateInput(attrs={"type": "date", "class": "input"}),
            "next_maintenance": forms.DateInput(attrs={"type": "date", "class": "input"}),
            "maintenance_interval_months": forms.NumberInput(
                attrs={"class": "input", "min": 1, "max": 60, "step": 1}
            ),
        }

    def clean(self):
        cleaned = super().clean()
        last_m = cleaned.get("last_maintenance")
        next_m = cleaned.get("next_maintenance")
        interval = cleaned.get("maintenance_interval_months") or 12

        # Validación de coherencia
        if last_m and next_m and next_m < last_m:
            self.add_error("next_maintenance", "La próxima mantención no puede ser anterior a la última.")

        # Autocalcular próxima si no se ingresó y hay última + intervalo
        if last_m and not next_m:
            cleaned["next_maintenance"] = _add_months(last_m, interval)

        return cleaned

# accounts/forms.py
from django import forms
from .models import GasConsumption

# accounts/forms.py
from django import forms
from .models import GasConsumption
# accounts/forms.py
from django import forms
from .models import GasConsumption

# accounts/forms.py
from django import forms
from .models import GasConsumption

MONTH_CHOICES = [
    ("ene", "Enero"), ("feb", "Febrero"), ("mar", "Marzo"), ("abr", "Abril"),
    ("may", "Mayo"), ("jun", "Junio"), ("jul", "Julio"), ("ago", "Agosto"),
    ("sep", "Septiembre"), ("oct", "Octubre"), ("nov", "Noviembre"), ("dic", "Diciembre"),
]

class GasConsumptionForm(forms.ModelForm):
    # Elegir año, mes y día
    month_choice = forms.ChoiceField(choices=MONTH_CHOICES, label="Mes")
    day = forms.IntegerField(label="Día", min_value=1, max_value=31, required=False)

    class Meta:
        model = GasConsumption
        # Si no quieres costo, elimínalo de fields:
        fields = ["year", "month_choice", "day", "m3_water", "m3_gas"]
        widgets = {
            "year": forms.NumberInput(attrs={"min": 2000, "max": 2100, "placeholder": "2025", "class": "in"}),
            "m3_water": forms.NumberInput(attrs={"step": "0.01", "class": "in"}),
            "m3_gas": forms.NumberInput(attrs={"step": "0.01", "class": "in"}),
        }
        labels = {
            "m3_water": "M³ Agua",
            "m3_gas": "M³ Gas",
        }

    def clean_year(self):
        y = self.cleaned_data["year"]
        if y < 2000 or y > 2100:
            raise forms.ValidationError("Año fuera de rango.")
        return y

    def clean_day(self):
        d = self.cleaned_data.get("day")
        # Si lo quieres obligatorio, descomenta:
        # if d is None:
        #     raise forms.ValidationError("El día es obligatorio.")
        return d

    def save(self, commit=True, user=None):
        """
        Construye 'month' como 'abr-25' con 'month_choice' + 'year', asigna 'day'
        y asocia el 'user' logeado.
        """
        instance = super().save(commit=False)
        abbr = self.cleaned_data["month_choice"]         # ej 'jun'
        year = self.cleaned_data["year"]                 # ej 2025
        yy = str(year)[-2:]                              # '25'
        instance.month = f"{abbr}-{yy}"
        instance.day = self.cleaned_data.get("day") or None
        if user is not None:
            instance.user = user
        if commit:
            instance.save()
        return instance





# accounts/forms.py
class AdminGasConsumptionForm(GasConsumptionForm):
    user = forms.ModelChoiceField(
        queryset=User.objects.order_by("username"),
        label="Usuario",
        required=True
    )

    class Meta(GasConsumptionForm.Meta):
        fields = ["user"] + GasConsumptionForm.Meta.fields + ["cost"]  # quita "cost" si no existe

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # todas las entradas con la misma clase visual
        for name, field in self.fields.items():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " input").strip()

        # afinamos algunos
        self.fields["user"].widget.attrs.setdefault("style", "min-width:220px")
        self.fields["month_choice"].widget.attrs.setdefault("class", "input select")
        self.fields["year"].widget.attrs.update({"min": 2000, "max": 2100, "placeholder": "2025"})
        self.fields["m3_water"].widget.attrs.setdefault("step", "0.01")
        self.fields["m3_gas"].widget.attrs.setdefault("step", "0.01")
