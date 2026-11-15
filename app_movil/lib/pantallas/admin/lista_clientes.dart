import 'dart:async';

import 'package:material_ui/material_ui.dart';

import '../../api/cliente_api.dart';
import '../../api/modelos.dart';
import '../../tema.dart';
import '../inicio.dart';
import 'inicio_admin.dart';

enum _Filtro { todos, activos, inactivos, admins, sinLink }

/// Lista de clientes con búsqueda y filtros.
class ListaClientesVista extends StatefulWidget {
  const ListaClientesVista({super.key, required this.api, required this.alCambiar});

  final ClienteApi api;
  final VoidCallback alCambiar;

  @override
  State<ListaClientesVista> createState() => _ListaClientesVistaState();
}

class _ListaClientesVistaState extends State<ListaClientesVista> {
  List<FichaCliente>? _clientes;
  Object? _error;
  String _busqueda = '';
  _Filtro _filtro = _Filtro.todos;
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
      final c = await widget.api.clientes(
        busqueda: _busqueda,
        estado: switch (_filtro) { _Filtro.activos => 'activos', _Filtro.inactivos => 'inactivos', _ => null },
        rol: _filtro == _Filtro.admins ? 'admin' : null,
      );
      if (!mounted) return;
      setState(() {
        _clientes = _filtro == _Filtro.sinLink ? c.where((x) => !x.tieneLink && !x.esAdmin).toList() : c;
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

  Future<void> _abrir(FichaCliente c) async {
    if (await abrirCliente(context, widget.api, c)) widget.alCambiar();
  }

  @override
  Widget build(BuildContext context) {
    final lista = _clientes;
    const etiquetas = {
      _Filtro.todos: 'Todos',
      _Filtro.activos: 'Activos',
      _Filtro.inactivos: 'Inactivos',
      _Filtro.sinLink: 'Sin link',
      _Filtro.admins: 'Administradores',
    };

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
          child: TextField(
            onChanged: _buscar,
            decoration: const InputDecoration(
              hintText: 'Buscar por usuario, email o ubicación',
              prefixIcon: Icon(Icons.search),
            ),
          ),
        ),
        SizedBox(
          height: 40,
          child: ListView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            children: [
              for (final f in _Filtro.values)
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text(etiquetas[f]!),
                    selected: _filtro == f,
                    onSelected: (_) {
                      setState(() => _filtro = f);
                      _cargar();
                    },
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        Expanded(
          child: switch ((lista, _error)) {
            (null, null) => const Center(child: CircularProgressIndicator()),
            (null, final e?) => Center(child: Text('$e', textAlign: TextAlign.center)),
            (final l?, _) => RefreshIndicator(
                onRefresh: _cargar,
                child: l.isEmpty
                    ? ListView(children: const [
                        Padding(padding: EdgeInsets.all(32), child: Text('Sin resultados', textAlign: TextAlign.center)),
                      ])
                    : ListView.builder(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 96),
                        itemCount: l.length + 1,
                        itemBuilder: (_, i) => i == 0
                            ? Padding(
                                padding: const EdgeInsets.only(bottom: 8),
                                child: Text('${l.length} ${l.length == 1 ? 'resultado' : 'resultados'}',
                                    style: const TextStyle(color: Colores.textoSuave, fontSize: 12)),
                              )
                            : Padding(
                                padding: const EdgeInsets.only(bottom: 8),
                                child: Card(
                                  clipBehavior: Clip.antiAlias,
                                  child: FilaCliente(cliente: l[i - 1], alTocar: () => _abrir(l[i - 1]), sinBorde: true),
                                ),
                              ),
                      ),
              ),
          },
        ),
      ],
    );
  }
}

/// Fila de cliente con avatar, nombre, ubicación y distintivos.
class FilaCliente extends StatelessWidget {
  const FilaCliente({
    super.key,
    required this.cliente,
    required this.alTocar,
    this.detalle,
    this.colorDetalle,
    this.sinBorde = false,
  });

  final FichaCliente cliente;
  final VoidCallback alTocar;
  final String? detalle;
  final Color? colorDetalle;
  final bool sinBorde;

  @override
  Widget build(BuildContext context) {
    final c = cliente;
    final sub = detalle ?? [if (c.ubicacion.isNotEmpty) c.ubicacion, if (c.email.isNotEmpty) c.email].join(' · ');
    return DecoratedBox(
      decoration: BoxDecoration(
        border: sinBorde ? null : const Border(top: BorderSide(color: Colores.linea)),
      ),
      child: ListTile(
        onTap: alTocar,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
        leading: CircleAvatar(
          backgroundColor: c.activo ? const Color(0xFFEFF6FE) : Colores.superficie3,
          foregroundColor: c.activo ? Colores.primario : Colores.textoSuave,
          child: Text(c.username.isEmpty ? '?' : c.username[0].toUpperCase()),
        ),
        title: Text(c.username, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: sub.isEmpty
            ? null
            : Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: colorDetalle)),
        trailing: Wrap(
          spacing: 6,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            if (c.esAdmin) const Etiqueta('Admin', Colores.tinta, Colors.white),
            if (!c.activo) const Etiqueta('Inactivo', Colores.superficie3, Colores.textoSuave),
            if (!c.tieneLink && !c.esAdmin) const Icon(Icons.link_off, size: 18, color: Colores.aviso),
            const Icon(Icons.chevron_right, color: Colores.textoSuave),
          ],
        ),
      ),
    );
  }
}

class Etiqueta extends StatelessWidget {
  const Etiqueta(this.texto, this.fondo, this.color, {super.key});

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
