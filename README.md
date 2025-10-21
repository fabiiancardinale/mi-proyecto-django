# 🚀 Actualización del Proyecto EMATEL Site en el VPS

Guía rápida para desplegar los últimos cambios en el servidor de producción.

---

## 🔹 Pasos para actualizar

```bash
# 1️⃣ Conéctate al servidor VPS
ssh sergio@82.25.79.89

# 2️⃣ Accede a la carpeta del proyecto
cd /var/www/ematel_site/app

# 3️⃣ Descarga los cambios desde GitHub
git pull origin main
# ⚠️ Si tu rama es master, cambia main por master

# 4️⃣ Activa el entorno virtual
source .venv/bin/activate

# 5️⃣ Instala las dependencias nuevas (si cambiaste requirements.txt)
pip install -r requirements.txt

# 6️⃣ Aplica migraciones y recopila archivos estáticos
python manage.py migrate
python manage.py collectstatic --noinput

# 7️⃣ Recarga Apache para aplicar los cambios
sudo systemctl reload apache2
