import 'package:intl/intl.dart';

/// Formatos chilenos: punto de miles y coma decimal.
final _m3 = NumberFormat('#,##0.0', 'es_CL');
final _m3Fino = NumberFormat('#,##0.00', 'es_CL');
final _pesos = NumberFormat('#,##0', 'es_CL');
final _fecha = DateFormat('dd/MM/yyyy', 'es_CL');
final _fechaLarga = DateFormat("d 'de' MMMM yyyy", 'es_CL');

String m3(double? v, {bool fino = false}) =>
    v == null ? '—' : (fino ? _m3Fino : _m3).format(v);

String pesos(double? v) => v == null ? '—' : '\$${_pesos.format(v)}';

String porcentaje(double? v) =>
    v == null ? '—' : '${NumberFormat('0.0', 'es_CL').format(v.abs())}%';

String fecha(DateTime? d) => d == null ? '—' : _fecha.format(d);

String fechaLarga(DateTime? d) => d == null ? '—' : _fechaLarga.format(d);

const mesesCortos = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];

const meses = [
  ('ene', 'Enero'), ('feb', 'Febrero'), ('mar', 'Marzo'), ('abr', 'Abril'),
  ('may', 'Mayo'), ('jun', 'Junio'), ('jul', 'Julio'), ('ago', 'Agosto'),
  ('sep', 'Septiembre'), ('oct', 'Octubre'), ('nov', 'Noviembre'), ('dic', 'Diciembre'),
];

/// Convierte lo que escribe el usuario en número.
/// "120,5" y "120.5" valen 120.5; "1.200,5" vale 1200.5.
double? leerNumero(String texto) {
  var limpio = texto.trim();
  if (limpio.isEmpty) return null;
  if (limpio.contains(',')) {
    limpio = limpio.replaceAll('.', '').replaceAll(',', '.');
  }
  return double.tryParse(limpio);
}
