import 'package:flutter/material.dart';
import 'screens/map_screen.dart';

void main() => runApp(const SRAVEApp());

class SRAVEApp extends StatelessWidget {
  const SRAVEApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SRAVE Field Agent',
      theme: ThemeData(colorSchemeSeed: Colors.green, useMaterial3: true),
      home: const MapScreen(),
    );
  }
}
