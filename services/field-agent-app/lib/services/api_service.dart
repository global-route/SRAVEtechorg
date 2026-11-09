import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/building.dart';

class ApiService {
  final String baseUrl;
  final String token;

  const ApiService({required this.baseUrl, required this.token});

  Future<List<Building>> getAssignments(String agentId) async {
    final res = await http.get(
      Uri.parse('$baseUrl/field/assignments/$agentId'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (res.statusCode != 200) throw Exception('Failed to load assignments');
    final List data = jsonDecode(res.body) as List;
    return data.map((e) => Building.fromJson(e as Map<String, dynamic>)).toList();
  }
}
