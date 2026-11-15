# EMATEL · Sistema de monitoreo de calderas

Panel web para gestionar clientes, consumo de agua y gas, y los enlaces de
monitoreo de los equipos Wecon.

---

## Ver el proyecto en local

Requiere Python 3.10 o superior. No necesitas MySQL: en local se usa SQLite.

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Set-Content -Path .env -Value "DJANGO_DEBUG=True","DJANGO_USAR_SQLITE=True" -Encoding ascii

python manage.py migrate
python manage.py datos_demo
python manage.py runserver
```

> Si `Activate.ps1` da un error de "ejecución de scripts deshabilitada", corre
> una vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y repite.

**Mac / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

printf "DJANGO_DEBUG=True\nDJANGO_USAR_SQLITE=True\n" > .env

python manage.py migrate
python manage.py datos_demo
python manage.py runserver
```

> Si `mysqlclient` falla al instalar, no lo necesitas para trabajar en local.
> Instala el resto con:
> `pip install "Django>=5.0,<6.0" djangorestframework djangorestframework-simplejwt django-cors-headers whitenoise reportlab python-dotenv`

Abre <http://127.0.0.1:8000> y entra con alguna de estas cuentas
(contraseña `demo1234` en todas):

| Usuario   | Qué ves                                                    |
|-----------|------------------------------------------------------------|
| `admin`   | Panel de administración: clientes, gráficos y registros    |
| `hotel`   | Panel de cliente con link de Wecon y dos años de consumo    |
| `colegio` | Cliente sin link y con la mantención vencida                |

`datos_demo` solo funciona con `DJANGO_DEBUG=True` y se puede correr varias
veces sin duplicar nada. El admin de Django sigue en `/admin/` (crea un
superusuario con `python manage.py createsuperuser` si lo necesitas).

### Producción

En el servidor el `.env` se completa a partir de `.env.example`, con
`DJANGO_DEBUG=False`, la `SECRET_KEY` y las credenciales de MySQL. Genera una
clave nueva con:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## App móvil (Flutter)

La carpeta `app_movil/` tiene la app para clientes y administradores. Usa la
API REST de este proyecto (`/api/panel/`, `/api/consumption/`,
`/api/clientes/`, con login JWT). Instrucciones en
[`app_movil/README.md`](app_movil/README.md).

Para probarla contra tu Django local, corre `python manage.py runserver` y en
la app elige el servidor `http://127.0.0.1:8000` (Windows o Chrome) o
`http://10.0.2.2:8000` (emulador de Android).

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
  models.py         User, Profile y GasConsumption
  forms.py          Formularios y validación (incluido el de login)
  views.py          Solo manejo HTTP: valida, delega, arma contexto
  services.py       Lógica de negocio: alta de consumo, series, historial
  months.py         Fuente única para interpretar y formatear meses
  reports.py        Reportes CSV y PDF
  api_views.py      API REST con JWT que usa la app (rutas en api_url.py, bajo /api/)
  api_admin.py      API de administración de la app (clientes, resumen)
  admin.py          Registro en el admin de Django
  management/commands/
    links_wecon.py  Carga masiva de links
    datos_demo.py   Datos de ejemplo para desarrollo
monitoring/         Tabla legacy consumos_calderas (gráfico global)
ematel_site/        Configuración del proyecto
app_movil/          App Flutter (ver su README)
templates/
  base.html             Esqueleto HTML común (fuentes, CSS, ui.js)
  layouts/app.html      Barra lateral + contenido, para páginas con sesión
  includes/             Piezas reutilizables: campo de formulario,
                        mensajes, errores, variación porcentual
  *.html                Una plantilla por página
static/
  theme.css         Sistema de diseño: única hoja de estilos
  js/ui.js          Utilidades comunes: CSRF, modales, pestañas, confirmación
  js/graficos.js    Configuración y colores comunes de Chart.js
  js/admin.js       Panel de administración
  js/usuario.js     Panel del cliente
```

### Dónde va cada cosa

- **Nueva regla de negocio** → `services.py`, no en la vista.
- **Nuevo formato de mes que aceptar** → `months.abreviar()`, único lugar.
- **Validación de un campo** → el formulario correspondiente, no la vista.
- **Estilos** → `theme.css`. Las plantillas no llevan `style="…"`.
- **JavaScript** → `static/js/`. Las plantillas no llevan `<script>` en línea;
  los datos pasan con `{{ valor|json_script:"id" }}` y las URLs con atributos
  `data-*` generados con `{% url %}`.
- **Un campo de formulario** → `{% include "includes/field.html" with field=form.x %}`.

Las migraciones repiten a propósito su propia tabla de meses: deben ser
autocontenidas y seguir funcionando aunque el código de la app cambie.

---

## Tests

```bash
python manage.py test accounts
```

86 pruebas que cubren la normalización de meses, el alta de consumo sin
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

Al actualizar un mes existente solo se escriben los campos que vienen con
valor: registrar el gas de un mes que ya tenía agua conserva el agua, y un
cliente que corrige su consumo no borra el costo que cargó el administrador.
Un `0` escrito explícitamente sí se guarda.
