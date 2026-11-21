import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import '../config.dart';

typedef Json = Map<String, dynamic>;

/// Erreur renvoyée par l'API, avec un message lisible pour l'utilisateur.
class ApiException implements Exception {
  ApiException(this.message, {this.status, this.body});

  final String message;
  final int? status;
  final dynamic body;

  bool get isUnavailable => status == 503;
  bool get isForbidden => status == 403;
  bool get isNotFound => status == 404;

  @override
  String toString() => message;
}

/// Client HTTP de l'API TTB : JWT (access + refresh rotatif), erreurs DRF, pagination.
class ApiClient {
  ApiClient({http.Client? httpClient, FlutterSecureStorage? storage})
      : _http = httpClient ?? http.Client(),
        _storage = storage ?? const FlutterSecureStorage();

  static const _kAccess = 'access_token';
  static const _kRefresh = 'refresh_token';
  static const _timeout = Duration(seconds: 90); // les appels IA peuvent prendre du temps

  final http.Client _http;
  final FlutterSecureStorage _storage;

  String? _access;
  String? _refresh;
  Future<bool>? _refreshing;

  /// Appelé quand la session ne peut plus être rafraîchie (déconnexion forcée).
  void Function()? onSessionExpired;

  bool get hasSession => _refresh != null;
  String? get refreshToken => _refresh;

  Future<void> loadTokens() async {
    _access = await _storage.read(key: _kAccess);
    _refresh = await _storage.read(key: _kRefresh);
  }

  Future<void> saveTokens(String access, String refresh) async {
    _access = access;
    _refresh = refresh;
    await _storage.write(key: _kAccess, value: access);
    await _storage.write(key: _kRefresh, value: refresh);
  }

  Future<void> clearTokens() async {
    _access = null;
    _refresh = null;
    await _storage.delete(key: _kAccess);
    await _storage.delete(key: _kRefresh);
  }

  // --- verbes -----------------------------------------------------------
  Future<dynamic> get(String path, {Map<String, String>? query}) =>
      _send('GET', path, query: query);

  Future<dynamic> post(String path, [Object? body]) => _send('POST', path, body: body ?? const {});

  Future<dynamic> patch(String path, Object body) => _send('PATCH', path, body: body);

  Future<dynamic> delete(String path) => _send('DELETE', path);

  /// Liste paginée DRF -> renvoie `results` (ou la liste brute si non paginée).
  Future<List<Json>> list(String path, {Map<String, String>? query}) async {
    final data = await get(path, query: query);
    return _results(data);
  }

  /// Suit tous les liens `next` (ex. communes d'une wilaya, messages d'une conversation).
  Future<List<Json>> listAll(String path, {Map<String, String>? query}) async {
    final out = <Json>[];
    dynamic data = await get(path, query: query);
    out.addAll(_results(data));
    while (data is Map && data['next'] is String) {
      data = await _send('GET', null, absoluteUrl: data['next'] as String);
      out.addAll(_results(data));
    }
    return out;
  }

  /// Envoi multipart (photos).
  Future<dynamic> upload(
    String path, {
    required String fileField,
    required File file,
    Map<String, String> fields = const {},
  }) {
    return _send('POST', path, multipart: (fields: fields, fileField: fileField, file: file));
  }

  List<Json> _results(dynamic data) {
    final raw = data is Map ? (data['results'] ?? const []) : (data ?? const []);
    return (raw as List).cast<Map>().map((e) => e.cast<String, dynamic>()).toList();
  }

