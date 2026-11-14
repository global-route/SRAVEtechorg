import 'package:flutter/material.dart';
import 'services/auth_service.dart';
import 'screens/login_screen.dart';
import 'screens/map_screen.dart';
import 'services/sync_service.dart';
import 'services/db_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const SRAVEApp());
}

class SRAVEApp extends StatelessWidget {
  const SRAVEApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SRAVE Field Agent',
      theme: ThemeData(colorSchemeSeed: Colors.green, useMaterial3: true),
      home: const _AppEntry(),
    );
  }
}

class _AppEntry extends StatefulWidget {
  const _AppEntry();

  @override
  State<_AppEntry> createState() => _AppEntryState();
}

class _AppEntryState extends State<_AppEntry> {
  static const _baseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: 'https://api.srave.io');
  final _auth = AuthService(baseUrl: _baseUrl);
  bool _checking = true;
  bool _loggedIn = false;

  @override
  void initState() {
    super.initState();
    _check();
  }

  Future<void> _check() async {
    final token = await _auth.getToken();
    if (token != null) {
      await _auth.refreshIfNeeded();
      // Start background sync
      final db = await DbService.instance;
      SyncService(db: db, baseUrl: _baseUrl, token: token).startListening();
    }
    setState(() { _loggedIn = token != null; _checking = false; });
  }

  @override
  Widget build(BuildContext context) {
    if (_checking) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    return _loggedIn ? const MapScreen() : LoginScreen(auth: _auth);
  }
}
