import 'dart:io';
import 'package:flutter/material.dart';
import 'package:mapbox_gl/mapbox_gl.dart';
import 'package:camera/camera.dart';
import 'package:geolocator/geolocator.dart';
import 'package:sqflite/sqflite.dart';
import '../models/building.dart';
import '../services/api_service.dart';
import '../services/db_service.dart';
import '../services/classifier_service.dart';
import '../services/sync_service.dart';

const _mapboxToken = String.fromEnvironment('MAPBOX_TOKEN');
const _apiBase = String.fromEnvironment('API_BASE', defaultValue: 'https://api.srave.io/api/v1');
const _agentToken = String.fromEnvironment('AGENT_TOKEN');
const _agentId = String.fromEnvironment('AGENT_ID', defaultValue: 'agent_001');

class MapScreen extends StatefulWidget {
  const MapScreen({super.key});

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  MapboxMapController? _mapController;
  late Database _db;
  final _classifier = ClassifierService();
  final _api = ApiService(baseUrl: _apiBase, token: _agentToken);
  List<Building> _buildings = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    _db = await DbService.instance;
    await _classifier.load();
    await _loadAssignments();
    SyncService(db: _db, baseUrl: _apiBase, token: _agentToken).startListening();
  }

  Future<void> _loadAssignments() async {
    try {
      final remote = await _api.getAssignments(_agentId);
      for (final b in remote) {
        await _db.insert(
          'buildings',
          {'id': b.id, 'lga_id': b.lgaId, 'lat': b.lat, 'lon': b.lon, 'verified': 0, 'synced': 1},
          conflictAlgorithm: ConflictAlgorithm.ignore,
        );
      }
    } catch (_) {
      // offline — fall through to local
    }

    final rows = await DbService.getUnverified(_db);
    setState(() {
      _buildings = rows
          .map((r) => Building(
                id: r['id'] as int,
                lgaId: r['lga_id'] as String,
                lat: r['lat'] as double,
                lon: r['lon'] as double,
                verified: (r['verified'] as int) == 1,
              ))
          .toList();
      _loading = false;
    });
  }

  void _onMapCreated(MapboxMapController controller) {
    _mapController = controller;
    _addMarkers();
  }

  Future<void> _addMarkers() async {
    for (final b in _buildings) {
      await _mapController?.addSymbol(SymbolOptions(
        geometry: LatLng(b.lat, b.lon),
        iconImage: 'marker-15',
        iconColor: '#E53935',
        textField: '${b.id}',
        textOffset: const Offset(0, 1.5),
        textSize: 10,
      ));
    }
    _mapController?.onSymbolTapped.add(_onMarkerTapped);
  }

  void _onMarkerTapped(Symbol symbol) {
    final idx = _buildings.indexWhere(
      (b) => b.lat == symbol.options.geometry!.latitude &&
             b.lon == symbol.options.geometry!.longitude,
    );
    if (idx != -1) _showVerifySheet(_buildings[idx]);
  }

  Future<void> _showVerifySheet(Building building) async {
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => _VerifySheet(
        building: building,
        db: _db,
        classifier: _classifier,
        onVerified: () {
          setState(() => _buildings.removeWhere((b) => b.id == building.id));
          _mapController?.clearSymbols();
          _addMarkers();
        },
      ),
    );
  }

  Future<void> _centerOnUser() async {
    final perm = await Geolocator.requestPermission();
    if (perm == LocationPermission.denied || perm == LocationPermission.deniedForever) return;
    final pos = await Geolocator.getCurrentPosition();
    _mapController?.animateCamera(
      CameraUpdate.newLatLngZoom(LatLng(pos.latitude, pos.longitude), 15),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_loading ? 'Loading…' : '${_buildings.length} unverified'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadAssignments),
        ],
      ),
      body: MapboxMap(
        accessToken: _mapboxToken,
        initialCameraPosition: const CameraPosition(
          target: LatLng(6.5244, 3.3792), // Lagos default
          zoom: 12,
        ),
        onMapCreated: _onMapCreated,
        myLocationEnabled: true,
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _centerOnUser,
        child: const Icon(Icons.my_location),
      ),
    );
  }
}

