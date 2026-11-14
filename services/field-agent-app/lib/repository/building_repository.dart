import 'package:sqflite/sqflite.dart';
import '../models/building.dart';
import '../services/db_service.dart';

class BuildingRepository {
  Future<List<Building>> getUnverified() async {
    final db = await DbService.instance;
    final rows = await DbService.getUnverified(db);
    return rows.map(Building.fromMap).toList();
  }

  Future<void> upsert(Building b) async {
    final db = await DbService.instance;
    await db.insert('buildings', b.toMap(), conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<void> markVerified({
    required int id,
    required String phone,
    String? photoPath,
    String? propType,
    String? lang,
  }) async {
    final db = await DbService.instance;
    await db.update(
      'buildings',
      {
        'verified': 1,
        'owner_phone': phone,
        'photo_path': photoPath,
        'property_type': propType,
        'owner_language': lang,
        'synced': 0,
      },
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<int> pendingSyncCount() async {
    final db = await DbService.instance;
    final r = await db.rawQuery('SELECT COUNT(*) AS cnt FROM buildings WHERE synced = 0');
    return r.first['cnt'] as int;
  }
}
