import 'package:google_fonts/google_fonts.dart';
import 'package:material_ui/material_ui.dart';

/// Colores de EMATEL. Son los mismos que static/theme.css en la web.
abstract final class Colores {
  static const tinta = Color(0xFF0F1A2E);
  static const tinta2 = Color(0xFF18263F);
  static const primario = Color(0xFF0B6BCB);
  static const agua = Color(0xFF0891B2);
  static const aguaSuave = Color(0xFFE0F5FA);
  static const gas = Color(0xFFE2730B);
  static const gasSuave = Color(0xFFFDF0E2);
  static const costo = Color(0xFF0F9D6B);
  static const costoSuave = Color(0xFFE3F6EE);
  static const anterior = Color(0xFF94A3B8);
  static const ok = Color(0xFF0F9D6B);
  static const aviso = Color(0xFFC86A04);
  static const avisoSuave = Color(0xFFFFF3DF);
  static const peligro = Color(0xFFD23B3B);
  static const peligroSuave = Color(0xFFFDEAEA);
  static const fondo = Color(0xFFF3F5F9);
  static const superficie = Color(0xFFFFFFFF);
  static const superficie3 = Color(0xFFEEF2F7);
  static const texto = Color(0xFF0F1A2E);
  static const textoSuave = Color(0xFF66748A);
  static const linea = Color(0xFFE3E8EF);
}

ThemeData construirTema() {
  final base = ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: Colores.primario,
      primary: Colores.primario,
      surface: Colores.superficie,
    ),
    scaffoldBackgroundColor: Colores.fondo,
  );
  final texto = GoogleFonts.ibmPlexSansTextTheme(base.textTheme).apply(
    bodyColor: Colores.texto,
    displayColor: Colores.texto,
  );
  final borde = OutlineInputBorder(
    borderRadius: BorderRadius.circular(10),
    borderSide: const BorderSide(color: Colores.linea),
  );

  return base.copyWith(
    textTheme: texto,
    appBarTheme: AppBarTheme(
      backgroundColor: Colores.fondo,
      foregroundColor: Colores.texto,
      elevation: 0,
      scrolledUnderElevation: 0,
      titleTextStyle: texto.titleLarge?.copyWith(fontWeight: FontWeight.w600),
    ),
    cardTheme: CardThemeData(
      color: Colores.superficie,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: const BorderSide(color: Colores.linea),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colores.superficie,
      border: borde,
      enabledBorder: borde,
      focusedBorder: borde.copyWith(
        borderSide: const BorderSide(color: Colores.primario, width: 1.6),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(48),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        textStyle: texto.labelLarge?.copyWith(fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size.fromHeight(44),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        side: const BorderSide(color: Colores.linea),
      ),
    ),
    dividerTheme: const DividerThemeData(color: Colores.linea, space: 1),
  );
}
