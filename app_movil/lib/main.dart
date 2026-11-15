import 'package:intl/date_symbol_data_local.dart';
import 'package:material_ui/material_ui.dart';

import 'api/cliente_api.dart';
import 'pantallas/inicio.dart';
import 'pantallas/login.dart';
import 'tema.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting('es_CL');

  final api = ClienteApi();
  final conSesion = await api.cargar();
  runApp(EmatelApp(api: api, conSesion: conSesion));
}

class EmatelApp extends StatelessWidget {
  const EmatelApp({super.key, required this.api, required this.conSesion});

  final ClienteApi api;
  final bool conSesion;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'EMATEL',
      debugShowCheckedModeBanner: false,
      theme: construirTema(),
      home: conSesion ? PantallaInicio(api: api) : PantallaLogin(api: api),
    );
  }
}
