import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';
import '../models/building.dart';
import '../repository/building_repository.dart';
import 'building_detail_screen.dart';

class AssignmentListScreen extends StatefulWidget {
  const AssignmentListScreen({super.key});

  @override
  State<AssignmentListScreen> createState() => _AssignmentListScreenState();
}

class _AssignmentListScreenState extends State<AssignmentListScreen> {
  final _repo = BuildingRepository();
  List<Building> _buildings = [];
  bool _offline = false;

  @override
  void initState() {
    super.initState();
    _load();
    Connectivity().onConnectivityChanged.listen((r) {
      setState(() => _offline = r == ConnectivityResult.none);
    });
  }

  Future<void> _load() async {
    final list = await _repo.getUnverified();
    setState(() => _buildings = list);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Assignments')),
      body: Column(
        children: [
          if (_offline)
            Container(
              color: Colors.orange,
              width: double.infinity,
              padding: const EdgeInsets.all(8),
              child: const Text('Offline — showing cached assignments',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.white)),
            ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _load,
              child: ListView.builder(
                itemCount: _buildings.length,
                itemBuilder: (_, i) {
                  final b = _buildings[i];
                  return ListTile(
                    leading: Icon(Icons.home,
                        color: b.verified ? Colors.green : Colors.red),
                    title: Text('Building #${b.id} — ${b.lgaId}'),
                    subtitle: Text(b.propertyType),
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                          builder: (_) => BuildingDetailScreen(building: b)),
                    ).then((_) => _load()),
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}
