import 'package:material_ui/material_ui.dart';

import '../tema.dart';

/// Tarjeta con título e ícono, como las "card" de la web.
class Seccion extends StatelessWidget {
  const Seccion({super.key, required this.titulo, required this.icono, required this.child, this.accion, this.relleno = true});

  final String titulo;
  final IconData icono;
  final Widget child;
  final Widget? accion;
  final bool relleno;

  @override
  Widget build(BuildContext context) {
    final estilo = Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600);
    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 12, 12),
            child: Row(
              children: [
                Icon(icono, size: 18, color: Colores.textoSuave),
                const SizedBox(width: 8),
                Expanded(child: Text(titulo, style: estilo)),
                ?accion,
              ],
            ),
          ),
          const Divider(),
          relleno ? Padding(padding: const EdgeInsets.all(16), child: child) : child,
        ],
      ),
    );
  }
}

/// Indicador grande (consumo del año, costo, mantención).
class Indicador extends StatelessWidget {
  const Indicador({
    super.key,
    required this.etiqueta,
    required this.valor,
    required this.icono,
    required this.color,
    required this.fondo,
    this.unidad,
    this.nota,
    this.colorNota,
  });

  final String etiqueta;
  final String valor;
  final String? unidad;
  final String? nota;
  final Color? colorNota;
  final IconData icono;
  final Color color;
  final Color fondo;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(color: fondo, borderRadius: BorderRadius.circular(8)),
                  child: Icon(icono, size: 15, color: color),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(etiqueta,
                      style: t.labelMedium?.copyWith(color: Colores.textoSuave), overflow: TextOverflow.ellipsis),
                ),
              ],
            ),
            const SizedBox(height: 10),
            FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.centerLeft,
              child: Text.rich(TextSpan(children: [
                TextSpan(
                  text: valor,
                  style: t.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                    fontFeatures: const [FontFeature.tabularFigures()],
                  ),
                ),
                if (unidad != null)
                  TextSpan(text: ' $unidad', style: t.bodySmall?.copyWith(color: Colores.textoSuave)),
              ])),
            ),
            if (nota != null) ...[
              const SizedBox(height: 4),
              Text(nota!,
                  style: t.bodySmall?.copyWith(color: colorNota ?? Colores.textoSuave),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis),
            ],
          ],
        ),
      ),
    );
  }
}

/// Variación contra el año anterior. En consumo, subir es malo (rojo).
class Variacion extends StatelessWidget {
  const Variacion(this.pct, {super.key});

  final double? pct;

  @override
  Widget build(BuildContext context) {
    final p = pct;
    if (p == null) return const SizedBox.shrink();
    final sube = p > 0;
    final color = p == 0 ? Colores.textoSuave : (sube ? Colores.peligro : Colores.ok);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(sube ? Icons.arrow_upward : Icons.arrow_downward, size: 12, color: color),
        Text(
          '${p.abs().toStringAsFixed(1).replaceAll('.', ',')}%',
          style: TextStyle(fontSize: 12, color: color, fontWeight: FontWeight.w500),
        ),
      ],
    );
  }
}

/// Aviso de color (sin link, errores).
class Aviso extends StatelessWidget {
  const Aviso({super.key, required this.texto, this.icono = Icons.warning_amber_rounded, this.color = Colores.aviso, this.fondo = Colores.avisoSuave});

  final String texto;
  final IconData icono;
  final Color color;
  final Color fondo;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: fondo, borderRadius: BorderRadius.circular(10)),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icono, color: color, size: 20),
          const SizedBox(width: 10),
          Expanded(child: Text(texto, style: TextStyle(color: color))),
        ],
      ),
    );
  }
}
