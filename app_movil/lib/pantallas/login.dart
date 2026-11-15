import 'package:material_ui/material_ui.dart';

import '../api/cliente_api.dart';
import '../tema.dart';
import 'inicio.dart';

class PantallaLogin extends StatefulWidget {
  const PantallaLogin({super.key, required this.api, this.mensaje});

  final ClienteApi api;

  /// Aviso opcional, por ejemplo "Tu sesión expiró".
  final String? mensaje;

  @override
  State<PantallaLogin> createState() => _PantallaLoginState();
}

class _PantallaLoginState extends State<PantallaLogin> {
  final _form = GlobalKey<FormState>();
  final _usuario = TextEditingController();
  final _clave = TextEditingController();
  late final _servidor = TextEditingController(text: widget.api.servidor);
  bool _cargando = false;
  bool _verClave = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _error = widget.mensaje;
  }

  @override
  void dispose() {
    _usuario.dispose();
    _clave.dispose();
    _servidor.dispose();
    super.dispose();
  }

  Future<void> _entrar() async {
    if (!_form.currentState!.validate()) return;
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      await widget.api.iniciarSesion(_usuario.text.trim(), _clave.text, servidor: _servidor.text);
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => PantallaInicio(api: widget.api)),
      );
    } on ErrorApi catch (e) {
      setState(() => _error = e.mensaje);
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Scaffold(
      backgroundColor: Colores.tinta,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const _Marca(),
                  const SizedBox(height: 28),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(20),
                      child: Form(
                        key: _form,
                        child: AutofillGroup(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              Text('Iniciar sesión', style: t.headlineSmall?.copyWith(fontWeight: FontWeight.w600)),
                              const SizedBox(height: 4),
                              Text('Ingresa con el usuario que te entregó EMATEL.',
                                  style: t.bodyMedium?.copyWith(color: Colores.textoSuave)),
                              const SizedBox(height: 20),
                              if (_error != null) ...[
                                Container(
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: Colores.peligroSuave,
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: Text(_error!, style: const TextStyle(color: Colores.peligro)),
                                ),
                                const SizedBox(height: 16),
                              ],
                              TextFormField(
                                controller: _usuario,
                                decoration: const InputDecoration(labelText: 'Usuario'),
                                autofillHints: const [AutofillHints.username],
                                textInputAction: TextInputAction.next,
                                validator: (v) => (v ?? '').trim().isEmpty ? 'Ingresa tu usuario' : null,
                              ),
                              const SizedBox(height: 14),
                              TextFormField(
                                controller: _clave,
                                obscureText: !_verClave,
                                decoration: InputDecoration(
                                  labelText: 'Contraseña',
                                  suffixIcon: IconButton(
                                    tooltip: _verClave ? 'Ocultar' : 'Mostrar',
                                    icon: Icon(_verClave ? Icons.visibility_off : Icons.visibility),
                                    onPressed: () => setState(() => _verClave = !_verClave),
                                  ),
                                ),
                                autofillHints: const [AutofillHints.password],
                                onFieldSubmitted: (_) => _entrar(),
                                validator: (v) => (v ?? '').isEmpty ? 'Ingresa tu contraseña' : null,
                              ),
                              const SizedBox(height: 20),
                              FilledButton(
                                onPressed: _cargando ? null : _entrar,
                                child: _cargando
                                    ? const SizedBox(
                                        width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                                    : const Text('Entrar'),
                              ),
                              const SizedBox(height: 8),
                              Theme(
                                data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                                child: ExpansionTile(
                                  tilePadding: EdgeInsets.zero,
                                  title: Text('Servidor', style: t.bodySmall?.copyWith(color: Colores.textoSuave)),
                                  children: [
                                    TextFormField(
                                      controller: _servidor,
                                      keyboardType: TextInputType.url,
                                      decoration: const InputDecoration(
                                        labelText: 'Dirección del servidor',
                                        helperText: 'Ej.: http://82.25.79.89 · Emulador Android: http://10.0.2.2:8000',
                                      ),
                                      validator: (v) => (v ?? '').trim().isEmpty ? 'Ingresa la dirección' : null,
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Marca extends StatelessWidget {
  const _Marca();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: 56,
          height: 56,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            gradient: const LinearGradient(
              colors: [Color(0xFF2B86E0), Colores.agua],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
          child: const Icon(Icons.local_fire_department, color: Colors.white, size: 30),
        ),
        const SizedBox(height: 14),
        const Text('EMATEL',
            style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w700, letterSpacing: 2)),
        const SizedBox(height: 2),
        const Text('Monitoreo de calderas', style: TextStyle(color: Color(0xFF8494AD))),
      ],
    );
  }
}
