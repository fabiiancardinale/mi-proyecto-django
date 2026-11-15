import 'dart:async';
import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import 'modelos.dart';

/// Servidor por defecto. Se puede cambiar al compilar:
///   flutter run --dart-define=API_URL=http://10.0.2.2:8000
/// o desde la pantalla de inicio de sesión ("Servidor").
const servidorPorDefecto = String.fromEnvironment('API_URL', defaultValue: 'http://82.25.79.89');

/// Error que se puede mostrar tal cual al usuario.
class ErrorApi implements Exception {
  ErrorApi(this.mensaje, {this.errores = const {}, this.codigo});

  final String mensaje;
  final Map<String, List<String>> errores;
  final int? codigo;

  @override
  String toString() => mensaje;
}

/// La sesión expiró y no se pudo renovar: hay que volver a iniciar sesión.
class SesionExpirada extends ErrorApi {
  SesionExpirada() : super('Tu sesión expiró. Vuelve a iniciar sesión.', codigo: 401);
}

/// Cliente HTTP de la API de EMATEL con autenticación JWT.
///
/// Guarda los tokens en el almacenamiento seguro del dispositivo y renueva
/// el token de acceso automáticamente cuando caduca.
class ClienteApi {
  ClienteApi({FlutterSecureStorage? almacen, http.Client? cliente})
      : _almacen = almacen ?? const FlutterSecureStorage(),
        _http = cliente ?? http.Client();

  final FlutterSecureStorage _almacen;
  final http.Client _http;
  static const _tiempoMaximo = Duration(seconds: 20);

  String servidor = servidorPorDefecto;
  String? _access;
  String? _refresh;

  bool get tieneSesion => _refresh != null;

  /// Recupera servidor y tokens guardados. Devuelve true si hay sesión.
  Future<bool> cargar() async {
    servidor = await _almacen.read(key: 'servidor') ?? servidorPorDefecto;
    _access = await _almacen.read(key: 'access');
    _refresh = await _almacen.read(key: 'refresh');
    return tieneSesion;
  }

