import 'package:material_ui/material_ui.dart';
import 'package:url_launcher/url_launcher.dart';

import '../api/cliente_api.dart';
import '../api/modelos.dart';
import '../formato.dart';
import '../tema.dart';
import '../widgets/grafico_consumo.dart';
import '../widgets/tarjetas.dart';
import 'admin/editar_cliente.dart';
import 'admin/lista_clientes.dart' show Etiqueta;
import 'inicio.dart';
import 'registrar.dart';

/// Panel de consumo de un cliente. Si [usuarioId] viene, lo abre un
/// administrador para ver a ese cliente.
class PantallaPanel extends StatefulWidget {
  const PantallaPanel({
    super.key,
    required this.api,
    this.panelInicial,
    this.usuarioId,
    this.esAdmin = false,
    this.ficha,
  });

  final ClienteApi api;
  final Panel? panelInicial;
  final int? usuarioId;
  final bool esAdmin;

  /// Cuenta del cliente, cuando lo abre un administrador.
  final FichaCliente? ficha;

  @override
  State<PantallaPanel> createState() => _PantallaPanelState();
}

class _PantallaPanelState extends State<PantallaPanel> {
  Panel? _panel;
  Object? _error;
  Magnitud _magnitud = Magnitud.agua;
  int? _anioA;
  int? _anioB;
  int? _anioHistorial;
  late FichaCliente? _ficha = widget.ficha;

  @override
  void initState() {
    super.initState();
    if (widget.panelInicial != null) {
      _aplicar(widget.panelInicial!);
    } else {
      _cargar();
    }
  }

  void _aplicar(Panel p) {
    _panel = p;
    _error = null;
    final anios = p.anios;
    _anioA = anios.contains(_anioA) ? _anioA : anios.firstOrNull;
    _anioB = anios.contains(_anioB) ? _anioB : (anios.length > 1 ? anios[1] : null);
    _anioHistorial = anios.contains(_anioHistorial) ? _anioHistorial : anios.firstOrNull;
  }

  Future<void> _cargar() async {
    try {
      final p = await widget.api.panel(usuarioId: widget.usuarioId);
      if (mounted) setState(() => _aplicar(p));
    } on SesionExpirada catch (e) {
      if (mounted) await salir(context, widget.api, mensaje: e.mensaje);
    } catch (e) {
      if (mounted) setState(() => _error = e);
    }
  }

