import 'package:flutter/material.dart';

class MapScreen extends StatelessWidget {
  const MapScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Field Assignments')),
      // TODO: integrate Mapbox GL JS map widget
      body: const Center(child: Text('Map loading...')),
    );
  }
}