// ---------------------------------------------------------------------------

class _VerifySheet extends StatefulWidget {
  final Building building;
  final Database db;
  final ClassifierService classifier;
  final VoidCallback onVerified;

  const _VerifySheet({
    required this.building,
    required this.db,
    required this.classifier,
    required this.onVerified,
  });

  @override
  State<_VerifySheet> createState() => _VerifySheetState();
}

class _VerifySheetState extends State<_VerifySheet> {
  final _phoneCtrl = TextEditingController();
  String _propertyType = 'residential_low';
  String _language = 'yoruba';
  File? _photo;
  String? _classifiedType;
  double? _classifiedConf;
  bool _saving = false;

  Future<void> _capturePhoto() async {
    final cameras = await availableCameras();
    if (cameras.isEmpty || !mounted) return;

    final controller = CameraController(cameras.first, ResolutionPreset.medium);
    await controller.initialize();

    if (!mounted) return;
    final path = await Navigator.push<String>(
      context,
      MaterialPageRoute(
        builder: (_) => _CameraView(controller: controller),
      ),
    );
    await controller.dispose();

    if (path != null) {
      final file = File(path);
      final result = await widget.classifier.classify(file);
      setState(() {
        _photo = file;
        _classifiedType = result.label;
        _classifiedConf = result.confidence;
        _propertyType = result.label;
      });
    }
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    await widget.db.update(
      'buildings',
      {
        'verified': 1,
        'owner_phone': _phoneCtrl.text.trim(),
        'owner_language': _language,
        'property_type': _propertyType,
        'photo_path': _photo?.path,
        'synced': 0,
      },
      where: 'id = ?',
      whereArgs: [widget.building.id],
    );
    if (mounted) {
      Navigator.pop(context);
      widget.onVerified();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 16, right: 16, top: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Building #${widget.building.id}',
              style: Theme.of(context).textTheme.titleMedium),
          Text(widget.building.lgaId,
              style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 12),
          Row(
            children: [
              ElevatedButton.icon(
                onPressed: _capturePhoto,
                icon: const Icon(Icons.camera_alt),
                label: const Text('Capture'),
              ),
              if (_classifiedType != null) ...[
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    '$_classifiedType (${(_classifiedConf! * 100).toStringAsFixed(0)}%)',
                    style: const TextStyle(fontSize: 12),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            value: _propertyType,
            decoration: const InputDecoration(labelText: 'Property type'),
            items: ['residential_low', 'residential_high', 'commercial', 'industrial']
                .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                .toList(),
            onChanged: (v) => setState(() => _propertyType = v!),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _phoneCtrl,
            decoration: const InputDecoration(labelText: 'Owner phone'),
            keyboardType: TextInputType.phone,
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            value: _language,
            decoration: const InputDecoration(labelText: 'Owner language'),
            items: ['yoruba', 'igbo', 'hausa', 'urhobo', 'pidgin']
                .map((l) => DropdownMenuItem(value: l, child: Text(l)))
                .toList(),
            onChanged: (v) => setState(() => _language = v!),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _saving ? null : _save,
              child: _saving
                  ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Mark Verified'),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------

class _CameraView extends StatelessWidget {
  final CameraController controller;
  const _CameraView({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        fit: StackFit.expand,
        children: [
          CameraPreview(controller),
          Positioned(
            bottom: 32,
            left: 0, right: 0,
            child: Center(
              child: FloatingActionButton(
                onPressed: () async {
                  final file = await controller.takePicture();
                  if (context.mounted) Navigator.pop(context, file.path);
                },
                child: const Icon(Icons.camera),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
