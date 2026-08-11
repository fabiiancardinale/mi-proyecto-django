# Guía de despliegue · actualización de agosto 2026

Esta actualización **no es un `git pull` normal**. Cambian tres cosas que
requieren atención:

1. La aplicación ya no arranca sin un archivo `.env`.
2. Tres migraciones modifican y borran datos existentes.
3. Hay archivos que conviene borrar del repositorio.

Léela completa antes de tocar el servidor.

---

## 1. Archivos que debes borrar

Corre esto **en tu equipo**, no en el servidor:

```bash
cd C:\src\Proyectos\mi-proyecto-django

# 12 MB de basura: es un PostScript de ImageMagick, no la librería pymysql
del pymysql

# CSS obsoletos: todo el estilo vive ahora en static/theme.css
git rm static/base.css static/admin.css static/user.css static/login.css static/app.css

# Archivo de prueba, si existe
del static\_prueba.css
```

En Linux o Git Bash:

```bash
rm -f pymysql static/_prueba.css
git rm static/base.css static/admin.css static/user.css static/login.css static/app.css
```

Ninguna plantilla los referencia — ya lo verifiqué. `staticfiles/` (625
archivos, 8 MB) ya no lo rastrea git; se regenera solo con `collectstatic`.

Después:

```bash
git add -A
git commit -m "Refactor, rediseño y gestión de links de Wecon"
git push origin main
```

---

## 2. Antes de migrar: mira qué le va a pasar a tus datos

**Sí, las migraciones modifican los datos que ya existen en el VPS.** Esto no
es opcional ni evitable: son justamente las que arreglan la inconsistencia
histórica. Pero puedes ver exactamente qué harán antes de ejecutarlas.

En el servidor, después del `git pull` y de crear el `.env`:

```bash
python manage.py revisar_migracion
```

No escribe nada. Te dirá, fila por fila:

- qué meses se van a reescribir (`"may-24"` → `"may"`)
- **qué filas duplicadas se van a borrar**, y cuál se conserva de cada grupo
- qué roles se van a reescribir, y **si algún usuario va a perder permisos**
- si hay algo que haría fallar la migración

Usa `--detalle` para ver el listado completo en vez de una muestra.

### Lo que hace cada migración

| Migración | Qué hace | ¿Destructiva? |
|---|---|---|
| `0011` | Normaliza `month` a tres letras y `role` a `admin`/`user` | Modifica filas |
| `0012` | Borra consumos duplicados del mismo usuario/año/mes | **Borra filas** |
| `0013` | Añade índice y restricción de unicidad, amplía `link` a 500 | Solo esquema |

**El riesgo real a vigilar:** si algún usuario tiene un `role` que no sea
`admin`, `user`, `Administrador` ni `Usuario`, la migración 0011 lo pasa a
`user` y **pierde el acceso al panel de administración**. El comando
`revisar_migracion` te avisa de esto en rojo. Si ocurre, corrígelo antes:

```sql
UPDATE accounts_user SET role='admin' WHERE username='nombre_del_usuario';
```

Sobre el borrado de duplicados: de cada grupo se conserva la fila con el `id`
más alto, es decir la última que se escribió, que es la que el usuario vio
guardarse. Las anteriores eran versiones viejas del mismo periodo.

---

## 3. Despliegue paso a paso

```bash
# ---- 1. Conectarse ----
ssh sergio@82.25.79.89
cd /var/www/ematel_site/app

# ---- 2. RESPALDO (no te lo saltes) ----
mysqldump -u datasensor_farmacia -p calderas_ematel > ~/respaldo-$(date +%F-%H%M).sql
ls -lh ~/respaldo-*.sql          # confirma que pesa algo

# ---- 3. Traer los cambios ----
git pull origin main

# ---- 4. Crear el .env (SOLO LA PRIMERA VEZ) ----
cp .env.example .env
nano .env
```

En el `.env` del servidor pon:

```ini
DJANGO_SECRET_KEY=<genérala, ver abajo>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=82.25.79.89
DJANGO_CSRF_TRUSTED_ORIGINS=http://82.25.79.89

DJANGO_USAR_SQLITE=False
DB_NOMBRE=calderas_ematel
DB_USUARIO=datasensor_farmacia
DB_PASSWORD=<la contraseña NUEVA, ver punto 5>
DB_HOST=127.0.0.1
DB_PUERTO=3306

# Mientras el sitio siga en http, déjalas en False
DJANGO_COOKIES_SEGURAS=False
DJANGO_SSL_REDIRECT=False
```

Genera la clave con:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Protege el archivo:

```bash
chmod 600 .env
```

```bash
# ---- 5. Dependencias ----
source .venv/bin/activate
pip install -r requirements.txt      # añade reportlab y python-dotenv

# ---- 6. Revisar qué harán las migraciones ----
python manage.py revisar_migracion

# ---- 7. Migrar (fuera de horario de uso) ----
python manage.py migrate

# ---- 8. Estáticos ----
python manage.py collectstatic --noinput

# ---- 9. Comprobar antes de recargar ----
python manage.py check --deploy      # debe salir sin issues

# ---- 10. Recargar Apache ----
sudo systemctl reload apache2
```

---

## 4. Verificación posterior

```bash
# Ningún consumo duplicado debe quedar
python manage.py shell -c "
from accounts.models import GasConsumption
from django.db.models import Count
d = (GasConsumption.objects.values('user','year','month')
     .annotate(n=Count('id')).filter(n__gt=1))
print('Duplicados restantes:', list(d) or 'ninguno')
"

# Los roles deben ser solo admin y user
python manage.py shell -c "
from accounts.models import User
from django.db.models import Count
print(list(User.objects.values('role').annotate(n=Count('id'))))
"
```

En el navegador, revisa que:

- entras al panel y **aparece el menú de Administración** (antes no salía)
- el filtro por rol devuelve resultados (antes daba siempre cero)
- el botón de editar muestra el campo **Link del equipo (Wecon)**
- el panel de usuario muestra el formulario para registrar consumo

---

## 5. Rotar la contraseña de MySQL

La contraseña anterior estuvo en `settings.py` dentro del repositorio, así que
sigue en el historial de git. Cámbiala:

```sql
ALTER USER 'datasensor_farmacia'@'localhost' IDENTIFIED BY 'la-nueva-contraseña';
FLUSH PRIVILEGES;
```

Y actualiza `DB_PASSWORD` en el `.env` del servidor.

---

## 6. Si algo sale mal

```bash
# Restaurar la base
mysql -u datasensor_farmacia -p calderas_ematel < ~/respaldo-FECHA.sql

# Volver al commit anterior
git log --oneline -5
git checkout <hash-anterior>
sudo systemctl reload apache2
```

Las migraciones 0011 y 0012 **no se pueden revertir**: los datos originales
eran inconsistentes y no hay forma de reconstruirlos. Por eso el respaldo del
paso 2 es la única vuelta atrás real.

---

## 7. Actualizar los links de Wecon

Ya con todo desplegado:

```bash
python manage.py links_wecon exportar --salida links.csv
```

Descarga `links.csv`, rellena la columna `link_nuevo`, súbelo de vuelta y:

```bash
python manage.py links_wecon importar --archivo links.csv          # simulación
python manage.py links_wecon importar --archivo links.csv --aplicar
```

O edítalos uno por uno desde el panel, en el botón del lápiz de cada fila.
