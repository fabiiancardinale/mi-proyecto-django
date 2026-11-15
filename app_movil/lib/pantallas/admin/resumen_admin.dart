import 'package:material_ui/material_ui.dart';

import '../../api/cliente_api.dart';
import '../../api/modelos.dart';
import '../../formato.dart';
import '../../tema.dart';
import '../../widgets/tarjetas.dart';
import '../inicio.dart';
import 'inicio_admin.dart';
import 'lista_clientes.dart';

/// Indicadores y clientes que requieren atención (mantención, sin link).
class ResumenAdminVista extends StatefulWidget {
  const ResumenAdminVista({super.key, required this.api, required this.alCambiar, required this.verClientes});

  final ClienteApi api;
  final VoidCallback alCambiar;
  final VoidCallback verClientes;

  @override
  State<ResumenAdminVista> createState() => _ResumenAdminVistaState();
}

class _ResumenAdminVistaState extends State<ResumenAdminVista> {
  ResumenAdmin? _datos;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    try {
      final d = await widget.api.resumenAdmin();
      if (!mounted) return;
      setState(() {
        _datos = d;
        _error = null;
      });
    } on SesionExpirada catch (e) {
      if (mounted) await salir(context, widget.api, mensaje: e.mensaje);
    } catch (e) {
      if (mounted) setState(() => _error = e);
    }
  }

  Future<void> _abrir(FichaCliente c) async {
    if (await abrirCliente(context, widget.api, c)) widget.alCambiar();
  }

  @override
  Widget build(BuildContext context) {
    final d = _datos;
    if (d == null) {
      return _error == null
          ? const Center(child: CircularProgressIndicator())
          : Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                  Text('$_error', textAlign: TextAlign.center),
                  const SizedBox(height: 12),
                  FilledButton(onPressed: _cargar, child: const Text('Reintentar')),
                ]),
              ),
            );
    }
    final c = d.conteo;
    final alertaMantencion = c.mantencionVencida > 0;

    return RefreshIndicator(
      onRefresh: _cargar,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 96),
        children: [
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 10,
            crossAxisSpacing: 10,
            childAspectRatio: 1.45,
            children: [
              Indicador(
                etiqueta: 'Usuarios',
                valor: '${c.total}',
                nota: '${c.activos} activos · ${c.inactivos} inactivos',
                icono: Icons.people_alt_outlined,
                color: Colores.primario,
                fondo: const Color(0xFFE6F0FC),
              ),
              Indicador(
                etiqueta: 'Activos',
                valor: '${c.activos}',
                nota: 'Pueden iniciar sesión',
                icono: Icons.how_to_reg_outlined,
                color: Colores.ok,
                fondo: Colores.costoSuave,
              ),
              Indicador(
                etiqueta: 'Sin link Wecon',
                valor: '${c.sinLink}',
                nota: c.sinLink == 0 ? 'Todos configurados' : 'Pendientes',
                icono: Icons.link_off,
                color: c.sinLink == 0 ? Colores.ok : Colores.aviso,
                fondo: c.sinLink == 0 ? Colores.costoSuave : Colores.avisoSuave,
              ),
              Indicador(
                etiqueta: 'Mantenciones',
                valor: '${c.mantencionVencida}',
                unidad: c.mantencionVencida == 1 ? 'vencida' : 'vencidas',
                nota: '${c.mantencionProxima} en los próximos 30 días',
                colorNota: c.mantencionProxima > 0 ? Colores.aviso : null,
                icono: Icons.build_outlined,
                color: alertaMantencion ? Colores.peligro : Colores.ok,
                fondo: alertaMantencion ? Colores.peligroSuave : Colores.costoSuave,
              ),
            ],
          ),
          const SizedBox(height: 16),
          Seccion(
            titulo: 'Mantenciones por vencer',
            icono: Icons.build_outlined,
            relleno: false,
            child: d.mantencion.isEmpty
                ? const _Vacio('Ninguna vencida ni en los próximos 30 días.')
                : Column(children: [
                    for (final f in d.mantencion)
                      FilaCliente(
                        cliente: f,
                        detalle: _textoMantencion(f),
                        colorDetalle: (f.diasParaMantencion ?? 0) < 0 ? Colores.peligro : Colores.aviso,
                        alTocar: () => _abrir(f),
                      ),
                  ]),
          ),
          const SizedBox(height: 16),
          Seccion(
            titulo: 'Sin link de Wecon',
            icono: Icons.link_off,
            relleno: false,
            child: d.sinLink.isEmpty
                ? const _Vacio('Todos los clientes tienen su link.')
                : Column(children: [
                    for (final f in d.sinLink)
                      FilaCliente(cliente: f, detalle: 'Toca para agregar el link', alTocar: () => _abrir(f)),
                  ]),
          ),
          const SizedBox(height: 12),
          TextButton.icon(
            onPressed: widget.verClientes,
            icon: const Icon(Icons.people_outline),
            label: const Text('Ver todos los clientes'),
          ),
        ],
      ),
    );
  }

  String _textoMantencion(FichaCliente f) {
    final dias = f.diasParaMantencion ?? 0;
    if (dias < 0) return 'Vencida hace ${-dias} ${dias == -1 ? 'día' : 'días'}';
    if (dias == 0) return 'Vence hoy';
    return 'Vence en $dias ${dias == 1 ? 'día' : 'días'} · ${fecha(f.proximaMantencion)}';
  }
}

class _Vacio extends StatelessWidget {
  const _Vacio(this.texto);

  final String texto;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(20),
        child: Row(children: [
          const Icon(Icons.check_circle_outline, color: Colores.ok, size: 20),
          const SizedBox(width: 10),
          Expanded(child: Text(texto, style: const TextStyle(color: Colores.textoSuave))),
        ]),
      );
}
