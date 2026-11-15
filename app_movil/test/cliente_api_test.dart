import 'dart:convert';

import 'package:ematel_app/api/cliente_api.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

http.Response _json(Object cuerpo, [int codigo = 200]) =>
    http.Response.bytes(utf8.encode(jsonEncode(cuerpo)), codigo, headers: {'content-type': 'application/json'});

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  test('inicia sesión, guarda tokens y normaliza el servidor', () async {
    final api = ClienteApi(cliente: MockClient((r) async {
      expect(r.url.toString(), 'http://82.25.79.89/api/auth/token/');
      return _json({'access': 'a1', 'refresh': 'r1'});
    }));
    await api.iniciarSesion('hotel', 'x', servidor: '82.25.79.89/');
    expect(api.tieneSesion, isTrue);

    final otra = ClienteApi();
    expect(await otra.cargar(), isTrue);
    expect(otra.servidor, 'http://82.25.79.89');
  });

  test('credenciales malas dan un mensaje claro', () async {
    final api = ClienteApi(cliente: MockClient((_) async => _json({'detail': 'x'}, 401)));
    expect(
      () => api.iniciarSesion('hotel', 'mala', servidor: 'http://s'),
      throwsA(isA<ErrorApi>().having((e) => e.mensaje, 'mensaje', contains('incorrectos'))),
    );
  });

  test('renueva el token caducado y reintenta', () async {
    final rutas = <String>[];
    final api = ClienteApi(cliente: MockClient((r) async {
      rutas.add('${r.method} ${r.url.path} ${r.headers['Authorization'] ?? ''}'.trim());
      if (r.url.path == '/api/auth/token/') return _json({'access': 'viejo', 'refresh': 'r1'});
      if (r.url.path == '/api/auth/refresh/') return _json({'access': 'nuevo'});
      if (r.headers['Authorization'] == 'Bearer viejo') return _json({'detail': 'expirado'}, 401);
      return _json([]);
    }));
    await api.iniciarSesion('jefe', 'x', servidor: 'http://s');
    expect(await api.clientes(), isEmpty);
    expect(rutas, [
      'POST /api/auth/token/',
      'GET /api/clientes/ Bearer viejo',
      'POST /api/auth/refresh/',
      'GET /api/clientes/ Bearer nuevo',
    ]);
  });

  test('si el refresh también caducó, pide iniciar sesión otra vez', () async {
    FlutterSecureStorage.setMockInitialValues({'access': 'a', 'refresh': 'r'});
    final api = ClienteApi(cliente: MockClient((r) async => _json({'detail': 'x'}, 401)));
    await api.cargar();
    await expectLater(api.panel(), throwsA(isA<SesionExpirada>()));
    expect(api.tieneSesion, isFalse);
  });

  test('registrar envía solo los campos con valor y muestra errores del servidor', () async {
    Map<String, dynamic>? enviado;
    final api = ClienteApi(cliente: MockClient((r) async {
      if (r.url.path == '/api/auth/token/') return _json({'access': 'a', 'refresh': 'r'});
      enviado = jsonDecode(r.body) as Map<String, dynamic>;
      if (enviado!['month'] == 'xyz') {
        return _json({'errores': {'month': ['Mes inválido.']}}, 400);
      }
      return _json({'creado': false, 'registro': {}});
    }));
    await api.iniciarSesion('hotel', 'x', servidor: 'http://s');

    expect(await api.registrarConsumo(anio: 2026, mes: 'nov', gas: 120.5), isFalse);
    expect(enviado, {'year': 2026, 'month': 'nov', 'm3_gas': 120.5});

    await expectLater(
      api.registrarConsumo(anio: 2026, mes: 'xyz', gas: 1),
      throwsA(isA<ErrorApi>().having((e) => e.errores['month'], 'errores', ['Mes inválido.'])),
    );
  });

  test('administración: editar usa PATCH y eliminar acepta respuesta vacía', () async {
    final vistas = <String>[];
    final api = ClienteApi(cliente: MockClient((r) async {
      if (r.url.path == '/api/auth/token/') return _json({'access': 'a', 'refresh': 'r'});
      vistas.add('${r.method} ${r.url.path} ${r.body}');
      if (r.method == 'DELETE') return http.Response('', 204);
      return _json({'id': 7, 'username': 'hotel', 'link': 'https://w/1', 'es_admin': false, 'is_active': true});
    }));
    await api.iniciarSesion('jefe', 'x', servidor: 'http://s');

    final f = await api.editarCliente(7, {'link': 'https://w/1'});
    expect(f.link, 'https://w/1');
    expect(f.tieneLink, isTrue);
    await api.eliminarCliente(7);
    expect(vistas, ['PATCH /api/clientes/7/ {"link":"https://w/1"}', 'DELETE /api/clientes/7/ ']);
  });
}
