import 'dart:convert';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:http/http.dart' as http;
import 'package:sqflite/sqflite.dart';

class SyncService {
  final Database db;
  final String baseUrl;
  final String token;
  final http.Client _httpClient;

  SyncService({
    required this.db,
    required this.baseUrl,
    required this.token,
    http.Client? httpClient,
  }) : _httpClient = httpClient ?? http.Client();

  void startListening() {
    Connectivity().onConnectivityChanged.listen((result) {
      if (result != ConnectivityResult.none) syncNow();
    });
  }

  Future<void> syncNow() async {
    final rows = await db.query('buildings', where: 'synced = 0');
    for (final row in rows) {
      try {
        final res = await _httpClient.patch(
          Uri.parse('$baseUrl/field/buildings/${row['id']}/verify'),
          headers: {
            'Authorization': 'Bearer $token',
            'Content-Type': 'application/json',
          },
          body: jsonEncode({
            'verified': row['verified'] == 1,
            'owner_phone': row['owner_phone'],
            'photo_url': row['photo_path'],
            'property_type': row['property_type'],
            'owner_language': row['owner_language'],
          }),
        );

        if (res.statusCode == 200) {
          await db.update('buildings', {'synced': 1}, where: 'id = ?', whereArgs: [row['id']]);
        } else if (res.statusCode == 409) {
          await db.insert('sync_conflicts', {
            'building_id': row['id'],
            'local_payload': jsonEncode(row),
            'server_response': res.body,
            'created_at': DateTime.now().toIso8601String(),
          });
          await db.update('buildings', {'synced': 2}, where: 'id = ?', whereArgs: [row['id']]);
        }
      } catch (_) {
        // Leave synced=0, retry on next reconnection
      }
    }
  }
}
