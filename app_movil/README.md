# EMATEL · App móvil

App Flutter para los clientes de EMATEL. Usa la API REST del proyecto Django
(carpeta de arriba).

- **Clientes:** ven el consumo de agua y gas, el costo, la próxima mantención,
  gráficos que comparan años, el historial mes a mes y el botón «Ver mi
  caldera» (link de Wecon). Pueden registrar su consumo.
- **Administradores** (rol administrador o superusuario):
  - **Resumen:** usuarios, activos, clientes sin link de Wecon y mantenciones
    vencidas o por vencer en 30 días, con acceso directo a cada cliente.
  - **Clientes:** búsqueda y filtros (activos, inactivos, sin link, admins).
  - **Ficha del cliente:** su panel de consumo, más su cuenta. Desde ahí se
    edita (datos, link de Wecon, mantención, activar o desactivar), se
    elimina o se registra consumo con costo.
  - **Nuevo cliente:** crea la cuenta y el perfil.

Al registrar un mes que ya existe solo cambian los campos que se completan:
cargar el gas no borra el agua.

## Requisitos

- [Flutter](https://docs.flutter.dev/get-started/install) 3.50 o superior.
  Revisa tu versión con `flutter --version`; si es más antigua, `flutter upgrade`.
- Para Android: Android Studio con un emulador, o un teléfono con depuración USB.
- Para iPhone: un Mac con Xcode.

## Ejecutarla

```powershell
cd app_movil
flutter pub get
flutter run
```

`flutter run` pregunta en qué dispositivo abrirla (emulador, teléfono,
Windows o Chrome).

### ¿A qué servidor se conecta?

Por defecto a `http://82.25.79.89`. Se puede cambiar de dos formas:

- **En la app:** pantalla de inicio de sesión → «Servidor».
- **Al compilar:** `flutter run --dart-define=API_URL=http://...`

Para probar contra el Django de tu computador (`python manage.py runserver`):

| Dónde corre la app       | Servidor                                     |
|--------------------------|----------------------------------------------|
| Windows o Chrome         | `http://127.0.0.1:8000`                      |
| Emulador de Android      | `http://10.0.2.2:8000`                       |
| Teléfono en la misma red | `http://IP-de-tu-PC:8000` y correr Django con `python manage.py runserver 0.0.0.0:8000` (agrega esa IP a `DJANGO_ALLOWED_HOSTS`) |

## Generar el instalador

```powershell
flutter build apk --release        # Android: build/app/outputs/flutter-apk/app-release.apk
flutter build windows              # Windows
flutter build ipa                  # iPhone (solo en Mac)
```

El APK que se genera así va firmado con la clave de depuración: sirve para
instalarlo directo en teléfonos, pero no para Play Store. Para publicar en
Play Store o App Store hay que configurar la firma de la app;
ver la guía oficial de Flutter para
[Android](https://docs.flutter.dev/deployment/android) e
[iOS](https://docs.flutter.dev/deployment/ios).

## Seguridad: HTTPS

El servidor todavía usa `http`, así que Android e iOS están configurados para
permitirlo (`usesCleartextTraffic` en `android/app/src/main/AndroidManifest.xml`
y `NSAppTransportSecurity` en `ios/Runner/Info.plist`). Con `http` el usuario y
la contraseña viajan sin cifrar. Cuando el servidor tenga certificado (por
ejemplo con Let's Encrypt), cambia el servidor por defecto a `https://...` y
quita esas dos configuraciones.

## Estructura

```
lib/
  main.dart               Arranque y tema
  tema.dart               Colores (los mismos de la web)
  formato.dart            Números, pesos y fechas en formato chileno
  api/
    cliente_api.dart      Login JWT, renovación automática del token, llamadas
    modelos.dart          Panel, Perfil, Serie, FilaHistorial, Cliente
  pantallas/
    login.dart            Inicio de sesión (y servidor)
    inicio.dart           Decide: admin → clientes, cliente → su panel
    panel.dart            Indicadores, gráfico, historial, sitio
    registrar.dart        Formulario para registrar consumo
    admin/
      inicio_admin.dart   Pestañas Resumen y Clientes
      resumen_admin.dart  Indicadores y clientes que requieren atención
      lista_clientes.dart Búsqueda y filtros
      editar_cliente.dart Alta y edición de clientes
  widgets/
    tarjetas.dart         Tarjetas, indicadores, variación, avisos
    grafico_consumo.dart  Gráfico de barras mensual
test/                     Pruebas (flutter test)
```

Los tokens se guardan en el almacenamiento seguro del dispositivo
(`flutter_secure_storage`). El token de acceso dura 30 minutos y la app lo
renueva sola; la sesión dura 30 días sin uso.

## Endpoints que usa

| Método | Ruta                 | Uso                                       |
|--------|----------------------|-------------------------------------------|
| POST   | `/api/auth/token/`   | Iniciar sesión                            |
| POST   | `/api/auth/refresh/` | Renovar el token                          |
| GET    | `/api/panel/`        | Todo el panel (`?user_id=` para admin)    |
| POST   | `/api/consumption/`  | Registrar o actualizar un mes             |
| GET    | `/api/admin/resumen/`| Indicadores del administrador             |
| GET    | `/api/clientes/`     | Lista (`?q=`, `?status=`, `?role=`)       |
| POST   | `/api/clientes/`     | Crear cliente                             |
| GET/PATCH/DELETE | `/api/clientes/<id>/` | Ver, editar o eliminar un cliente |
