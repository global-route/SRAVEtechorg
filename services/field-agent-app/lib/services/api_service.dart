import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import '../models/building.dart';

const _storage = FlutterSecureStorage();

class ApiService {
  final String baseUrl;
  final http.Client _httpClient;

  ApiService({required this.baseUrl, http.Client? httpClient, String? token})
      : _httpClient = httpClient ?? http.Client(),
        _cachedToken = token;

  String? _cachedToken;

  // ── Static login ──────────────────────────────────────────────────────────

  static Future<Map<String, String>> login({
    required String baseUrl,
    required String clientId,
    required String clientSecret,
    http.Client? httpClient,
  }) async {
    final client = httpClient ?? http.Client();
    final res = await client.post(
      Uri.parse('$baseUrl/auth/token'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'client_id': clientId, 'client_secret': clientSecret}),
    );
    if (res.statusCode != 200) throw Exception('Login failed: ${res.statusCode}');
    final body = jsonDecode(res.body) as Map<String, dynamic>;
    return {
      'access_token':  body['access_token'] as String,
      'refresh_token': body['refresh_token'] as String,
    };
  }

  // ── Token management ──────────────────────────────────────────────────────

  Future<String> _getToken() async {
    if (_cachedToken != null) return _cachedToken!;

    final stored = await _storage.read(key: 'access_token');
    if (stored == null) throw Exception('Not authenticated');

    // Decode without verification to check expiry
    final parts = stored.split('.');
    if (parts.length == 3) {
      final payload = jsonDecode(
        utf8.decode(base64Url.decode(base64Url.normalize(parts[1]))),
      ) as Map<String, dynamic>;
      final exp = payload['exp'] as int?;
      if (exp != null) {
        final expiresAt = DateTime.fromMillisecondsSinceEpoch(exp * 1000, isUtc: true);
        if (expiresAt.difference(DateTime.now().toUtc()).inMinutes < 5) {
          return await _refresh();
        }
      }
    }
    return stored;
  }

  Future<String> _refresh() async {
    final refreshToken = await _storage.read(key: 'refresh_token');
    if (refreshToken == null) throw Exception('No refresh token');

    final storedBase = await _storage.read(key: 'access_token');
    final parts = storedBase?.split('.') ?? [];
    // Extract baseUrl from stored token sub isn't possible — use instance baseUrl
    final res = await _httpClient.post(
      Uri.parse('$baseUrl/auth/refresh'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'refresh_token': refreshToken}),
    );
    if (res.statusCode != 200) throw Exception('Token refresh failed');
    final body = jsonDecode(res.body) as Map<String, dynamic>;
    await _storage.write(key: 'access_token',  value: body['access_token'] as String);
    await _storage.write(key: 'refresh_token', value: body['refresh_token'] as String);
    return body['access_token'] as String;
  }

  Future<Map<String, String>> _authHeaders() async {
    final token = await _getToken();
    return {'Authorization': 'Bearer $token'};
  }

  // ── API calls ─────────────────────────────────────────────────────────────

  Future<List<Building>> getAssignments(String agentId, {String? lgaId, int page = 1}) async {
    final uri = Uri.parse('$baseUrl/field/assignments/$agentId').replace(
      queryParameters: {
        if (lgaId != null) 'lga_id': lgaId,
        'page': '$page',
        'limit': '50',
      },
    );
    final res = await _httpClient.get(uri, headers: await _authHeaders());
    if (res.statusCode != 200) throw Exception('Failed to load assignments');
    final body = jsonDecode(res.body) as Map<String, dynamic>;
    final List data = body['assignments'] as List;
    return data.map((e) => Building.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> verifyBuilding(int buildingId, Map<String, dynamic> payload) async {
    final res = await _httpClient.patch(
      Uri.parse('$baseUrl/field/buildings/$buildingId/verify'),
      headers: {...await _authHeaders(), 'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );
    if (res.statusCode != 200) throw Exception('Verify failed: ${res.statusCode}');
  }
}