  // --- cœur ---------------------------------------------------------------
  Future<dynamic> _send(
    String method,
    String? path, {
    Map<String, String>? query,
    Object? body,
    ({Map<String, String> fields, String fileField, File file})? multipart,
    String? absoluteUrl,
    bool retried = false,
  }) async {
    final uri = absoluteUrl != null
        ? Uri.parse(absoluteUrl)
        : Uri.parse('${ServerConfig.baseUrl}$path').replace(queryParameters: query);

    http.Response resp;
    try {
      resp = await _rawSend(method, uri, body: body, multipart: multipart).timeout(_timeout);
    } on SocketException {
      throw ApiException(_unreachable);
    } on TimeoutException {
      throw ApiException('Le serveur met trop de temps à répondre.');
    } on http.ClientException {
      throw ApiException(_unreachable);
    }

    if (resp.statusCode == 401 && !retried && _refresh != null && !_isAuthPath(uri)) {
      if (await _refreshAccess()) {
        return _send(method, path,
            query: query, body: body, multipart: multipart, absoluteUrl: absoluteUrl, retried: true);
      }
      await clearTokens();
      onSessionExpired?.call();
    }

    final decoded = resp.body.isEmpty ? null : _tryJson(utf8.decode(resp.bodyBytes));
    if (resp.statusCode >= 200 && resp.statusCode < 300) return decoded;
    throw ApiException(_errorMessage(decoded, resp.statusCode), status: resp.statusCode, body: decoded);
  }

  Future<http.Response> _rawSend(
    String method,
    Uri uri, {
    Object? body,
    ({Map<String, String> fields, String fileField, File file})? multipart,
  }) async {
    final headers = <String, String>{
      'Accept': 'application/json',
      if (_access != null) 'Authorization': 'Bearer $_access',
    };
    if (multipart != null) {
      final req = http.MultipartRequest(method, uri)
        ..headers.addAll(headers)
        ..fields.addAll(multipart.fields)
        ..files.add(await http.MultipartFile.fromPath(multipart.fileField, multipart.file.path));
      return http.Response.fromStream(await _http.send(req));
    }
    final req = http.Request(method, uri)..headers.addAll(headers);
    if (body != null && method != 'GET') {
      req.headers['Content-Type'] = 'application/json; charset=utf-8';
      req.body = jsonEncode(body);
    }
    return http.Response.fromStream(await _http.send(req));
  }

  static String get _unreachable =>
      'Serveur injoignable (${ServerConfig.baseUrl}). Vérifiez le Wi-Fi ou l\'adresse du serveur.';

  /// Vérifie qu'un serveur TTB répond à cette adresse (`/api/health/`).
  Future<bool> ping(String baseUrl) async {
    try {
      final resp = await _http
          .get(Uri.parse('$baseUrl/api/health/'), headers: {'Accept': 'application/json'})
          .timeout(const Duration(seconds: 6));
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  bool _isAuthPath(Uri uri) => uri.path.contains('/api/auth/token/refresh/');

  /// Un seul rafraîchissement à la fois, même si plusieurs requêtes reçoivent 401.
  Future<bool> _refreshAccess() {
    return _refreshing ??= () async {
      try {
        final resp = await _http.post(
          Uri.parse('${ServerConfig.baseUrl}/api/auth/token/refresh/'),
          headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
          body: jsonEncode({'refresh': _refresh}),
        );
        if (resp.statusCode != 200) return false;
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        await saveTokens(data['access'] as String, (data['refresh'] as String?) ?? _refresh!);
        return true;
      } catch (_) {
        return false;
      } finally {
        _refreshing = null;
      }
    }();
  }

  static dynamic _tryJson(String text) {
    try {
      return jsonDecode(text);
    } catch (_) {
      return text;
    }
  }

  /// Aplatit les erreurs DRF : {"detail": "..."}, {"champ": ["..."]}, ["..."].
  static String _errorMessage(dynamic body, int status) {
    String flatten(dynamic v) {
      if (v is String) return v;
      if (v is List) return v.map(flatten).where((s) => s.isNotEmpty).join('\n');
      if (v is Map) {
        if (v['detail'] != null) return flatten(v['detail']);
        return v.values.map(flatten).where((s) => s.isNotEmpty).join('\n');
      }
      return '';
    }

    final msg = flatten(body).trim();
    if (msg.isNotEmpty && msg.length < 400 && !msg.startsWith('<')) return msg;
    if (status == 429) return 'Trop de tentatives, réessayez plus tard.';
    if (status >= 500) return 'Erreur du serveur ($status).';
    return 'Erreur ($status).';
  }
}
