# accounts/tests.py
"""Batería de pruebas del panel EMATEL.

Cubre lo que el refactor tocó y, sobre todo, los errores concretos que se
corrigieron: normalización de meses, alta de consumo sin duplicados, permisos
por rol, y el link de Wecon editable desde la interfaz.
"""

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from . import months, reports, services
from .models import GasConsumption, Profile, User, sumar_meses


class MesesTest(TestCase):
    """accounts.months es la fuente única; antes había cuatro copias."""

    def test_reconoce_formatos_historicos(self):
        casos = {
            "may": "may", "Mayo": "may", "MAYO": "may", "mayo": "may",
            "may-24": "may", "may-2024": "may", "Mayo 2024": "may",
            5: "may", "5": "may", "05": "may",
            "septiembre": "sep", "setiembre": "sep", "sept": "sep",
            "september": "sep", "jan": "ene", "December": "dic",
            "Día": None,
        }
        for entrada, esperado in casos.items():
            with self.subTest(entrada=entrada):
                self.assertEqual(months.abreviar(entrada), esperado)

    def test_valores_no_reconocidos_devuelven_none(self):
        # El código viejo asumía enero en silencio y ensuciaba los datos.
        for basura in (None, "", "   ", "xyz", 0, 13, 99, "mes"):
            with self.subTest(basura=basura):
                self.assertIsNone(months.abreviar(basura))

    def test_indices_y_etiquetas(self):
        self.assertEqual(months.a_indice("ene"), 1)
        self.assertEqual(months.a_indice("dic"), 12)
        self.assertEqual(months.a_posicion("ene"), 0)
        self.assertEqual(months.etiqueta("may"), "Mayo")
        self.assertEqual(months.etiqueta("basura"), "—")

    def test_choices_tiene_doce_meses(self):
        self.assertEqual(len(months.CHOICES), 12)
        self.assertEqual(months.CHOICES[0], ("ene", "Enero"))


class SumarMesesTest(TestCase):
    def test_respeta_fin_de_mes(self):
        import datetime
        self.assertEqual(
            sumar_meses(datetime.date(2025, 1, 31), 1),
            datetime.date(2025, 2, 28),
        )
        self.assertEqual(
            sumar_meses(datetime.date(2024, 1, 31), 1),
            datetime.date(2024, 2, 29),  # bisiesto
        )
        self.assertEqual(
            sumar_meses(datetime.date(2025, 6, 15), 12),
            datetime.date(2026, 6, 15),
        )

    def test_none_devuelve_none(self):
        self.assertIsNone(sumar_meses(None, 12))


