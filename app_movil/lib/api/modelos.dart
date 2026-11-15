/// Modelos de lo que devuelve la API de Django (/api/panel/, /api/clientes/).
library;

double? _d(Object? v) => v == null ? null : (v as num).toDouble();
DateTime? _f(Object? v) => v == null ? null : DateTime.tryParse(v as String);

class Usuario {
  Usuario({required this.id, required this.username, required this.nombre, required this.email, required this.role});

  final int id;
  final String username;
  final String nombre;
  final String email;
  final String role;

  bool get esAdmin => role == 'admin';

  factory Usuario.desdeJson(Map<String, dynamic> j) => Usuario(
        id: j['id'] as int,
        username: j['username'] as String,
        nombre: (j['nombre'] ?? j['username']) as String,
        email: (j['email'] ?? '') as String,
        role: (j['role'] ?? 'user') as String,
      );
}

class Perfil {
  Perfil({
    required this.ubicacion,
    required this.idExterno,
    required this.encargado,
    required this.telefono,
    required this.direccion,
    required this.link,
    required this.ultimaMantencion,
    required this.proximaMantencion,
    required this.diasParaMantencion,
    required this.intervaloMeses,
  });

  final String ubicacion;
  final String idExterno;
  final String encargado;
  final String telefono;
  final String direccion;
  final String link;
  final DateTime? ultimaMantencion;
  final DateTime? proximaMantencion;
  final int? diasParaMantencion;
  final int intervaloMeses;

  bool get tieneLink => link.startsWith('http://') || link.startsWith('https://');

  factory Perfil.desdeJson(Map<String, dynamic> j) => Perfil(
        ubicacion: (j['location'] ?? '') as String,
        idExterno: (j['external_id'] ?? '') as String,
        encargado: (j['manager_name'] ?? '') as String,
        telefono: (j['phone'] ?? '') as String,
        direccion: (j['address'] ?? '') as String,
        link: (j['link'] ?? '') as String,
        ultimaMantencion: _f(j['last_maintenance']),
        proximaMantencion: _f(j['next_maintenance']),
        diasParaMantencion: j['days_to_next_maintenance'] as int?,
        intervaloMeses: (j['maintenance_interval_months'] ?? 12) as int,
      );
}

class Resumen {
  Resumen({this.totalAgua, this.totalGas, this.totalCosto, this.promedioAgua, this.promedioGas});

  final double? totalAgua;
  final double? totalGas;
  final double? totalCosto;
  final double? promedioAgua;
  final double? promedioGas;

  factory Resumen.desdeJson(Map<String, dynamic> j) => Resumen(
        totalAgua: _d(j['total_water']),
        totalGas: _d(j['total_gas']),
        totalCosto: _d(j['total_cost']),
        promedioAgua: _d(j['water_avg']),
        promedioGas: _d(j['gas_avg']),
      );
}

/// Doce posiciones (enero a diciembre). null = mes sin registro.
class Serie {
  Serie(this.agua, this.gas);

  final List<double?> agua;
  final List<double?> gas;

  factory Serie.desdeJson(Map<String, dynamic> j) => Serie(
        (j['water'] as List).map(_d).toList(),
        (j['gas'] as List).map(_d).toList(),
      );
}

class FilaHistorial {
  FilaHistorial({
    required this.anio,
    required this.mes,
    required this.nombreMes,
    this.agua,
    this.gas,
    this.costo,
    this.pctAgua,
    this.pctGas,
  });

  final int anio;
  final String mes;
  final String nombreMes;
  final double? agua;
  final double? gas;
  final double? costo;
  final double? pctAgua;
  final double? pctGas;

  factory FilaHistorial.desdeJson(Map<String, dynamic> j) => FilaHistorial(
        anio: j['year'] as int,
        mes: j['month'] as String,
        nombreMes: j['month_label'] as String,
        agua: _d(j['m3_water']),
        gas: _d(j['m3_gas']),
        costo: _d(j['cost']),
        pctAgua: _d(j['pct_water']),
        pctGas: _d(j['pct_gas']),
      );
}

class Panel {
  Panel({
    required this.usuario,
    required this.perfil,
    required this.anio,
    required this.resumen,
    required this.series,
    required this.historial,
  });

  final Usuario usuario;
  final Perfil? perfil;
  final int? anio;
  final Resumen resumen;
  final Map<int, Serie> series;
  final List<FilaHistorial> historial;

  /// Años con datos, del más reciente al más antiguo.
  List<int> get anios => series.keys.toList()..sort((a, b) => b.compareTo(a));

  factory Panel.desdeJson(Map<String, dynamic> j) => Panel(
        usuario: Usuario.desdeJson(j['usuario'] as Map<String, dynamic>),
        perfil: j['perfil'] == null ? null : Perfil.desdeJson(j['perfil'] as Map<String, dynamic>),
        anio: j['anio'] as int?,
        resumen: Resumen.desdeJson(j['resumen'] as Map<String, dynamic>),
        series: (j['series'] as Map<String, dynamic>).map(
          (anio, s) => MapEntry(int.parse(anio), Serie.desdeJson(s as Map<String, dynamic>)),
        ),
        historial: (j['historial'] as List)
            .map((f) => FilaHistorial.desdeJson(f as Map<String, dynamic>))
            .toList(),
      );
}

class Cliente {
  Cliente({
    required this.id,
    required this.username,
    required this.email,
    required this.ubicacion,
    required this.activo,
    required this.tieneLink,
    required this.esAdmin,
  });

  final int id;
  final String username;
  final String email;
  final String ubicacion;
  final bool activo;
  final bool tieneLink;
  final bool esAdmin;

  factory Cliente.desdeJson(Map<String, dynamic> j) => Cliente(
        id: j['id'] as int,
        username: j['username'] as String,
        email: (j['email'] ?? '') as String,
        ubicacion: (j['location'] ?? '') as String,
        activo: (j['is_active'] ?? true) as bool,
        tieneLink: (j['tiene_link'] ?? false) as bool,
        esAdmin: j['role'] == 'admin',
      );
}
