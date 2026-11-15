import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:material_ui/material_ui.dart';

import '../../api/cliente_api.dart';
import '../../api/modelos.dart';
import '../../formato.dart';
import '../../tema.dart';
import '../../widgets/tarjetas.dart';
import '../inicio.dart';
import '../panel.dart';

/// Panel de un cliente visto por el administrador (con editar y eliminar).
class PantallaClienteAdmin extends StatelessWidget {
  const PantallaClienteAdmin({super.key, required this.api, required this.cliente});

  final ClienteApi api;
  final FichaCliente cliente;

  @override
  Widget build(BuildContext context) =>
      PantallaPanel(api: api, usuarioId: cliente.id, esAdmin: true, ficha: cliente);
}

/// Alta (si [ficha] es null) o edición de un cliente. Devuelve la ficha guardada.
class PantallaEditarCliente extends StatefulWidget {
  const PantallaEditarCliente({super.key, required this.api, this.ficha});

  final ClienteApi api;
  final FichaCliente? ficha;

  @override
  State<PantallaEditarCliente> createState() => _PantallaEditarClienteState();
}

class _PantallaEditarClienteState extends State<PantallaEditarCliente> {
  final _form = GlobalKey<FormState>();
  late final FichaCliente? f = widget.ficha;
  bool get _esNuevo => f == null;

  late final _usuario = TextEditingController(text: f?.username);
  late final _email = TextEditingController(text: f?.email);
  final _clave1 = TextEditingController();
  final _clave2 = TextEditingController();
  late final _ubicacion = TextEditingController(text: f?.ubicacion);
  late final _idExterno = TextEditingController(text: f?.idExterno);
  late final _encargado = TextEditingController(text: f?.encargado);
  late final _telefono = TextEditingController(text: f?.telefono);
  late final _direccion = TextEditingController(text: f?.direccion);
  late final _link = TextEditingController(text: f?.link);
  late final _intervalo = TextEditingController(text: '${f?.intervaloMeses ?? 12}');

  late String _rol = f?.role ?? 'user';
  late bool _activo = f?.activo ?? true;
  late DateTime? _ultima = f?.ultimaMantencion;
  late DateTime? _proxima = f?.proximaMantencion;
  bool _proximaTocada = false;
  bool _verClave = false;

  bool _guardando = false;
  String? _error;
  Map<String, List<String>> _errores = {};

  @override
  void dispose() {
    for (final c in [_usuario, _email, _clave1, _clave2, _ubicacion, _idExterno, _encargado, _telefono, _direccion, _link, _intervalo]) {
      c.dispose();
    }
    super.dispose();
  }

  String? _err(String campo) => _errores[campo]?.join(' ');
  static final _iso = DateFormat('yyyy-MM-dd');

  Map<String, Object?> _datos() {
    final datos = <String, Object?>{
      'username': _usuario.text.trim(),
      'email': _email.text.trim(),
      'role': _rol,
      'location': _ubicacion.text.trim(),
      'external_id': _idExterno.text.trim(),
      'manager_name': _encargado.text.trim(),
      'phone': _telefono.text.trim(),
      'address': _direccion.text.trim(),
      'link': _link.text.trim(),
      'maintenance_interval_months': int.tryParse(_intervalo.text) ?? 12,
    };
    if (_esNuevo) {
      datos['password1'] = _clave1.text;
      datos['password2'] = _clave2.text;
      if (_ultima != null) datos['last_maintenance'] = _iso.format(_ultima!);
      if (_proxima != null) datos['next_maintenance'] = _iso.format(_proxima!);
    } else {
      datos['is_active'] = _activo;
      // Solo se envía la última mantención si cambió: así el servidor
      // recalcula la próxima, salvo que el admin la haya fijado a mano.
      if (_ultima != f!.ultimaMantencion) datos['last_maintenance'] = _ultima == null ? '' : _iso.format(_ultima!);
      if (_proximaTocada) datos['next_maintenance'] = _proxima == null ? '' : _iso.format(_proxima!);
    }
    return datos;
  }

