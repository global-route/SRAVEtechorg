import 'dart:io';
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import '../models/building.dart';
import '../repository/building_repository.dart';
import '../services/classifier_service.dart';

const _propertyLabels = {
  'residential_low': 'Residential (Low)',
  'residential_high': 'Residential (High)',
  'commercial': 'Commercial',
  'industrial': 'Industrial',
};

const _languages = ['yoruba', 'igbo', 'hausa', 'urhobo', 'pidgin', 'english'];

class BuildingDetailScreen extends StatefulWidget {
  final Building building;
  const BuildingDetailScreen({super.key, required this.building});

  @override
  State<BuildingDetailScreen> createState() => _BuildingDetailScreenState();
}

class _BuildingDetailScreenState extends State<BuildingDetailScreen> {
  final _repo = BuildingRepository();
  final _classifier = ClassifierService();
  final _phoneCtrl = TextEditingController();
  String? _propType;
  double? _confidence;
  String? _photoPath;
  String _language = 'yoruba';
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _propType = widget.building.propertyType;
    _classifier.load();
  }

  bool _validPhone(String v) => RegExp(r'^\+234\d{10}$').hasMatch(v);

  Future<void> _capturePhoto() async {
    final cameras = await availableCameras();
    if (cameras.isEmpty || !mounted) return;
    final ctrl = CameraController(cameras.first, ResolutionPreset.medium);
    await ctrl.initialize();
    final xfile = await ctrl.takePicture();
    await ctrl.dispose();

    final file = File(xfile.path);
    final result = await _classifier.classify(file);
    setState(() {
      _photoPath = xfile.path;
      _propType = result.label;
      _confidence = result.confidence;
    });
  }

  Future<void> _save() async {
    if (!_validPhone(_phoneCtrl.text)) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Enter a valid +234XXXXXXXXXX number')));
      return;
    }
    setState(() => _saving = true);
    await _repo.markVerified(
      id: widget.building.id,
      phone: _phoneCtrl.text.trim(),
      photoPath: _photoPath,
      propType: _propType,
      lang: _language,
    );
    if (mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Building #${widget.building.id}')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('LGA: ${widget.building.lgaId}'),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              value: _propType,
              decoration: const InputDecoration(labelText: 'Property Type'),
              items: _propertyLabels.entries
                  .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                  .toList(),
              onChanged: (v) => setState(() => _propType = v),
            ),
            if (_confidence != null)
              Text(
                _confidence! < 0.6
                    ? 'Uncertain (${(_confidence! * 100).toStringAsFixed(0)}%) — please confirm'
                    : 'Confidence: ${(_confidence! * 100).toStringAsFixed(0)}%',
                style: TextStyle(color: _confidence! < 0.6 ? Colors.orange : Colors.green),
              ),
            const SizedBox(height: 12),
            ElevatedButton.icon(
              onPressed: _capturePhoto,
              icon: const Icon(Icons.camera_alt),
              label: Text(_photoPath == null ? 'Capture Photo' : 'Retake Photo'),
            ),
            if (_photoPath != null) ...[
              const SizedBox(height: 8),
              Image.file(File(_photoPath!), height: 150, fit: BoxFit.cover),
            ],
            const SizedBox(height: 12),
            TextField(
              controller: _phoneCtrl,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(
                  labelText: 'Owner Phone', hintText: '+234XXXXXXXXXX'),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: _language,
              decoration: const InputDecoration(labelText: 'Owner Language'),
              items: _languages
                  .map((l) => DropdownMenuItem(value: l, child: Text(l)))
                  .toList(),
              onChanged: (v) => setState(() => _language = v ?? 'yoruba'),
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _saving ? null : _save,
                child: _saving
                    ? const CircularProgressIndicator()
                    : const Text('Mark Verified'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
