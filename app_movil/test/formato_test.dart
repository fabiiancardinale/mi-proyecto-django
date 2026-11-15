import 'package:ematel_app/formato.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';

void main() {
  setUpAll(() => initializeDateFormatting('es_CL'));

  test('leerNumero acepta coma y punto decimal', () {
    expect(leerNumero('120,5'), 120.5);
    expect(leerNumero('120.5'), 120.5);
    expect(leerNumero('1.200,5'), 1200.5);
    expect(leerNumero(' 35 '), 35);
    expect(leerNumero(''), isNull);
    expect(leerNumero('abc'), isNull);
  });

  test('formatos chilenos', () {
    expect(m3(1557.04), '1.557,0');
    expect(m3(null), '—');
    expect(pesos(2622132), '\$2.622.132');
    expect(porcentaje(-19.24), '19,2%');
  });
}
