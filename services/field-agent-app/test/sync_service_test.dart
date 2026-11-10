import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:srave_field_agent/services/sync_service.dart';

void main() {
  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  Future<Database> _makeDb(List<Map<String, dynamic>> rows) async {
    final db = await databaseFactoryFfi.openDatabase(
      inMemoryDatabasePath,
      options: OpenDatabaseOptions(
        version: 1,
        onCreate: (db, _) async {
          await db.execute('''
            CREATE TABLE buildings (
              id INTEGER PRIMARY KEY, lga_id TEXT, lat REAL, lon REAL,
              property_type TEXT, verified INTEGER DEFAULT 0,
              owner_phone TEXT, owner_language TEXT, photo_path TEXT, synced INTEGER DEFAULT 0
            )
          ''');
          await db.execute('''
            CREATE TABLE sync_conflicts (
              id INTEGER PRIMARY KEY AUTOINCREMENT, building_id INTEGER,
              local_payload TEXT, server_response TEXT, created_at TEXT
            )
          ''');
        },
      ),
    );
    for (final row in rows) {
      await db.insert('buildings', row);
    }
    return db;
  }

  test('syncs pending row — sets synced=1 on HTTP 200', () async {
    final db = await _makeDb([
      {'id': 1, 'lga_id': 'NGA025012', 'lat': 6.5, 'lon': 3.4, 'verified': 1, 'owner_phone': '2348012345678', 'synced': 0},
    ]);

    final mockClient = MockClient((_) async => http.Response('{}', 200));

    final service = SyncService(
      db: db,
      baseUrl: 'https://api.srave.io/api/v1',
      token: 'test_token',
      httpClient: mockClient,
    );
    await service.syncNow();

    final rows = await db.query('buildings', where: 'id = 1');
    expect(rows.first['synced'], 1);
    await db.close();
  });

  test('logs conflict and sets synced=2 on HTTP 409', () async {
    final db = await _makeDb([
      {'id': 2, 'lga_id': 'NGA025012', 'lat': 6.5, 'lon': 3.4, 'verified': 1, 'owner_phone': '2348099999999', 'synced': 0},
    ]);

    final mockClient = MockClient((_) async => http.Response('{"detail":"conflict"}', 409));

    final service = SyncService(
      db: db,
      baseUrl: 'https://api.srave.io/api/v1',
      token: 'test_token',
      httpClient: mockClient,
    );
    await service.syncNow();

    final rows = await db.query('buildings', where: 'id = 2');
    expect(rows.first['synced'], 2);

    final conflicts = await db.query('sync_conflicts', where: 'building_id = 2');
    expect(conflicts.length, 1);
    expect(jsonDecode(conflicts.first['server_response'] as String)['detail'], 'conflict');
    await db.close();
  });

  test('leaves synced=0 on network error', () async {
    final db = await _makeDb([
      {'id': 3, 'lga_id': 'NGA025012', 'lat': 6.5, 'lon': 3.4, 'verified': 1, 'owner_phone': '2348011111111', 'synced': 0},
    ]);

    final mockClient = MockClient((_) async => throw Exception('network error'));

    final service = SyncService(
      db: db,
      baseUrl: 'https://api.srave.io/api/v1',
      token: 'test_token',
      httpClient: mockClient,
    );
    await service.syncNow();

    final rows = await db.query('buildings', where: 'id = 3');
    expect(rows.first['synced'], 0);
    await db.close();
  });

  test('skips already-synced rows', () async {
    int callCount = 0;
    final db = await _makeDb([
      {'id': 4, 'lga_id': 'NGA025012', 'lat': 6.5, 'lon': 3.4, 'verified': 1, 'owner_phone': '2348022222222', 'synced': 1},
    ]);

    final mockClient = MockClient((_) async { callCount++; return http.Response('{}', 200); });

    final service = SyncService(db: db, baseUrl: 'https://api.srave.io/api/v1', token: 'test_token', httpClient: mockClient);
    await service.syncNow();

    expect(callCount, 0);
    await db.close();
  });
}
