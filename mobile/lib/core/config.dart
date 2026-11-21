import 'package:shared_preferences/shared_preferences.dart';

/// Adresse du serveur Django.
///
/// Par défaut : `10.0.2.2:8000` = le PC hôte vu depuis l'émulateur Android.
/// Sur un vrai téléphone, changer l'adresse dans Profil → Serveur
/// (ex. `http://192.168.1.20:8000`), ou compiler avec
/// `--dart-define=API_BASE_URL=https://api.exemple.dz`.
class AppConfig {
  static const String _defaultBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );
  static const _key = 'api_base_url';

  static String baseUrl = _defaultBaseUrl;

  static Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    baseUrl = prefs.getString(_key) ?? _defaultBaseUrl;
  }

  static Future<void> setBaseUrl(String url) async {
    var clean = url.trim();
    while (clean.endsWith('/')) {
      clean = clean.substring(0, clean.length - 1);
    }
    if (clean.isEmpty) clean = _defaultBaseUrl;
    baseUrl = clean;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, clean);
  }

  static String get apiUrl => '$baseUrl/api';

  /// Les champs image de l'API peuvent être relatifs (`/media/...` ou `media/...`).
  static String mediaUrl(String? path) {
    if (path == null || path.isEmpty) return '';
    if (path.startsWith('http')) return path;
    return path.startsWith('/') ? '$baseUrl$path' : '$baseUrl/$path';
  }
}