  Future<void> _registrar() async {
    final guardado = await mostrarRegistro(
      context,
      api: widget.api,
      usuarioId: widget.usuarioId,
      conCosto: widget.esAdmin,
    );
    if (guardado == true) {
      await _cargar();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Consumo guardado')));
      }
    }
  }

  Future<void> _editar() async {
    final guardado = await Navigator.of(context).push<FichaCliente>(
      MaterialPageRoute(builder: (_) => PantallaEditarCliente(api: widget.api, ficha: _ficha)),
    );
    if (guardado == null || !mounted) return;
    setState(() => _ficha = guardado);
    await _cargar();
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Cambios guardados')));
  }

  Future<void> _eliminar() async {
    final f = _ficha!;
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('¿Eliminar a ${f.username}?'),
        content: const Text('Se borrarán también todos sus registros de consumo. Esta acción no se puede deshacer.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colores.peligro, minimumSize: const Size(0, 40)),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Eliminar'),
          ),
        ],
      ),
    );
    if (confirmado != true || !mounted) return;
    try {
      await widget.api.eliminarCliente(f.id);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Cliente "${f.username}" eliminado')));
      Navigator.of(context).pop(true);
    } on ErrorApi catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.mensaje)));
    }
  }

  Future<void> _abrirCaldera(String link) async {
    final ok = await launchUrl(Uri.parse(link), mode: LaunchMode.externalApplication);
    if (!ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('No se pudo abrir el link')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final panel = _panel;
    final viendoCliente = widget.usuarioId != null;

    return Scaffold(
      appBar: AppBar(
        title: Text(panel == null
            ? 'Consumo'
            : viendoCliente
                ? panel.usuario.username
                : 'Hola, ${panel.usuario.nombre}'),
        actions: [
          if (_ficha != null) ...[
            IconButton(tooltip: 'Editar cliente', icon: const Icon(Icons.edit_outlined), onPressed: _editar),
            PopupMenuButton<String>(
              onSelected: (v) => v == 'eliminar' ? _eliminar() : null,
              itemBuilder: (_) => const [
                PopupMenuItem(
                  value: 'eliminar',
                  child: ListTile(
                    leading: Icon(Icons.delete_outline, color: Colores.peligro),
                    title: Text('Eliminar cliente', style: TextStyle(color: Colores.peligro)),
                    contentPadding: EdgeInsets.zero,
                  ),
                ),
              ],
            ),
          ],
          if (!viendoCliente)
            IconButton(
              tooltip: 'Cerrar sesión',
              icon: const Icon(Icons.logout),
              onPressed: () => salir(context, widget.api),
            ),
        ],
      ),
      floatingActionButton: panel == null
          ? null
          : FloatingActionButton.extended(
              onPressed: _registrar,
              icon: const Icon(Icons.add),
              label: const Text('Registrar'),
            ),
      body: switch ((panel, _error)) {
        (null, null) => const Center(child: CircularProgressIndicator()),
        (null, final error?) => _ErrorCarga(error: error, reintentar: _cargar),
        (final p?, _) => RefreshIndicator(onRefresh: _cargar, child: _contenido(p)),
      },
    );
  }

  Widget _contenido(Panel p) {
    final perfil = p.perfil;
    final t = Theme.of(context).textTheme;
    final r = p.resumen;
    final dias = perfil?.diasParaMantencion;

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 96),
      children: [
        if (perfil != null && perfil.ubicacion.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Row(
              children: [
                const Icon(Icons.place_outlined, size: 16, color: Colores.textoSuave),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    [perfil.ubicacion, if (perfil.idExterno.isNotEmpty) perfil.idExterno].join(' · '),
                    style: t.bodyMedium?.copyWith(color: Colores.textoSuave),
                  ),
                ),
              ],
            ),
          ),

        if (perfil != null && perfil.tieneLink)
          FilledButton.icon(
            onPressed: () => _abrirCaldera(perfil.link),
            icon: const Icon(Icons.speed),
            label: Text(widget.usuarioId == null ? 'Ver mi caldera' : 'Ver caldera'),
          )
        else
          Aviso(
            texto: widget.esAdmin
                ? 'Este cliente no tiene link de Wecon. Agrégalo con «Editar».'
                : 'Aún no hay un link configurado para esta caldera. Pídele a un administrador que lo agregue.',
          ),
        const SizedBox(height: 16),

        // ---------------------------------------------------- Indicadores
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          childAspectRatio: 1.45,
          children: [
            Indicador(
              etiqueta: 'Agua ${p.anio ?? ''}',
              valor: m3(r.totalAgua),
              unidad: 'm³',
              nota: 'Prom. ${m3(r.promedioAgua)} m³/mes',
              icono: Icons.water_drop,
              color: Colores.agua,
              fondo: Colores.aguaSuave,
            ),
            Indicador(
              etiqueta: 'Gas ${p.anio ?? ''}',
              valor: m3(r.totalGas),
              unidad: 'm³',
              nota: 'Prom. ${m3(r.promedioGas)} m³/mes',
              icono: Icons.local_fire_department,
              color: Colores.gas,
              fondo: Colores.gasSuave,
            ),
            Indicador(
              etiqueta: 'Costo ${p.anio ?? ''}',
              valor: pesos(r.totalCosto),
              nota: 'Acumulado del año',
              icono: Icons.payments_outlined,
              color: Colores.costo,
              fondo: Colores.costoSuave,
            ),
            Indicador(
              etiqueta: 'Mantención',
              valor: dias == null ? '—' : (dias < 0 ? 'Vencida' : '$dias'),
              unidad: dias != null && dias >= 0 ? 'días' : null,
              nota: perfil?.proximaMantencion == null ? 'Sin fecha' : fecha(perfil!.proximaMantencion),
              colorNota: dias != null && dias < 0 ? Colores.peligro : null,
              icono: Icons.build_outlined,
              color: dias == null ? Colores.textoSuave : (dias < 0 ? Colores.peligro : (dias <= 30 ? Colores.aviso : Colores.ok)),
              fondo: dias == null ? Colores.superficie3 : (dias < 0 ? Colores.peligroSuave : (dias <= 30 ? Colores.avisoSuave : Colores.costoSuave)),
            ),
          ],
        ),
        const SizedBox(height: 16),

        // ------------------------------------------------------- Gráfico
        Seccion(
          titulo: 'Consumo mensual',
          icono: Icons.bar_chart,
          child: p.series.isEmpty
              ? const _Vacio('Cuando registres tu primer consumo verás aquí el gráfico.')
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    SegmentedButton<Magnitud>(
                      segments: const [
                        ButtonSegment(value: Magnitud.agua, label: Text('Agua'), icon: Icon(Icons.water_drop_outlined)),
                        ButtonSegment(value: Magnitud.gas, label: Text('Gas'), icon: Icon(Icons.local_fire_department_outlined)),
                      ],
                      selected: {_magnitud},
                      onSelectionChanged: (s) => setState(() => _magnitud = s.first),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(child: _selectorAnio(p.anios, _anioA, (a) => setState(() => _anioA = a))),
                        const Padding(
                          padding: EdgeInsets.symmetric(horizontal: 10),
                          child: Text('vs', style: TextStyle(color: Colores.textoSuave)),
                        ),
                        Expanded(
                          child: _selectorAnio(p.anios, _anioB, (a) => setState(() => _anioB = a), permitirNinguno: true),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    if (_anioA != null)
                      GraficoConsumo(
                        magnitud: _magnitud,
                        anio: _anioA!,
                        serie: p.series[_anioA]!,
                        anioComparado: _anioB == _anioA ? null : _anioB,
                        serieComparada: _anioB == null || _anioB == _anioA ? null : p.series[_anioB],
                      ),
                  ],
                ),
        ),
        const SizedBox(height: 16),

        // ------------------------------------------------------ Historial
        Seccion(
          titulo: 'Historial',
          icono: Icons.list_alt,
          relleno: false,
          child: p.historial.isEmpty
              ? const Padding(padding: EdgeInsets.all(16), child: _Vacio('Aún no hay registros de consumo.'))
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (p.anios.length > 1)
                      SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                        child: Row(
                          children: [
                            for (final a in p.anios)
                              Padding(
                                padding: const EdgeInsets.only(right: 8),
                                child: ChoiceChip(
                                  label: Text('$a'),
                                  selected: _anioHistorial == a,
                                  onSelected: (_) => setState(() => _anioHistorial = a),
                                ),
                              ),
                          ],
                        ),
                      ),
                    for (final f in p.historial.where((f) => f.anio == _anioHistorial)) _FilaMes(f),
                  ],
                ),
        ),
        const SizedBox(height: 16),

        // ---------------------------------------------- Cuenta (solo admin)
        if (_ficha case final f?) ...[
          Seccion(
            titulo: 'Cuenta',
            icono: Icons.manage_accounts_outlined,
            accion: TextButton(onPressed: _editar, child: const Text('Editar')),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(spacing: 6, children: [
                  f.activo
                      ? const Etiqueta('Activo', Colores.costoSuave, Colores.ok)
                      : const Etiqueta('Inactivo', Colores.superficie3, Colores.textoSuave),
                  f.esAdmin
                      ? const Etiqueta('Administrador', Colores.tinta, Colors.white)
                      : const Etiqueta('Cliente', Colores.superficie3, Colores.texto),
                  if (!f.tieneLink) const Etiqueta('Sin link Wecon', Colores.avisoSuave, Colores.aviso),
                ]),
                const SizedBox(height: 8),
                _Dato('Email', f.email),
                _Dato('Último acceso', f.ultimoAcceso == null ? 'Nunca' : fecha(f.ultimoAcceso!.toLocal())),
                _Dato('Creado', fecha(f.creado?.toLocal())),
                _Dato('Link Wecon', f.link),
              ],
            ),
          ),
          const SizedBox(height: 16),
        ],

        // --------------------------------------------------------- Sitio
        if (perfil != null)
          Seccion(
            titulo: 'Sitio y mantenciones',
            icono: Icons.apartment,
            child: Column(
              children: [
                _Dato('Encargado', perfil.encargado),
                _Dato('Teléfono', perfil.telefono),
                _Dato('Dirección', perfil.direccion),
                _Dato('Última mantención', fecha(perfil.ultimaMantencion)),
                _Dato('Próxima mantención', fechaLarga(perfil.proximaMantencion)),
                _Dato('Intervalo', '${perfil.intervaloMeses} meses'),
              ],
            ),
          ),
      ],
    );
  }

  Widget _selectorAnio(List<int> anios, int? valor, ValueChanged<int?> alCambiar, {bool permitirNinguno = false}) {
    return DropdownButtonFormField<int?>(
      initialValue: valor,
      isDense: true,
      decoration: const InputDecoration(contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10)),
      items: [
        if (permitirNinguno) const DropdownMenuItem<int?>(value: null, child: Text('—')),
        for (final a in anios) DropdownMenuItem<int?>(value: a, child: Text('$a')),
      ],
      onChanged: alCambiar,
    );
  }
}

