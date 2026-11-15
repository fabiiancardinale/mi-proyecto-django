import 'dart:async';

import 'package:material_ui/material_ui.dart';

import '../api/cliente_api.dart';
import '../api/modelos.dart';
import '../tema.dart';
import 'inicio.dart';
import 'panel.dart';

/// Lista de clientes para administradores. Al tocar uno se abre su panel.
class PantallaClientes extends StatefulWidget {
  const PantallaClientes({super.key, required this.api, required this.admin});

  final ClienteApi api;
  final Usuario admin;

  @override
  State<PantallaClientes> createState() => _PantallaClientesState();
}

class _PantallaClientesState extends State<PantallaClientes> {
  List<Cliente>? _clientes;
  Object? _error;
  String _busqueda = '';
  Timer? _espera;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  @override
  void dispose() {
    _espera?.cancel();
    super.dispose();
  }

  Future<void> _cargar() async {
    try {
      final c = await widget.api.clientes(busqueda: _busqueda);
      if (!mounted) return;
      setState(() {
        _clientes = c;
        _error = null;
      });
    } on SesionExpirada catch (e) {
      if (mounted) await salir(context, widget.api, mensaje: e.mensaje);
    } catch (e) {
      if (mounted) setState(() => _error = e);
    }
  }

  void _buscar(String texto) {
    _espera?.cancel();
    _espera = Timer(const Duration(milliseconds: 350), () {
      _busqueda = texto.trim();
      _cargar();
    });
  }

  @override
  Widget build(BuildContext context) {
    final clientes = _clientes;
    final sinLink = clientes?.where((c) => !c.tieneLink && !c.esAdmin).length ?? 0;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Clientes'),
        actions: [
          IconButton(tooltip: 'Cerrar sesión', icon: const Icon(Icons.logout), onPressed: () => salir(context, widget.api)),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
            child: TextField(
              onChanged: _buscar,
              decoration: const InputDecoration(
                hintText: 'Buscar por usuario o email',
                prefixIcon: Icon(Icons.search),
              ),
            ),
          ),
          if (sinLink > 0 && _busqueda.isEmpty)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
              child: Row(
                children: [
                  const Icon(Icons.link_off, size: 16, color: Colores.aviso),
                  const SizedBox(width: 6),
                  Text('$sinLink ${sinLink == 1 ? 'cliente' : 'clientes'} sin link de Wecon',
                      style: const TextStyle(color: Colores.aviso)),
                ],
              ),
            ),
          Expanded(
            child: switch ((clientes, _error)) {
              (null, null) => const Center(child: CircularProgressIndicator()),
              (null, final e?) => Center(child: Text('$e', textAlign: TextAlign.center)),
              (final lista?, _) => RefreshIndicator(
                  onRefresh: _cargar,
                  child: lista.isEmpty
                      ? ListView(children: const [
                          Padding(padding: EdgeInsets.all(32), child: Text('Sin resultados', textAlign: TextAlign.center)),
                        ])
                      : ListView.separated(
                          padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                          itemCount: lista.length,
                          separatorBuilder: (_, _) => const SizedBox(height: 8),
                          itemBuilder: (_, i) => _TarjetaCliente(
                            cliente: lista[i],
                            alTocar: () => Navigator.of(context).push(MaterialPageRoute(
                              builder: (_) => PantallaPanel(api: widget.api, usuarioId: lista[i].id, esAdmin: true),
                            )),
                          ),
                        ),
                ),
            },
          ),
        ],
      ),
    );
  }
}

class _TarjetaCliente extends StatelessWidget {
  const _TarjetaCliente({required this.cliente, required this.alTocar});

  final Cliente cliente;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) {
    final c = cliente;
    final subtitulo = [if (c.ubicacion.isNotEmpty) c.ubicacion, if (c.email.isNotEmpty) c.email].join(' · ');
    return Card(
      clipBehavior: Clip.antiAlias,
      child: ListTile(
        onTap: alTocar,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
        leading: CircleAvatar(
          backgroundColor: const Color(0xFFEFF6FE),
          foregroundColor: Colores.primario,
          child: Text(c.username.isEmpty ? '?' : c.username[0].toUpperCase()),
        ),
        title: Text(c.username, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: subtitulo.isEmpty ? null : Text(subtitulo, maxLines: 1, overflow: TextOverflow.ellipsis),
        trailing: Wrap(
          spacing: 6,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            if (c.esAdmin) const _Etiqueta('Admin', Colores.tinta, Colors.white),
            if (!c.activo) const _Etiqueta('Inactivo', Colores.superficie3, Colores.textoSuave),
            if (!c.tieneLink && !c.esAdmin) const Icon(Icons.link_off, size: 18, color: Colores.aviso),
            const Icon(Icons.chevron_right, color: Colores.textoSuave),
          ],
        ),
      ),
    );
  }
}

class _Etiqueta extends StatelessWidget {
  const _Etiqueta(this.texto, this.fondo, this.color);

  final String texto;
  final Color fondo;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(color: fondo, borderRadius: BorderRadius.circular(99)),
        child: Text(texto, style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w500)),
      );
}