  Future<void> _guardar() async {
    setState(() {
      _error = null;
      _errores = {};
    });
    if (!_form.currentState!.validate()) return;
    setState(() => _guardando = true);
    try {
      final guardado = _esNuevo
          ? await widget.api.crearCliente(_datos())
          : await widget.api.editarCliente(f!.id, _datos());
      if (mounted) Navigator.of(context).pop(guardado);
    } on SesionExpirada catch (e) {
      if (mounted) await salir(context, widget.api, mensaje: e.mensaje);
    } on ErrorApi catch (e) {
      setState(() {
        _errores = e.errores;
        _error = e.errores.isEmpty
            ? e.mensaje
            : (e.errores['__all__']?.join(' ') ?? 'Revisa los campos marcados.');
      });
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  Future<DateTime?> _elegirFecha(DateTime? actual) => showDatePicker(
        context: context,
        initialDate: actual ?? DateTime.now(),
        firstDate: DateTime(2000),
        lastDate: DateTime(2100),
      );

  @override
  Widget build(BuildContext context) {
    const sep = SizedBox(height: 14);
    return Scaffold(
      appBar: AppBar(title: Text(_esNuevo ? 'Nuevo cliente' : 'Editar ${f!.username}')),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
          children: [
            if (_error != null) ...[
              Aviso(texto: _error!, icono: Icons.error_outline, color: Colores.peligro, fondo: Colores.peligroSuave),
              sep,
            ],
            Seccion(
              titulo: 'Cuenta',
              icono: Icons.manage_accounts_outlined,
              child: Column(children: [
                TextFormField(
                  controller: _usuario,
                  decoration: InputDecoration(labelText: 'Usuario', errorText: _err('username')),
                  validator: (v) => (v ?? '').trim().isEmpty ? 'Obligatorio' : null,
                ),
                sep,
                TextFormField(
                  controller: _email,
                  keyboardType: TextInputType.emailAddress,
                  decoration: InputDecoration(labelText: 'Email', errorText: _err('email')),
                ),
                sep,
                DropdownButtonFormField<String>(
                  initialValue: _rol,
                  decoration: InputDecoration(labelText: 'Rol', errorText: _err('role')),
                  items: const [
                    DropdownMenuItem(value: 'user', child: Text('Usuario (cliente)')),
                    DropdownMenuItem(value: 'admin', child: Text('Administrador')),
                  ],
                  onChanged: (v) => setState(() => _rol = v ?? _rol),
                ),
                if (_esNuevo) ...[
                  sep,
                  TextFormField(
                    controller: _clave1,
                    obscureText: !_verClave,
                    decoration: InputDecoration(
                      labelText: 'Contraseña',
                      errorText: _err('password1'),
                      helperText: 'Mínimo 8 caracteres, no solo números',
                      suffixIcon: IconButton(
                        icon: Icon(_verClave ? Icons.visibility_off : Icons.visibility),
                        onPressed: () => setState(() => _verClave = !_verClave),
                      ),
                    ),
                    validator: (v) => (v ?? '').length < 8 ? 'Mínimo 8 caracteres' : null,
                  ),
                  sep,
                  TextFormField(
                    controller: _clave2,
                    obscureText: !_verClave,
                    decoration: InputDecoration(labelText: 'Repetir contraseña', errorText: _err('password2')),
                    validator: (v) => v != _clave1.text ? 'Las contraseñas no coinciden' : null,
                  ),
                ] else ...[
                  const SizedBox(height: 6),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Cuenta activa'),
                    subtitle: Text(
                      _err('is_active') ?? (_activo ? 'Puede iniciar sesión' : 'No puede iniciar sesión'),
                      style: TextStyle(color: _err('is_active') != null ? Colores.peligro : null),
                    ),
                    value: _activo,
                    onChanged: (v) => setState(() => _activo = v),
                  ),
                ],
              ]),
            ),
            sep,
            Seccion(
              titulo: 'Sitio y equipo',
              icono: Icons.apartment,
              child: Column(children: [
                TextFormField(controller: _ubicacion, decoration: InputDecoration(labelText: 'Ubicación', errorText: _err('location'))),
                sep,
                Row(children: [
                  Expanded(child: TextFormField(controller: _idExterno, decoration: InputDecoration(labelText: 'ID externo', errorText: _err('external_id')))),
                  const SizedBox(width: 12),
                  Expanded(child: TextFormField(controller: _encargado, decoration: InputDecoration(labelText: 'Encargado', errorText: _err('manager_name')))),
                ]),
                sep,
                TextFormField(
                  controller: _telefono,
                  keyboardType: TextInputType.phone,
                  decoration: InputDecoration(labelText: 'Teléfono', hintText: '+56 9 1234 5678', errorText: _err('phone')),
                ),
                sep,
                TextFormField(controller: _direccion, decoration: InputDecoration(labelText: 'Dirección', errorText: _err('address'))),
                sep,
                TextFormField(
                  controller: _link,
                  keyboardType: TextInputType.url,
                  autocorrect: false,
                  decoration: InputDecoration(
                    labelText: 'Link del equipo (Wecon)',
                    hintText: 'https://…',
                    prefixIcon: const Icon(Icons.link),
                    helperText: 'El cliente lo abre con «Ver mi caldera»',
                    errorText: _err('link'),
                  ),
                  validator: (v) {
                    final t = (v ?? '').trim();
                    if (t.isEmpty) return null;
                    return t.startsWith('http://') || t.startsWith('https://') ? null : 'Debe empezar con http:// o https://';
                  },
                ),
              ]),
            ),
            sep,
            Seccion(
              titulo: 'Mantenciones',
              icono: Icons.build_outlined,
              child: Column(children: [
                Row(children: [
                  Expanded(
                    flex: 3,
                    child: _CampoFecha(
                      etiqueta: 'Última mantención',
                      valor: _ultima,
                      error: _err('last_maintenance'),
                      alElegir: () async {
                        final d = await _elegirFecha(_ultima);
                        if (d != null) setState(() => _ultima = d);
                      },
                      alBorrar: () => setState(() => _ultima = null),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    flex: 2,
                    child: TextFormField(
                      controller: _intervalo,
                      keyboardType: TextInputType.number,
                      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                      decoration: InputDecoration(labelText: 'Cada (meses)', errorText: _err('maintenance_interval_months')),
                      validator: (v) {
                        final n = int.tryParse(v ?? '');
                        return n == null || n < 1 || n > 60 ? 'Entre 1 y 60' : null;
                      },
                    ),
                  ),
                ]),
                sep,
                _CampoFecha(
                  etiqueta: 'Próxima mantención',
                  valor: _proxima,
                  error: _err('next_maintenance'),
                  ayuda: _proximaTocada || _esNuevo
                      ? 'Si la dejas vacía se calcula sola'
                      : 'Se recalcula al cambiar la última, salvo que la edites',
                  alElegir: () async {
                    final d = await _elegirFecha(_proxima);
                    if (d != null) {
                      setState(() {
                        _proxima = d;
                        _proximaTocada = true;
                      });
                    }
                  },
                  alBorrar: () => setState(() {
                    _proxima = null;
                    _proximaTocada = true;
                  }),
                ),
              ]),
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: _guardando ? null : _guardar,
              icon: _guardando
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : Icon(_esNuevo ? Icons.person_add_alt_1 : Icons.save_outlined),
              label: Text(_esNuevo ? 'Crear cliente' : 'Guardar cambios'),
            ),
          ],
        ),
      ),
    );
  }
}

class _CampoFecha extends StatelessWidget {
  const _CampoFecha({
    required this.etiqueta,
    required this.valor,
    required this.alElegir,
    required this.alBorrar,
    this.error,
    this.ayuda,
  });

  final String etiqueta;
  final DateTime? valor;
  final VoidCallback alElegir;
  final VoidCallback alBorrar;
  final String? error;
  final String? ayuda;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: alElegir,
        borderRadius: BorderRadius.circular(10),
        child: InputDecorator(
          isEmpty: valor == null,
          decoration: InputDecoration(
            labelText: etiqueta,
            errorText: error,
            helperText: ayuda,
            helperMaxLines: 2,
            prefixIcon: const Icon(Icons.event_outlined),
            suffixIcon: valor == null
                ? null
                : IconButton(tooltip: 'Quitar', icon: const Icon(Icons.close, size: 18), onPressed: alBorrar),
          ),
          child: Text(valor == null ? '' : fecha(valor)),
        ),
      );
}