  Future<void> iniciarSesion(String usuario, String clave, {required String servidor}) async {
    this.servidor = _normalizar(servidor);
    final r = await _enviar(() => _http.post(
          _uri('/api/auth/token/'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'username': usuario, 'password': clave}),
        ));
    if (r.statusCode == 401) {
      throw ErrorApi('Usuario o contraseña incorrectos.', codigo: 401);
    }
    final datos = _decodificar(r) as Map<String, dynamic>;
    _access = datos['access'] as String;
    _refresh = datos['refresh'] as String;
    await _almacen.write(key: 'servidor', value: this.servidor);
    await _almacen.write(key: 'access', value: _access);
    await _almacen.write(key: 'refresh', value: _refresh);
  }

  Future<void> cerrarSesion() async {
    _access = null;
    _refresh = null;
    await _almacen.delete(key: 'access');
    await _almacen.delete(key: 'refresh');
  }

  // ------------------------------------------------------------------ API

  Future<Panel> panel({int? usuarioId}) async {
    final datos = await _get('/api/panel/', {if (usuarioId != null) 'user_id': '$usuarioId'});
    return Panel.desdeJson(datos as Map<String, dynamic>);
  }

  // ----------------------------------------------------- Administración

  Future<ResumenAdmin> resumenAdmin() async =>
      ResumenAdmin.desdeJson(await _get('/api/admin/resumen/') as Map<String, dynamic>);

  /// [estado]: 'activos' o 'inactivos'. [rol]: 'admin' o 'user'.
  Future<List<FichaCliente>> clientes({String busqueda = '', String? estado, String? rol}) async {
    final datos = await _get('/api/clientes/', {
      if (busqueda.isNotEmpty) 'q': busqueda,
      'status': ?estado,
      'role': ?rol,
    });
    return [for (final c in datos as List) FichaCliente.desdeJson(c as Map<String, dynamic>)];
  }

  Future<FichaCliente> crearCliente(Map<String, Object?> datos) async =>
      FichaCliente.desdeJson(await _post('/api/clientes/', datos) as Map<String, dynamic>);

  /// Solo se modifican los campos enviados.
  Future<FichaCliente> editarCliente(int id, Map<String, Object?> datos) async => FichaCliente.desdeJson(
        await _conToken((t) => _http.patch(_uri('/api/clientes/$id/'), headers: _cabeceras(t), body: jsonEncode(datos)))
            as Map<String, dynamic>,
      );

  Future<void> eliminarCliente(int id) =>
      _conToken((t) => _http.delete(_uri('/api/clientes/$id/'), headers: _cabeceras(t)));

  /// Registra o actualiza un mes. Solo se envían los campos con valor, así
  /// que completar el gas de un mes que ya tenía agua no borra el agua.
  Future<bool> registrarConsumo({
    required int anio,
    required String mes,
    double? agua,
    double? gas,
    double? costo,
    int? dia,
    int? usuarioId,
  }) async {
    final datos = await _post('/api/consumption/', {
      'year': anio,
      'month': mes,
      'm3_water': ?agua,
      'm3_gas': ?gas,
      'cost': ?costo,
      'day': ?dia,
      'user_id': ?usuarioId,
    });
    return (datos as Map<String, dynamic>)['creado'] as bool;
  }

  // ------------------------------------------------------------ Internos

  Future<Object?> _get(String ruta, [Map<String, String>? query]) =>
      _conToken((t) => _http.get(_uri(ruta, query), headers: _cabeceras(t)));

  Future<Object?> _post(String ruta, Map<String, Object?> cuerpo) => _conToken(
        (t) => _http.post(_uri(ruta), headers: _cabeceras(t), body: jsonEncode(cuerpo)),
      );

  /// Hace la petición y, si el token de acceso caducó, lo renueva y reintenta una vez.
  Future<Object?> _conToken(Future<http.Response> Function(String token) peticion) async {
    if (_access == null) await _renovar();
    var r = await _enviar(() => peticion(_access!));
    if (r.statusCode == 401) {
      await _renovar();
      r = await _enviar(() => peticion(_access!));
    }
    if (r.statusCode == 401) throw SesionExpirada();
    return _decodificar(r);
  }

  Future<void> _renovar() async {
    if (_refresh == null) throw SesionExpirada();
    final r = await _enviar(() => _http.post(
          _uri('/api/auth/refresh/'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'refresh': _refresh}),
        ));
    if (r.statusCode != 200) {
      await cerrarSesion();
      throw SesionExpirada();
    }
    final datos = jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;
    _access = datos['access'] as String;
    await _almacen.write(key: 'access', value: _access);
    if (datos['refresh'] case final String nuevo) {
      _refresh = nuevo;
      await _almacen.write(key: 'refresh', value: nuevo);
    }
  }

  Future<http.Response> _enviar(Future<http.Response> Function() peticion) async {
    try {
      return await peticion().timeout(_tiempoMaximo);
    } on TimeoutException {
      throw ErrorApi('El servidor no responde. Revisa tu conexión.');
    } on http.ClientException {
      throw ErrorApi('No se pudo conectar con el servidor ($servidor).');
    }
  }

  Object? _decodificar(http.Response r) {
    Object? cuerpo;
    try {
      cuerpo = r.bodyBytes.isEmpty ? null : jsonDecode(utf8.decode(r.bodyBytes));
    } on FormatException {
      cuerpo = null;
    }
    if (r.statusCode >= 200 && r.statusCode < 300) return cuerpo;

    final errores = <String, List<String>>{};
    var mensaje = 'Error del servidor (${r.statusCode}).';
    if (cuerpo is Map<String, dynamic>) {
      if (cuerpo['detail'] case final String d) mensaje = d;
      if (cuerpo['errores'] case final Map<String, dynamic> e) {
        e.forEach((campo, lista) => errores[campo] = (lista as List).map((x) => '$x').toList());
        mensaje = errores.values.expand((x) => x).join(' ');
      }
    }
    throw ErrorApi(mensaje, errores: errores, codigo: r.statusCode);
  }

  Map<String, String> _cabeceras(String token) => {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      };

  Uri _uri(String ruta, [Map<String, String>? query]) =>
      Uri.parse('$servidor$ruta').replace(queryParameters: (query?.isEmpty ?? true) ? null : query);

  static String _normalizar(String url) {
    var u = url.trim();
    if (!u.startsWith('http://') && !u.startsWith('https://')) u = 'http://$u';
    while (u.endsWith('/')) {
      u = u.substring(0, u.length - 1);
    }
    return u;
  }
}
