import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/building.dart';

class ApiService {
  final String baseUrl;
  final String token;

  const ApiService({required this.baseUrl, required this.token});

  Future<List<Building>> getAssignments(String agentId, {String? lgaId, int page = 1}) async {
    final uri = Uri.parse('$baseUrl/field/assignments/$agentId').replace(
      queryParameters: {
        if (lgaId != null) 'lga_id': lgaId,
        'page': '$page',
        'limit': '50',
      },
    );
    final res = await http.get(uri, headers: {'Authorization': 'Bearer $token'});
    if (res.statusCode != 200) throw Exception('Failed to load assignments');
    final body = jsonDecode(res.body) as Map<String, dynamic>;
    final List data = body['assignments'] as List;
    return data.map((e) => Building.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> verifyBuilding(int buildingId, Map<String, dynamic> payload) async {
    final res = await http.patch(
      Uri.parse('$baseUrl/field/buildings/$buildingId/verify'),
      headers: {'Authorization': 'Bearer $token', 'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );
    if (res.statusCode != 200) throw Exception('Verify failed: ${res.statusCode}');
  }
}
