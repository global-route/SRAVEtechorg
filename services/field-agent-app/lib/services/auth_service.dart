import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

class AuthService {
  final String baseUrl;
  final _storage = const FlutterSecureStorage();

  AuthService({required this.baseUrl});

  Future<String?> getToken() => _storage.read(key: 'jwt');

  Future<bool> login(String clientId, String clientSecret) async {
    final res = await http.post(
      Uri.parse('$baseUrl/api/v1/auth/token'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'client_id': clientId, 'client_secret': clientSecret}),
    );
    if (res.statusCode != 200) return false;
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    await _storage.write(key: 'jwt', value: data['access_token'] as String);
    await _storage.write(
      key: 'jwt_exp',
      value: DateTime.now()
          .add(Duration(seconds: data['expires_in'] as int))
          .toIso8601String(),
    );
    return true;
  }

  Future<void> refreshIfNeeded() async {
    final expStr = await _storage.read(key: 'jwt_exp');
    if (expStr == null) return;
    final exp = DateTime.parse(expStr);
    if (exp.difference(DateTime.now()).inMinutes < 5) {
      final id = await _storage.read(key: 'client_id') ?? '';
      final secret = await _storage.read(key: 'client_secret') ?? '';
      await login(id, secret);
    }
  }

  Future<void> logout() => _storage.deleteAll();
}
