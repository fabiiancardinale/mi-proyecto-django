import 'package:material_ui/material_ui.dart';

import '../api/cliente_api.dart';
import '../api/modelos.dart';
import 'admin/inicio_admin.dart';
import 'login.dart';
import 'panel.dart';

/// Decide a dónde va el usuario después de iniciar sesión:
/// los administradores ven la lista de clientes; el resto, su panel.
class PantallaInicio extends StatefulWidget {
  const PantallaInicio({super.key, required this.api});

  final ClienteApi api;

  @override
  State<PantallaInicio> createState() => _PantallaInicioState();
}

class _PantallaInicioState extends State<PantallaInicio> {
  late Future<Panel> _panel = widget.api.panel();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Panel>(
      future: _panel,
      builder: (context, estado) {
        if (estado.hasError) {
          final error = estado.error;
          if (error is SesionExpirada) {
            return PantallaLogin(api: widget.api, mensaje: error.mensaje);
          }
          return Scaffold(
            body: Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.cloud_off, size: 40),
                    const SizedBox(height: 12),
                    Text('$error', textAlign: TextAlign.center),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: () => setState(() => _panel = widget.api.panel()),
                      child: const Text('Reintentar'),
                    ),
                    TextButton(
                      onPressed: () async {
                        await widget.api.cerrarSesion();
                        if (!context.mounted) return;
                        Navigator.of(context).pushReplacement(
                          MaterialPageRoute(builder: (_) => PantallaLogin(api: widget.api)),
                        );
                      },
                      child: const Text('Cambiar de cuenta'),
                    ),
                  ],
                ),
              ),
            ),
          );
        }
        final panel = estado.data;
        if (panel == null) {
          return const Scaffold(body: Center(child: CircularProgressIndicator()));
        }
        return panel.usuario.esAdmin
            ? PantallaAdmin(api: widget.api, admin: panel.usuario)
            : PantallaPanel(api: widget.api, panelInicial: panel);
      },
    );
  }
}

/// Cierra la sesión y vuelve al login, borrando el historial de pantallas.
Future<void> salir(BuildContext context, ClienteApi api, {String? mensaje}) async {
  await api.cerrarSesion();
  if (!context.mounted) return;
  Navigator.of(context).pushAndRemoveUntil(
    MaterialPageRoute(builder: (_) => PantallaLogin(api: api, mensaje: mensaje)),
    (_) => false,
  );
}