class RegistrarConsumoTest(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user("cliente", password="x")

    def test_crea_y_luego_actualiza_sin_duplicar(self):
        _, creado = services.registrar_consumo(
            user=self.usuario, year=2025, month="Mayo", m3_water=100, m3_gas=50
        )
        self.assertTrue(creado)

        registro, creado = services.registrar_consumo(
            user=self.usuario, year=2025, month="may-25", m3_water=120, m3_gas=60
        )
        self.assertFalse(creado)
        self.assertEqual(GasConsumption.objects.count(), 1)
        self.assertEqual(registro.m3_water, Decimal("120"))

    def test_normaliza_el_mes_al_guardar(self):
        registro, _ = services.registrar_consumo(
            user=self.usuario, year=2025, month="SEPTIEMBRE", m3_gas=10
        )
        self.assertEqual(registro.month, "sep")

    def test_guarda_el_dia(self):
        # El formulario recogía 'day' pero la vista nunca lo guardaba.
        registro, _ = services.registrar_consumo(
            user=self.usuario, year=2025, month="ene", day=15, m3_gas=1
        )
        self.assertEqual(registro.day, 15)

    def test_mes_invalido_lanza_error(self):
        with self.assertRaises(services.MesInvalido):
            services.registrar_consumo(user=self.usuario, year=2025, month="xyz")

    def test_acepta_coma_decimal(self):
        registro, _ = services.registrar_consumo(
            user=self.usuario, year=2025, month="ene", m3_water="12,50"
        )
        self.assertEqual(registro.m3_water, Decimal("12.50"))

    def test_restriccion_de_unicidad_en_base_de_datos(self):
        services.registrar_consumo(user=self.usuario, year=2025, month="ene", m3_gas=1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                GasConsumption.objects.create(
                    user=self.usuario, year=2025, month="ene", m3_gas=2
                )


class SeriesYResumenTest(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user("cliente", password="x")
        for anio, mes, agua, gas, costo in [
            (2024, "may", 100, 50, 1000),
            (2024, "jun", 110, 55, 1100),
            (2025, "may", 120, 60, 1200),
        ]:
            services.registrar_consumo(
                user=self.usuario, year=anio, month=mes,
                m3_water=agua, m3_gas=gas, cost=costo,
            )

    def test_serie_anual_coloca_los_meses_en_su_posicion(self):
        serie = services.serie_anual(self.usuario.id, 2024)
        self.assertEqual(serie["water"][4], 100.0)  # mayo
        self.assertEqual(serie["water"][5], 110.0)  # junio
        self.assertEqual(serie["water"][0], 0.0)    # enero sin datos
        self.assertEqual(len(serie["water"]), 12)

    def test_datos_comparativa(self):
        datos = services.datos_comparativa(
            user_id=self.usuario.id, anio_actual=2025, anio_previo=2024
        )
        self.assertEqual(datos["years"], {"prev": 2024, "now": 2025})
        self.assertEqual(datos["water"]["prev"][4], 100.0)
        self.assertEqual(datos["water"]["now"][4], 120.0)
        self.assertEqual(len(datos["labels"]), 12)

    def test_comparativa_global_no_falla_sin_datos(self):
        datos = services.datos_comparativa(
            user_id=None, anio_actual=2025, anio_previo=2024
        )
        self.assertEqual(datos["water"]["now"], [0.0] * 12)

    def test_historial_calcula_variacion_interanual(self):
        filas = services.historial(self.usuario)
        mayo_2025 = next(f for f in filas if f.year == 2025 and f.month == "may")
        self.assertEqual(mayo_2025.diff_water, Decimal("20"))
        self.assertAlmostEqual(mayo_2025.pct_water, 20.0)

        # Junio 2024 no tiene año anterior con datos.
        junio_2024 = next(f for f in filas if f.year == 2024 and f.month == "jun")
        self.assertIsNone(junio_2024.diff_water)

    def test_resumen_anual(self):
        resumen = services.resumen_anual(self.usuario, 2024)
        self.assertEqual(resumen["total_water"], Decimal("210"))
        self.assertEqual(resumen["total_cost"], Decimal("2100"))
        self.assertEqual(resumen["water_avg"], Decimal("105"))

    def test_resumen_sin_anio_devuelve_claves_vacias(self):
        resumen = services.resumen_anual(self.usuario, None)
        self.assertIsNone(resumen["total_water"])
        self.assertIn("water_avg", resumen)

    def test_buscar_mes(self):
        registro, comparativa = services.buscar_mes(self.usuario, 2025, "Mayo")
        self.assertEqual(registro.m3_water, Decimal("120"))
        self.assertEqual(comparativa["prev_year"], 2024)
        self.assertEqual(comparativa["water_diff"], Decimal("20"))

    def test_buscar_mes_inexistente(self):
        registro, comparativa = services.buscar_mes(self.usuario, 2025, "Diciembre")
        self.assertIsNone(registro)
        self.assertIsNone(comparativa)

    def test_anios_disponibles_ordenados(self):
        self.assertEqual(services.anios_disponibles(self.usuario), [2025, 2024])


class ReportesTest(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user("cliente", password="x")
        # Se cargan desordenados a propósito.
        for mes, agua in [("dic", 30), ("ene", 10), ("jun", 20)]:
            services.registrar_consumo(
                user=self.usuario, year=2025, month=mes, m3_water=agua, cost=100
            )

    def test_filas_salen_en_orden_cronologico(self):
        # Antes se ordenaba por id, o sea por orden de carga.
        filas = reports.filas_del_anio(self.usuario, 2025)
        self.assertEqual([f[1] for f in filas], ["Enero", "Junio", "Diciembre"])

    def test_csv_incluye_cabecera_y_datos(self):
        contenido = reports.construir_csv(self.usuario, 2025).decode("utf-8-sig")
        self.assertIn("cliente", contenido)
        self.assertIn("M3_AGUA", contenido)
        self.assertIn("Enero", contenido)

    def test_pdf_es_un_pdf(self):
        contenido = reports.construir_pdf(self.usuario, 2025)
        self.assertTrue(contenido.startswith(b"%PDF"))

    def test_pdf_sin_datos_no_falla(self):
        contenido = reports.construir_pdf(self.usuario, 1999)
        self.assertTrue(contenido.startswith(b"%PDF"))

    def test_formato_no_soportado(self):
        with self.assertRaises(reports.FormatoNoSoportado):
            reports.construir(self.usuario, 2025, "xlsx")


class PermisosPorRolTest(TestCase):
    """El rol se guarda como 'admin'/'user'; nunca como la etiqueta visible."""

    def setUp(self):
        self.admin = User.objects.create_user("jefe", password="x", role="admin")
        self.cliente = User.objects.create_user("cliente", password="x", role="user")

    def test_anonimo_va_al_login(self):
        respuesta = self.client.get(reverse("admin_dashboard"))
        self.assertRedirects(respuesta, reverse("login"), fetch_redirect_response=False)

    def test_cliente_no_entra_al_panel_admin(self):
        self.client.force_login(self.cliente)
        respuesta = self.client.get(reverse("admin_dashboard"))
        self.assertRedirects(respuesta, reverse("user_dashboard"), fetch_redirect_response=False)

    def test_admin_entra_al_panel_admin(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("admin_dashboard")).status_code, 200)

    def test_superusuario_pasa_siempre(self):
        raiz = User.objects.create_superuser("raiz", "r@e.cl", "x")
        raiz.role = "user"
        raiz.save()
        self.client.force_login(raiz)
        self.assertEqual(self.client.get(reverse("admin_dashboard")).status_code, 200)

    def test_cliente_no_puede_borrar_usuarios(self):
        self.client.force_login(self.cliente)
        respuesta = self.client.post(
            reverse("usuario_eliminar", args=[self.admin.id])
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(User.objects.filter(pk=self.admin.id).exists())


class FiltroDeUsuariosTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("jefe", password="x", role="admin")
        User.objects.create_user("farmacia", "f@e.cl", "x", role="user")
        self.client.force_login(self.admin)

    def _usuarios_en_tabla(self, respuesta):
        cuerpo = respuesta.content.decode().split("<tbody>")[1].split("</tbody>")[0]
        return cuerpo

    def test_filtro_por_rol_funciona(self):
        # Antes comparaba contra "Administrador" y siempre devolvía cero.
        cuerpo = self._usuarios_en_tabla(self.client.get("/panel/admin/?role=user"))
        self.assertIn("farmacia", cuerpo)
        self.assertNotIn(">jefe<", cuerpo)

    def test_busqueda_por_texto(self):
        cuerpo = self._usuarios_en_tabla(self.client.get("/panel/admin/?q=farma"))
        self.assertIn("farmacia", cuerpo)
        self.assertNotIn(">jefe<", cuerpo)

    def test_filtro_por_estado(self):
        User.objects.filter(username="farmacia").update(is_active=False)
        cuerpo = self._usuarios_en_tabla(self.client.get("/panel/admin/?status=inactivos"))
        self.assertIn("farmacia", cuerpo)


class EditarUsuarioTest(TestCase):
    """El bug original: el link solo se podía tocar desde el admin de Django."""

    def setUp(self):
        self.admin = User.objects.create_user("jefe", password="x", role="admin")
        self.cliente = User.objects.create_user("farmacia", "f@e.cl", "x", role="user")
        self.client.force_login(self.admin)
        self.url = reverse("usuario_editar", args=[self.cliente.id])

    def _datos(self, **extra):
        base = {
            "username": "farmacia", "email": "f@e.cl",
            "role": "user", "is_active": "True",
        }
        base.update(extra)
        return base

    def test_actualiza_el_link_desde_la_interfaz(self):
        nuevo = "https://cloud.we-con.com.cn/device/AF-9921"
        respuesta = self.client.post(self.url, self._datos(link=nuevo))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()["ok"])
        self.cliente.profile.refresh_from_db()
        self.assertEqual(self.cliente.profile.link, nuevo)

    def test_rechaza_esquema_peligroso(self):
        respuesta = self.client.post(self.url, self._datos(link="javascript:alert(1)"))
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("link", respuesta.json()["errores"])

    def test_rechaza_username_duplicado(self):
        respuesta = self.client.post(self.url, self._datos(username="jefe"))
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("username", respuesta.json()["errores"])

    def test_rechaza_email_invalido(self):
        respuesta = self.client.post(self.url, self._datos(email="no-es-un-email"))
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("email", respuesta.json()["errores"])

    def test_admin_no_puede_desactivarse_a_si_mismo(self):
        url = reverse("usuario_editar", args=[self.admin.id])
        respuesta = self.client.post(url, {
            "username": "jefe", "role": "admin", "is_active": "",
        })
        self.assertEqual(respuesta.status_code, 400)

    def test_admin_no_puede_quitarse_su_rol(self):
        url = reverse("usuario_editar", args=[self.admin.id])
        respuesta = self.client.post(url, {
            "username": "jefe", "role": "user", "is_active": "True",
        })
        self.assertEqual(respuesta.status_code, 400)

    def test_actualiza_datos_del_sitio(self):
        self.client.post(self.url, self._datos(
            location="Antofagasta", manager_name="Ana Ruiz", external_id="AF-01"
        ))
        perfil = Profile.objects.get(user=self.cliente)
        self.assertEqual(perfil.location, "Antofagasta")
        self.assertEqual(perfil.manager_name, "Ana Ruiz")


class PanelUsuarioTest(TestCase):
    def setUp(self):
        self.cliente = User.objects.create_user("farmacia", "f@e.cl", "x", role="user")
        perfil = self.cliente.profile
        perfil.link = "https://cloud.we-con.com.cn/device/AF-1"
        perfil.save()
        self.client.force_login(self.cliente)

    def test_muestra_el_formulario_de_consumo(self):
        # La vista lo preparaba pero la plantilla nunca lo renderizaba.
        respuesta = self.client.get(reverse("user_dashboard"))
        self.assertContains(respuesta, 'name="month_choice"')
        self.assertContains(respuesta, "Registrar consumo")

    def test_el_usuario_puede_registrar_su_consumo(self):
        self.client.post(reverse("user_dashboard"), {
            "year": "2025", "month_choice": "may",
            "m3_water": "100", "m3_gas": "50",
        })
        self.assertTrue(
            GasConsumption.objects.filter(
                user=self.cliente, year=2025, month="may"
            ).exists()
        )

    def test_rechaza_consumo_sin_agua_ni_gas(self):
        self.client.post(reverse("user_dashboard"), {
            "year": "2025", "month_choice": "may",
        })
        self.assertEqual(GasConsumption.objects.count(), 0)

    def test_rechaza_anio_fuera_de_rango(self):
        self.client.post(reverse("user_dashboard"), {
            "year": "1800", "month_choice": "may", "m3_gas": "10",
        })
        self.assertEqual(GasConsumption.objects.count(), 0)

    def test_muestra_el_link_de_la_caldera(self):
        respuesta = self.client.get(reverse("user_dashboard"))
        self.assertContains(respuesta, "https://cloud.we-con.com.cn/device/AF-1")
        self.assertContains(respuesta, "Ver mi caldera")

    def test_avisa_cuando_no_hay_link(self):
        self.cliente.profile.link = ""
        self.cliente.profile.save()
        respuesta = self.client.get(reverse("user_dashboard"))
        self.assertContains(respuesta, "Aún no hay un link configurado")


class PreferenciasReporteTest(TestCase):
    def setUp(self):
        self.cliente = User.objects.create_user("farmacia", "f@e.cl", "x", role="user")
        self.client.force_login(self.cliente)

    def test_guarda_preferencias_validas(self):
        respuesta = self.client.post(
            reverse("save_prefs"),
            data='{"report_frequency":"m","report_format":"csv","report_email":"a@b.cl"}',
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.cliente.profile.refresh_from_db()
        self.assertEqual(self.cliente.profile.report_frequency, "m")
        self.assertEqual(self.cliente.profile.report_email, "a@b.cl")

    def test_rechaza_valores_invalidos(self):
        # Antes se hacía setattr() directo con lo que llegara en el JSON.
        respuesta = self.client.post(
            reverse("save_prefs"),
            data='{"report_frequency":"cada-rato","report_email":"no-es-email"}',
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.cliente.profile.refresh_from_db()
        self.assertEqual(self.cliente.profile.report_frequency, "off")


class DescargaReportesTest(TestCase):
    def setUp(self):
        self.cliente = User.objects.create_user("farmacia", "f@e.cl", "x", role="user")
        services.registrar_consumo(
            user=self.cliente, year=2025, month="may", m3_water=100, cost=1000
        )
        self.client.force_login(self.cliente)

    def test_descarga_csv(self):
        respuesta = self.client.get(reverse("download_report") + "?year=2025&format=csv")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "text/csv")
        self.assertIn("attachment", respuesta["Content-Disposition"])

    def test_descarga_pdf(self):
        respuesta = self.client.get(reverse("download_report") + "?year=2025&format=pdf")
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.content.startswith(b"%PDF"))

    def test_formato_desconocido_da_404(self):
        respuesta = self.client.get(reverse("download_report") + "?year=2025&format=doc")
        self.assertEqual(respuesta.status_code, 404)

    def test_envio_por_correo(self):
        from django.core import mail
        respuesta = self.client.post(
            reverse("email_report"),
            data='{"year":2025,"format":"csv","to":"destino@ematel.cl"}',
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["destino@ematel.cl"])

    def test_envio_sin_destinatario_falla_con_mensaje(self):
        self.cliente.email = ""
        self.cliente.save()
        self.cliente.profile.report_email = ""
        self.cliente.profile.save()
        respuesta = self.client.post(
            reverse("email_report"), data='{"year":2025}',
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 400)


class AltaDeConsumoAdminTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("jefe", password="x", role="admin")
        self.cliente = User.objects.create_user("farmacia", password="x", role="user")
        self.client.force_login(self.admin)

    def test_alta_por_formulario(self):
        self.client.post(reverse("admin_dashboard"), {
            "user": self.cliente.id, "year": "2025", "month_choice": "jul",
            "m3_water": "99.9", "m3_gas": "55.5", "cost": "300000",
        })
        registro = GasConsumption.objects.get(user=self.cliente, year=2025, month="jul")
        self.assertEqual(registro.m3_water, Decimal("99.90"))
        self.assertEqual(registro.cost, Decimal("300000"))

    def test_alta_por_json(self):
        respuesta = self.client.post(
            reverse("admin_add_consumption"),
            data=f'{{"user_id":{self.cliente.id},"year":2025,"month":"Agosto","m3_gas":10}}',
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()["ok"])
        self.assertTrue(
            GasConsumption.objects.filter(
                user=self.cliente, year=2025, month="ago"
            ).exists()
        )

    def test_json_con_mes_invalido(self):
        respuesta = self.client.post(
            reverse("admin_add_consumption"),
            data=f'{{"user_id":{self.cliente.id},"year":2025,"month":"xyz"}}',
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 400)

    def test_json_con_usuario_inexistente(self):
        respuesta = self.client.post(
            reverse("admin_add_consumption"),
            data='{"user_id":99999,"year":2025,"month":"ene"}',
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_datos_de_graficos(self):
        services.registrar_consumo(
            user=self.cliente, year=2025, month="may", m3_water=100
        )
        respuesta = self.client.get(
            reverse("admin_chart_data")
            + f"?user_id={self.cliente.id}&year_now=2025&year_prev=2024"
        )
        datos = respuesta.json()["chart_data"]
        self.assertEqual(datos["water"]["now"][4], 100.0)


class PerfilTest(TestCase):
    def test_se_crea_perfil_automaticamente(self):
        usuario = User.objects.create_user("nuevo", password="x")
        self.assertTrue(Profile.objects.filter(user=usuario).exists())

    def test_calcula_proxima_mantencion(self):
        import datetime
        usuario = User.objects.create_user("nuevo", password="x")
        perfil = usuario.profile
        perfil.last_maintenance = datetime.date(2025, 1, 31)
        perfil.maintenance_interval_months = 6
        perfil.save()
        self.assertEqual(perfil.next_maintenance, datetime.date(2025, 7, 31))

    def test_hereda_el_email_para_reportes(self):
        usuario = User.objects.create_user("nuevo", "n@e.cl", "x")
        perfil = usuario.profile
        perfil.save()
        self.assertEqual(perfil.report_email, "n@e.cl")


class RutasTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("jefe", password="x", role="admin")

    def test_listado_de_usuarios_redirige(self):
        # Apuntaba a una plantilla inexistente y daba TemplateDoesNotExist.
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse("usuarios_lista"))
        self.assertEqual(respuesta.status_code, 302)

    def test_home_redirige_segun_rol(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse("home"))
        self.assertRedirects(respuesta, reverse("admin_dashboard"))

    def test_login_muestra_error_con_credenciales_malas(self):
        respuesta = self.client.post(reverse("login"), {
            "username": "jefe", "password": "incorrecta",
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Credenciales inválidas")
