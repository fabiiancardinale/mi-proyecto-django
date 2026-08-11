# EMATEL · Sistema de monitoreo de calderas

Panel web para gestionar clientes, consumo de agua y gas, y los enlaces de
monitoreo de los equipos Wecon.

---

## Puesta en marcha

```bash
# 1. Dependencias
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Configuración
cp .env.example .env               # y completa los valores reales

# 3. Base de datos y estáticos
python manage.py migrate
python manage.py collectstatic --noinput

# 4. Servidor
python manage.py runserver
```

> **Importante:** el proyecto ya no funciona sin `.env`. Las credenciales de
> base de datos y la `SECRET_KEY` salieron del código fuente. Genera una clave
> nueva con:
>
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

Para trabajar en local sin MySQL, pon `DJANGO_USAR_SQLITE=True` en tu `.env`.

---

## Actualizar los links de Wecon

Los enlaces de los equipos **no están en el código**: son datos por cliente
guardados en `Profile.link`. Hay dos formas de actualizarlos.

### Uno por uno, desde la interfaz

Panel de administración → botón de editar (lápiz) en la fila del cliente →
campo **Link del equipo (Wecon)**. Ya no hace falta entrar al admin de Django.

La tabla marca con **«Sin link»** a quien le falte, y el indicador superior
muestra cuántos clientes quedan pendientes.

### En lote, con un CSV

Para una migración completa de servidor:

```bash
# 1. Exporta el estado actual
python manage.py links_wecon exportar --salida links.csv

# 2. Abre links.csv y rellena la columna "link_nuevo"

# 3. Revisa qué cambiaría (no escribe nada)
python manage.py links_wecon importar --archivo links.csv

# 4. Aplica de verdad
python manage.py links_wecon importar --archivo links.csv --aplicar
```

El comando valida cada URL, avisa de usuarios inexistentes y **no aplica nada
si alguna fila tiene problemas**. Es idempotente: correrlo dos veces no
duplica ni rompe datos.

---

## Despliegue en el VPS

```bash
ssh sergio@82.25.79.89
cd /var/www/ematel_site/app

git pull origin main
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py collectstatic --noinput

sudo systemctl reload apache2
```

**Solo la primera vez tras esta actualización:** crea el archivo `.env` en el
servidor a partir de `.env.example` con las credenciales de producción. Sin él
la aplicación no arranca.

---

## Estructura

```
accounts/
  months.py        Fuente única para interpretar y formatear meses
  services.py      Lógica de negocio: alta de consumo, series, historial
  reports.py       Generación de reportes CSV y PDF
  views.py         Solo manejo HTTP: valida, delega, arma contexto
  forms.py         Formularios y validación
  models.py        User, Profile y GasConsumption
  api_views.py     API REST con JWT
  management/commands/links_wecon.py    Carga masiva de links
monitoring/        Modelo Consumption sobre la tabla legacy consumos_calderas
ematel_site/       Configuración del proyecto
templates/         Plantillas; todas extienden base.html
static/theme.css   Sistema de diseño (fuente única de estilos)
```

Los archivos `static/base.css`, `admin.css`, `user.css`, `login.css` y
`app.css` quedaron obsoletos y pueden borrarse: todo el estilo vive en
`theme.css`.

### Dónde va cada cosa

- **Nueva regla de negocio** → `services.py`, no en la vista.
- **Nuevo formato de mes que aceptar** → `months.abreviar()`, único lugar.
- **Validación de un campo** → el formulario correspondiente, no la vista.

Las migraciones repiten a propósito su propia tabla de meses: deben ser
autocontenidas y seguir funcionando aunque el código de la app cambie.

---

## Tests

```bash
python manage.py test accounts
```

65 pruebas que cubren la normalización de meses, el alta de consumo sin
duplicados, los permisos por rol, la edición del link desde la interfaz y la
generación de reportes.

---

## Convenciones

**Roles.** La columna `role` guarda los códigos `admin` y `user`. Las
etiquetas «Administrador» y «Usuario» son solo de presentación — nunca
compares contra ellas en código ni en plantillas.

**Meses.** `GasConsumption.month` guarda siempre la abreviatura de tres letras
en minúscula (`ene`..`dic`). Para leer cualquier otro formato usa
`months.abreviar()`; nunca cortes la cadena a mano.

**Consumo.** Hay como máximo un registro por usuario, año y mes: lo garantiza
una restricción en la base de datos. Para dar de alta usa
`services.registrar_consumo()`, que hace `update_or_create` y evita duplicados
con envíos simultáneos.