class _FilaMes extends StatelessWidget {
  const _FilaMes(this.f);

  final FilaHistorial f;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    Widget medida(IconData icono, Color color, double? valor, double? pct) => Expanded(
          child: Row(
            children: [
              Icon(icono, size: 14, color: color),
              const SizedBox(width: 4),
              Text(m3(valor, fino: true), style: const TextStyle(fontFeatures: [FontFeature.tabularFigures()])),
              const SizedBox(width: 6),
              Variacion(pct),
            ],
          ),
        );

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: const BoxDecoration(border: Border(top: BorderSide(color: Colores.linea))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(f.nombreMes, style: t.titleSmall?.copyWith(fontWeight: FontWeight.w600))),
              Text(pesos(f.costo), style: t.bodyMedium?.copyWith(color: Colores.textoSuave)),
            ],
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              medida(Icons.water_drop, Colores.agua, f.agua, f.pctAgua),
              medida(Icons.local_fire_department, Colores.gas, f.gas, f.pctGas),
            ],
          ),
        ],
      ),
    );
  }
}

class _Dato extends StatelessWidget {
  const _Dato(this.etiqueta, this.valor);

  final String etiqueta;
  final String valor;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(width: 140, child: Text(etiqueta, style: const TextStyle(color: Colores.textoSuave))),
            Expanded(
              child: Text(valor.isEmpty ? '—' : valor, style: const TextStyle(fontWeight: FontWeight.w500)),
            ),
          ],
        ),
      );
}

class _Vacio extends StatelessWidget {
  const _Vacio(this.texto);

  final String texto;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 16),
        child: Text(texto, textAlign: TextAlign.center, style: const TextStyle(color: Colores.textoSuave)),
      );
}

class _ErrorCarga extends StatelessWidget {
  const _ErrorCarga({required this.error, required this.reintentar});

  final Object error;
  final VoidCallback reintentar;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off, size: 40, color: Colores.textoSuave),
              const SizedBox(height: 12),
              Text('$error', textAlign: TextAlign.center),
              const SizedBox(height: 16),
              FilledButton(onPressed: reintentar, child: const Text('Reintentar')),
            ],
          ),
        ),
      );
}
