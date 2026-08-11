# accounts/forms.py
"""Formularios del panel EMATEL."""

from __future__ import annotations

from django import forms
from django.contrib.auth.forms import UserCreationForm

from . import months
from .models import GasConsumption, Profile, User, sumar_meses

CLASE_CAMPO = "input"


def _aplicar_clase(formulario: forms.BaseForm) -> None:
    """Pone la clase visual comun en todos los widgets del formulario."""
    for campo in formulario.fields.values():
        css = campo.widget.attrs.get("class", "")
        if CLASE_CAMPO not in css.split():
            campo.widget.attrs["class"] = f"{css} {CLASE_CAMPO}".strip()


# =============================================================================
# Cuentas
# =============================================================================
class AdminCreateUserForm(UserCreationForm):
    """Alta de usuario desde el panel."""

    role = forms.ChoiceField(
        choices=User.Roles.choices,
        label="Rol",
        initial=User.Roles.USER,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "role")  # password1/2 los añade la clase base

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_clase(self)
        # Los textos de ayuda largos de Django se reemplazan por el mensaje
        # corto que ya muestra la plantilla.
        for campo in self.fields.values():
            campo.help_text = ""


class AdminEditUserForm(forms.ModelForm):
    """Edicion de cuenta desde el modal del panel.

    Valida unicidad de usuario y formato de email, cosa que la version
    anterior no hacia porque leia el POST en crudo.
    """

    class Meta:
        model = User
        fields = ("username", "email", "role", "is_active")
        labels = {
            "username": "Usuario",
            "email": "Email",
            "role": "Rol",
            "is_active": "Estado",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = False
        _aplicar_clase(self)


# =============================================================================
# Perfil del cliente
# =============================================================================
class _BaseProfileForm(forms.ModelForm):
    """Comportamiento compartido: validacion del link de Wecon."""

    def clean_link(self) -> str:
        url = (self.cleaned_data.get("link") or "").strip()
        if not url:
            return ""
        # URLField ya valida el formato. Aqui cerramos la puerta a esquemas
        # peligrosos como javascript: en un enlace que se abre con _blank.
        if not url.lower().startswith(("http://", "https://")):
            raise forms.ValidationError("El link debe empezar con http:// o https://")
        return url


class ProfileForm(_BaseProfileForm):
    """Perfil completo, usado en el alta de usuario."""

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
            "link": "Link del equipo (Wecon)",
            "last_maintenance": "Última mantención",
            "next_maintenance": "Próxima mantención",
            "maintenance_interval_months": "Intervalo mantención (meses)",
        }
        widgets = {
            "phone": forms.TextInput(attrs={"placeholder": "+56 9 1234 5678"}),
            "address": forms.TextInput(attrs={"placeholder": "Bellavista 165"}),
            "link": forms.URLInput(attrs={
                "placeholder": "https://servidor-wecon/...",
                "spellcheck": "false",
            }),
            "last_maintenance": forms.DateInput(attrs={"type": "date"}),
            "next_maintenance": forms.DateInput(attrs={"type": "date"}),
            "maintenance_interval_months": forms.NumberInput(
                attrs={"min": 1, "max": 60, "step": 1}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_clase(self)

    def clean(self):
        datos = super().clean()
        ultima = datos.get("last_maintenance")
        proxima = datos.get("next_maintenance")
        intervalo = datos.get("maintenance_interval_months") or 12

        if ultima and proxima and proxima < ultima:
            self.add_error(
                "next_maintenance",
                "La próxima mantención no puede ser anterior a la última.",
            )

        if ultima and not proxima:
            datos["next_maintenance"] = sumar_meses(ultima, intervalo)

        return datos


class ProfilePanelForm(_BaseProfileForm):
    """Subconjunto editable desde el modal del panel, incluido el link.

    Este es el formulario que faltaba: antes el link solo se podia tocar desde
    el admin de Django porque el modal no lo incluia.
    """

    class Meta:
        model = Profile
        fields = ("location", "external_id", "manager_name", "phone", "address", "link")
        labels = {
            "location": "Ubicación",
            "external_id": "ID",
            "manager_name": "Encargado",
            "phone": "Teléfono",
            "address": "Dirección",
            "link": "Link del equipo (Wecon)",
        }
        widgets = {
            "phone": forms.TextInput(attrs={"placeholder": "+56 9 1234 5678"}),
            "link": forms.URLInput(attrs={
                "placeholder": "https://servidor-wecon/...",
                "spellcheck": "false",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_clase(self)


class PreferenciasReporteForm(forms.ModelForm):
    """Preferencias de reporte, guardadas por AJAX desde el panel de usuario.

    Antes la vista hacia setattr() directo sobre el perfil con lo que llegara
    en el JSON, sin validar que la frecuencia o el formato fueran valores
    aceptados ni que el email tuviera formato correcto.
    """

    class Meta:
        model = Profile
        fields = ("report_frequency", "report_format", "report_email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.required = False


# =============================================================================
# Consumo
# =============================================================================
class GasConsumptionForm(forms.ModelForm):
    """Alta de consumo por parte del propio usuario."""

    month_choice = forms.ChoiceField(choices=months.CHOICES, label="Mes")
    day = forms.IntegerField(label="Día", min_value=1, max_value=31, required=False)

    class Meta:
        model = GasConsumption
        fields = ["year", "month_choice", "day", "m3_water", "m3_gas"]
        labels = {"m3_water": "M³ agua", "m3_gas": "M³ gas"}
        widgets = {
            "year": forms.NumberInput(attrs={"min": 2000, "max": 2100, "placeholder": "2025"}),
            "m3_water": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "m3_gas": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El modelo declara 'month' con choices, pero aqui lo reemplazamos por
        # month_choice, asi que 'month' no forma parte del formulario.
        self.fields["year"].initial = self.fields["year"].initial or None
        _aplicar_clase(self)

    def clean_year(self) -> int:
        anio = self.cleaned_data["year"]
        if not 2000 <= anio <= 2100:
            raise forms.ValidationError("El año debe estar entre 2000 y 2100.")
        return anio

    def clean(self):
        datos = super().clean()
        agua, gas = datos.get("m3_water"), datos.get("m3_gas")
        if agua in (None, "") and gas in (None, ""):
            raise forms.ValidationError(
                "Ingresa al menos el consumo de agua o el de gas."
            )
        return datos


class AdminGasConsumptionForm(GasConsumptionForm):
    """Igual que el anterior, pero el admin elige el usuario y el costo."""

    user = forms.ModelChoiceField(
        queryset=User.objects.order_by("username"),
        label="Usuario",
        required=True,
    )

    class Meta(GasConsumptionForm.Meta):
        fields = ["user"] + GasConsumptionForm.Meta.fields + ["cost"]
        widgets = {
            **GasConsumptionForm.Meta.widgets,
            "cost": forms.NumberInput(attrs={"step": "1", "min": "0"}),
        }
        labels = {**GasConsumptionForm.Meta.labels, "cost": "Costo (CLP)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].widget.attrs.setdefault("style", "min-width:200px")
        _aplicar_clase(self)
