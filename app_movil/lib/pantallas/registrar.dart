import 'package:flutter/services.dart';
import 'package:material_ui/material_ui.dart';

import '../api/cliente_api.dart';
import '../formato.dart';
import '../tema.dart';
import '../widgets/tarjetas.dart';
import 'inicio.dart';

/// Abre el formulario de registro de consumo. Devuelve true si se guardó.
Future<bool?> mostrarRegistro(
  BuildContext context, {
  required ClienteApi api,
  int? usuarioId,
  bool conCosto = false,
}) {
  return showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    backgroundColor: Colores.superficie,
    builder: (_) => Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: _FormularioRegistro(api: api, usuarioId: usuarioId, conCosto: conCosto),
    ),
  );
}

class _FormularioRegistro extends StatefulWidget {
  const _FormularioRegistro({required this.api, this.usuarioId, required this.conCosto});

  final ClienteApi api;
  final int? usuarioId;
  final bool conCosto;

  @override
  State<_FormularioRegistro> createState() => _FormularioRegistroState();
}

class _FormularioRegistroState extends State<_FormularioRegistro> {
  final _form = GlobalKey<FormState>();
  final _hoy = DateTime.now();
  late String _mes = meses[_hoy.month - 1].$1;
  late final _anio = TextEditingController(text: '${_hoy.year}');
  final _agua = TextEditingController();
  final _gas = TextEditingController();
  final _costo = TextEditingController();
  final _dia = TextEditingController();
  bool _guardando = false;
  String? _error;
  Map<String, List<String>> _erroresCampo = {};

  @override
  void dispose() {
    for (final c in [_anio, _agua, _gas, _costo, _dia]) {
      c.dispose();
    }
    super.dispose();
  }

  String? _errorDe(String campo) => _erroresCampo[campo]?.join(' ');

  String? _validarNumero(String? v) {
    if ((v ?? '').trim().isEmpty) return null;
    final n = leerNumero(v!);
    if (n == null) return 'Número inválido';
    if (n < 0) return 'No puede ser negativo';
    return null;
  }

  Future<void> _guardar() async {
    setState(() {
      _error = null;
      _erroresCampo = {};
    });
    if (!_form.currentState!.validate()) return;

    final agua = leerNumero(_agua.text);
    final gas = leerNumero(_gas.text);
    if (agua == null && gas == null) {
      setState(() => _error = 'Ingresa al menos el consumo de agua o el de gas.');
      return;
    }

    setState(() => _guardando = true);
    try {
      await widget.api.registrarConsumo(
        anio: int.parse(_anio.text),
        mes: _mes,
        agua: agua,
        gas: gas,
        costo: widget.conCosto ? leerNumero(_costo.text) : null,
        dia: int.tryParse(_dia.text),
        usuarioId: widget.usuarioId,
      );
      if (mounted) Navigator.of(context).pop(true);
    } on SesionExpirada catch (e) {
      if (mounted) await salir(context, widget.api, mensaje: e.mensaje);
    } on ErrorApi catch (e) {
      setState(() {
        _erroresCampo = e.errores;
        _error = e.errores.isEmpty ? e.mensaje : null;
      });
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    const decimales = TextInputType.numberWithOptions(decimal: true);
    final soloNumeros = [FilteringTextInputFormatter.allow(RegExp(r'[0-9.,]'))];

    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
        child: Form(
          key: _form,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('Registrar consumo', style: t.titleLarge?.copyWith(fontWeight: FontWeight.w600)),
              const SizedBox(height: 4),
              Text('Si el mes ya existe, solo cambian los campos que completes.',
                  style: t.bodySmall?.copyWith(color: Colores.textoSuave)),
              const SizedBox(height: 18),
              if (_error != null) ...[
                Aviso(texto: _error!, icono: Icons.error_outline, color: Colores.peligro, fondo: Colores.peligroSuave),
                const SizedBox(height: 14),
              ],
              Row(
                children: [
                  Expanded(
                    flex: 3,
                    child: DropdownButtonFormField<String>(
                      initialValue: _mes,
                      decoration: InputDecoration(labelText: 'Mes', errorText: _errorDe('month')),
                      items: [for (final (codigo, nombre) in meses) DropdownMenuItem(value: codigo, child: Text(nombre))],
                      onChanged: (v) => setState(() => _mes = v ?? _mes),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    flex: 2,
                    child: TextFormField(
                      controller: _anio,
                      keyboardType: TextInputType.number,
                      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                      decoration: InputDecoration(labelText: 'Año', errorText: _errorDe('year')),
                      validator: (v) {
                        final a = int.tryParse(v ?? '');
                        return a == null || a < 2000 || a > 2100 ? 'Año inválido' : null;
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _agua,
                      keyboardType: decimales,
                      inputFormatters: soloNumeros,
                      decoration: InputDecoration(
                        labelText: 'Agua (m³)',
                        prefixIcon: const Icon(Icons.water_drop_outlined, color: Colores.agua),
                        errorText: _errorDe('m3_water'),
                      ),
                      validator: _validarNumero,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      controller: _gas,
                      keyboardType: decimales,
                      inputFormatters: soloNumeros,
                      decoration: InputDecoration(
                        labelText: 'Gas (m³)',
                        prefixIcon: const Icon(Icons.local_fire_department_outlined, color: Colores.gas),
                        errorText: _errorDe('m3_gas'),
                      ),
                      validator: _validarNumero,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  if (widget.conCosto) ...[
                    Expanded(
                      flex: 3,
                      child: TextFormField(
                        controller: _costo,
                        keyboardType: TextInputType.number,
                        inputFormatters: soloNumeros,
                        decoration: InputDecoration(labelText: 'Costo (CLP)', prefixText: '\$ ', errorText: _errorDe('cost')),
                        validator: _validarNumero,
                      ),
                    ),
                    const SizedBox(width: 12),
                  ],
                  Expanded(
                    flex: 2,
                    child: TextFormField(
                      controller: _dia,
                      keyboardType: TextInputType.number,
                      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                      decoration: InputDecoration(labelText: 'Día', hintText: 'Opcional', errorText: _errorDe('day')),
                      validator: (v) {
                        if ((v ?? '').isEmpty) return null;
                        final d = int.tryParse(v!);
                        return d == null || d < 1 || d > 31 ? 'Entre 1 y 31' : null;
                      },
                    ),
                  ),
                  if (!widget.conCosto) const Spacer(flex: 3),
                ],
              ),
              const SizedBox(height: 22),
              FilledButton.icon(
                onPressed: _guardando ? null : _guardar,
                icon: _guardando
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.save_outlined),
                label: const Text('Guardar'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
