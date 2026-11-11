import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'screens/login_screen.dart';
import 'screens/map_screen.dart';

void main() => runApp(const SRAVEApp());

class SRAVEApp extends StatelessWidget {
  const SRAVEApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SRAVE Field Agent',
      theme: ThemeData(colorSchemeSeed: Colors.green, useMaterial3: true),
      home: const _AuthGate(),
    );
  }
}

class _AuthGate extends StatefulWidget {
  const _AuthGate();

  @override
  State<_AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<_AuthGate> {
  static const _storage = FlutterSecureStorage();
  bool _checking = true;
  bool _authenticated = false;

  @override
  void initState() {
    super.initState();
    _check();
  }

  Future<void> _check() async {
    final token = await _storage.read(key: 'access_token');
    setState(() {
      _authenticated = token != null;
      _checking = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_checking) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return _authenticated ? const MapScreen() : const LoginScreen();
  }
}
