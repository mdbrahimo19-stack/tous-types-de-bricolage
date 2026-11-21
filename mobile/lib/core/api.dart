import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'config.dart';

typedef Json = Map<String, dynamic>;

/// Erreur API lisible par l'utilisateur.
class ApiException implements Exception {
  ApiException(this.message, [this.statusCode]);
  final String message;
  final int? statusCode;
  @override
  String toString() => message;
}

/// Client HTTP unique : ajoute le JWT, le rafraîchit à l'expiration,
/// et transforme les erreurs DRF en message lisible.
class Api {
  Api._() {
    _dio = Dio(BaseOptions(
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 30),
    ));
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) {
        options.baseUrl = AppConfig.apiUrl;
        final token = _access;
        if (token != null && options.extra['noAuth'] != true) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (e, handler) async {
        final opts = e.requestOptions;
        if (e.response?.statusCode == 401 &&
            _refresh != null &&
            opts.extra['retried'] != true &&
            opts.extra['noAuth'] != true) {
          if (await _refreshToken()) {
            opts.extra['retried'] = true;
            opts.headers['Authorization'] = 'Bearer $_access';
            try {
              final r = await _dio.fetch(opts);
              return handler.resolve(r);
            } on DioException catch (e2) {
              return handler.next(e2);
            }
          } else {
            await clearTokens();
            onSessionExpired?.call();
          }
        }
        handler.next(e);
      },
    ));
  }

  static final Api instance = Api._();

  late final Dio _dio;
  final _storage = const FlutterSecureStorage();
  String? _access;
  String? _refresh;

  /// Appelé quand la session ne peut plus être renouvelée.
  void Function()? onSessionExpired;

  bool get hasSession => _refresh != null;

  Future<void> loadTokens() async {
    _access = await _storage.read(key: 'access');
    _refresh = await _storage.read(key: 'refresh');
  }

  Future<void> saveTokens(String access, String refresh) async {
    _access = access;
    _refresh = refresh;
    await _storage.write(key: 'access', value: access);
    await _storage.write(key: 'refresh', value: refresh);
  }

  Future<void> clearTokens() async {
    _access = null;
    _refresh = null;
    await _storage.delete(key: 'access');
    await _storage.delete(key: 'refresh');
  }

  String? get refreshToken => _refresh;

  Future<bool> _refreshToken() async {
    try {
      final r = await Dio().post(
        '${AppConfig.apiUrl}/auth/token/refresh/',
        data: {'refresh': _refresh},
      );
      final data = r.data as Map;
      final access = data['access'] as String;
      final refresh = (data['refresh'] as String?) ?? _refresh!;
      await saveTokens(access, refresh);
      return true;
    } catch (_) {
      return false;
    }
  }

  // ------------------------------------------------------------------
  Future<dynamic> get(String path, {Map<String, dynamic>? query, bool auth = true}) =>
      _wrap(() => _dio.get(path, queryParameters: query, options: _opts(auth)));

  Future<dynamic> post(String path, {Object? data, bool auth = true}) =>
      _wrap(() => _dio.post(path, data: data, options: _opts(auth)));

  Future<dynamic> patch(String path, {Object? data}) =>
      _wrap(() => _dio.patch(path, data: data));

  Future<dynamic> delete(String path) => _wrap(() => _dio.delete(path));

  /// Envoie un fichier en multipart (`field` = nom du champ côté Django).
  Future<dynamic> upload(String path, String field, String filePath,
      {Map<String, dynamic>? fields}) async {
    final form = FormData.fromMap({
      ...?fields,
      field: await MultipartFile.fromFile(filePath, filename: filePath.split('/').last),
    });
    return _wrap(() => _dio.post(path, data: form));
  }

  /// Récupère toutes les pages d'une liste paginée DRF (`{results, next}`).
  Future<List<Json>> getAll(String path,
      {Map<String, dynamic>? query, bool auth = true, int maxPages = 20}) async {
    final out = <Json>[];
    var page = 1;
    while (page <= maxPages) {
      final data = await get(path, query: {...?query, 'page': page}, auth: auth);
      if (data is List) {
        out.addAll(data.cast<Json>());
        break;
      }
      final map = data as Map;
      out.addAll((map['results'] as List).cast<Json>());
      if (map['next'] == null) break;
      page++;
    }
    return out;
  }

  Options _opts(bool auth) => Options(extra: {'noAuth': !auth});

  Future<dynamic> _wrap(Future<Response> Function() call) async {
    try {
      final r = await call();
      return r.data;
    } on DioException catch (e) {
      throw ApiException(_message(e), e.response?.statusCode);
    }
  }

  static String _message(DioException e) {
    final res = e.response;
    if (res == null) {
      return 'Serveur injoignable. Vérifiez votre connexion ou l\'adresse du serveur.';
    }
    final data = res.data;
    if (data is Map) {
      if (data['detail'] != null) return data['detail'].toString();
      final parts = <String>[];
      data.forEach((k, v) {
        final txt = v is List ? v.join(' ') : v.toString();
        parts.add(k == 'non_field_errors' ? txt : '$k : $txt');
      });
      if (parts.isNotEmpty) return parts.join('\n');
    }
    if (data is List && data.isNotEmpty) return data.join('\n');
    if (res.statusCode == 429) return 'Trop de tentatives. Réessayez plus tard.';
    return 'Erreur ${res.statusCode ?? ''}';
  }
}
