import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';

class DbService {
  static Database? _db;

  static Future<Database> get instance async {
    _db ??= await _init();
    return _db!;
  }

  static Future<Database> _init() async {
    final path = join(await getDatabasesPath(), 'srave_field.db');
    return openDatabase(path, version: 1, onCreate: _onCreate);
  }

  static Future<void> _onCreate(Database db, int version) async {
    await db.execute('''
      CREATE TABLE buildings (
        id            INTEGER PRIMARY KEY,
        lga_id        TEXT,
        lat           REAL,
        lon           REAL,
        property_type TEXT,
        verified      INTEGER DEFAULT 0,
        owner_phone   TEXT,
        owner_language TEXT,
        photo_path    TEXT,
        synced        INTEGER DEFAULT 0
      )
    ''');
    await db.execute('''
      CREATE TABLE sync_conflicts (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        building_id    INTEGER,
        local_payload  TEXT,
        server_response TEXT,
        created_at     TEXT
      )
    ''');
  }

  static Future<List<Map<String, dynamic>>> getPendingSync(Database db) =>
      db.query('buildings', where: 'synced = 0');

  static Future<List<Map<String, dynamic>>> getUnverified(Database db) =>
      db.query('buildings', where: 'verified = 0', orderBy: 'id DESC', limit: 50);
}
