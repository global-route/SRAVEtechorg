import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:srave_field_agent/models/building.dart';
import 'package:srave_field_agent/services/api_service.dart';
import 'package:srave_field_agent/screens/map_screen.dart';

class _FakeApiService extends ApiService {
  final List<Building> buildings;
  final bool shouldThrow;

  _FakeApiService({this.buildings = const [], this.shouldThrow = false})
      : super(baseUrl: '', token: '');

  @override
  Future<List<Building>> getAssignments(String agentId) async {
    if (shouldThrow) throw Exception('offline');
    return buildings;
  }
}

void main() {
  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  testWidgets('shows loading indicator on init', (tester) async {
    final api = _FakeApiService(
      buildings: [
        Building(id: 1, lgaId: 'NGA025012', lat: 6.5244, lon: 3.3792),
      ],
    );

    await tester.pumpWidget(MaterialApp(
      home: MapScreen(apiService: api),
    ));

    // Before async completes — loading state
    expect(find.textContaining('Loading'), findsOneWidget);
  });

  testWidgets('shows assignment count after load', (tester) async {
    final api = _FakeApiService(buildings: [
      Building(id: 1, lgaId: 'NGA025012', lat: 6.5244, lon: 3.3792),
      Building(id: 2, lgaId: 'NGA025012', lat: 6.5300, lon: 3.3800),
    ]);

    await tester.pumpWidget(MaterialApp(home: MapScreen(apiService: api)));
    await tester.pumpAndSettle();

    expect(find.textContaining('2 unverified'), findsOneWidget);
  });

  testWidgets('shows zero count when no assignments', (tester) async {
    final api = _FakeApiService(buildings: []);

    await tester.pumpWidget(MaterialApp(home: MapScreen(apiService: api)));
    await tester.pumpAndSettle();

    expect(find.textContaining('0 unverified'), findsOneWidget);
  });

  testWidgets('falls back to local DB when API throws', (tester) async {
    final api = _FakeApiService(shouldThrow: true);

    await tester.pumpWidget(MaterialApp(home: MapScreen(apiService: api)));
    await tester.pumpAndSettle();

    // Should not crash — shows 0 from empty local DB
    expect(find.textContaining('unverified'), findsOneWidget);
  });
}
