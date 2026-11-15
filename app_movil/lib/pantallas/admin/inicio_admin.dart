import 'package:material_ui/material_ui.dart';

import '../../api/cliente_api.dart';
import '../../api/modelos.dart';
import '../inicio.dart';
import 'editar_cliente.dart';
import 'lista_clientes.dart';
import 'resumen_admin.dart';

/// Inicio del administrador: pestañas Resumen y Clientes.
class PantallaAdmin extends StatefulWidget {
  const PantallaAdmin({super.key, required this.api, required this.admin});

  final ClienteApi api;
  final Usuario admin;

  @override
  State<PantallaAdmin> createState() => _PantallaAdminState();
}

class _PantallaAdminState extends State<PantallaAdmin> {
  int _pestana = 0;

  // Cambiar la clave obliga a las pestañas a recargar sus datos.
  int _version = 0;

  void _recargar() => setState(() => _version++);

  Future<void> _nuevoCliente() async {
    final creado = await Navigator.of(context).push<FichaCliente>(
      MaterialPageRoute(builder: (_) => PantallaEditarCliente(api: widget.api)),
    );
    if (creado != null && mounted) {
      _recargar();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Cliente "${creado.username}" creado')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_pestana == 0 ? 'Panel general' : 'Clientes'),
        actions: [
          IconButton(
            tooltip: 'Cerrar sesión',
            icon: const Icon(Icons.logout),
            onPressed: () => salir(context, widget.api),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _nuevoCliente,
        icon: const Icon(Icons.person_add_alt_1),
        label: const Text('Nuevo cliente'),
      ),
      body: IndexedStack(
        index: _pestana,
        children: [
          ResumenAdminVista(
            key: ValueKey('resumen$_version'),
            api: widget.api,
            alCambiar: _recargar,
            verClientes: () => setState(() => _pestana = 1),
          ),
          ListaClientesVista(key: ValueKey('lista$_version'), api: widget.api, alCambiar: _recargar),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _pestana,
        onDestinationSelected: (i) => setState(() => _pestana = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.space_dashboard_outlined), selectedIcon: Icon(Icons.space_dashboard), label: 'Resumen'),
          NavigationDestination(icon: Icon(Icons.people_outline), selectedIcon: Icon(Icons.people), label: 'Clientes'),
        ],
      ),
    );
  }
}

/// Abre el panel de un cliente. Devuelve true si se editó o eliminó.
Future<bool> abrirCliente(BuildContext context, ClienteApi api, FichaCliente cliente) async {
  final cambio = await Navigator.of(context).push<bool>(
    MaterialPageRoute(builder: (_) => PantallaClienteAdmin(api: api, cliente: cliente)),
  );
  return cambio ?? false;
}
