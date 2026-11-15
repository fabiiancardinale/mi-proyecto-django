import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:material_ui/material_ui.dart';

import '../api/modelos.dart';
import '../formato.dart';
import '../tema.dart';

enum Magnitud { agua, gas }

/// Barras mensuales de un año comparadas con otro, para agua o gas.
class GraficoConsumo extends StatelessWidget {
  const GraficoConsumo({
    super.key,
    required this.magnitud,
    required this.anio,
    required this.serie,
    this.anioComparado,
    this.serieComparada,
  });

  final Magnitud magnitud;
  final int anio;
  final Serie serie;
  final int? anioComparado;
  final Serie? serieComparada;

  List<double?> _valores(Serie s) => magnitud == Magnitud.agua ? s.agua : s.gas;

  @override
  Widget build(BuildContext context) {
    final color = magnitud == Magnitud.agua ? Colores.agua : Colores.gas;
    final principal = _valores(serie);
    final comparada = serieComparada == null ? null : _valores(serieComparada!);

    final maximo = [...principal, ...?comparada].whereType<double>().fold<double>(0, (a, b) => b > a ? b : a);
    final paso = _pasoRedondo(maximo / 4);
    final tope = paso * 4 < maximo * 1.05 ? paso * 5 : paso * 4;

    BarChartRodData barra(double? v, Color c) => BarChartRodData(
          toY: v ?? 0,
          color: v == null ? Colors.transparent : c,
          width: comparada == null ? 12 : 6,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(3)),
        );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          height: 200,
          child: BarChart(
            BarChartData(
              maxY: tope,
              alignment: BarChartAlignment.spaceAround,
              gridData: FlGridData(
                drawVerticalLine: false,
                horizontalInterval: paso,
                getDrawingHorizontalLine: (_) => const FlLine(color: Colores.linea, strokeWidth: 1),
              ),
              borderData: FlBorderData(show: false),
              titlesData: FlTitlesData(
                topTitles: const AxisTitles(),
                rightTitles: const AxisTitles(),
                leftTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 36,
                    interval: paso,
                    getTitlesWidget: (valor, meta) => SideTitleWidget(
                      meta: meta,
                      child: Text(valor.round().toString(), style: const TextStyle(fontSize: 10, color: Colores.textoSuave)),
                    ),
                  ),
                ),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    getTitlesWidget: (valor, meta) => SideTitleWidget(
                      meta: meta,
                      child: Text(mesesCortos[valor.toInt()][0],
                          style: const TextStyle(fontSize: 10, color: Colores.textoSuave)),
                    ),
                  ),
                ),
              ),
              barTouchData: BarTouchData(
                touchTooltipData: BarTouchTooltipData(
                  getTooltipColor: (_) => Colores.tinta,
                  getTooltipItem: (grupo, _, barra, indiceBarra) {
                    final valores = indiceBarra == 0 ? principal : comparada!;
                    final v = valores[grupo.x];
                    if (v == null) return null;
                    final a = indiceBarra == 0 ? anio : anioComparado;
                    return BarTooltipItem(
                      '${mesesCortos[grupo.x]} $a\n${m3(v)} m³',
                      const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w500),
                    );
                  },
                ),
              ),
              barGroups: [
                for (var i = 0; i < 12; i++)
                  BarChartGroupData(
                    x: i,
                    barsSpace: 2,
                    barRods: [
                      barra(principal[i], color),
                      if (comparada != null) barra(comparada[i], Colores.anterior.withValues(alpha: .55)),
                    ],
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 14,
          children: [
            _Leyenda(color: color, texto: '$anio'),
            if (comparada != null) _Leyenda(color: Colores.anterior, texto: '$anioComparado'),
          ],
        ),
      ],
    );
  }
}

/// Redondea el paso del eje a 1, 2, 2,5 o 5 por potencia de 10 (10, 20, 25, 50...).
double _pasoRedondo(double bruto) {
  if (bruto <= 0) return 2.5;
  final magnitud = math.pow(10, (math.log(bruto) / math.ln10).floor()).toDouble();
  for (final m in const [1.0, 2.0, 2.5, 5.0, 10.0]) {
    if (bruto <= m * magnitud) return m * magnitud;
  }
  return 10 * magnitud;
}

class _Leyenda extends StatelessWidget {
  const _Leyenda({required this.color, required this.texto});

  final Color color;
  final String texto;

  @override
  Widget build(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(width: 10, height: 10, decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(3))),
          const SizedBox(width: 6),
          Text(texto, style: const TextStyle(fontSize: 12, color: Colores.textoSuave)),
        ],
      );
}
