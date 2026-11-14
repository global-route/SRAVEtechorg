import 'dart:io';
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import '../models/building.dart';
import '../repository/building_repository.dart';
import 'assignment_list_screen.dart';

class MapScreen extends StatefulWidget {
  const MapScreen({super.key});

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  final _repo = BuildingRepository();
  int _pendingSync = 0;

  @override
  void initState() {
    super.initState();
    _refreshBadge();
  }

  Future<void> _refreshBadge() async {
    final count = await _repo.pendingSyncCount();
    setState(() => _pendingSync = count);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('SRAVE Field Map'),
        actions: [
          if (_pendingSync > 0)
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: Chip(
                label: Text('$_pendingSync pending'),
                backgroundColor: Colors.orange,
                labelStyle: const TextStyle(color: Colors.white),
              ),
            ),
        ],
      ),
      // TODO: replace with MapboxMap widget once Mapbox token configured
      body: const Center(child: Text('Map — Mapbox GL initialising...')),
      floatingActionButton: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          FloatingActionButton(
            heroTag: 'list',
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const AssignmentListScreen()),
            ).then((_) => _refreshBadge()),
            child: const Icon(Icons.list),
          ),
          const SizedBox(height: 8),
          FloatingActionButton(
            heroTag: 'locate',
            onPressed: () async {
              await Geolocator.requestPermission();
              await _refreshBadge();
            },
            child: const Icon(Icons.my_location),
          ),
        ],
      ),
    );
  }
}
