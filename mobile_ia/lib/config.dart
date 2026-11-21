import 'package:shared_preferences/shared_preferences.dart';

/// Adresse du backend Django, modifiable dans l'app (écran de connexion ou Profil → Serveur).
///
/// - Émulateur Android : http://10.0.2.2:8000 (valeur par défaut)
/// - Téléphone réel sur le même Wi-Fi : l'IP du PC, ex. http://192.168.1.20:8000
///   (lancer Django avec `python manage.py runserver 0.0.0.0:8000`
///   et ajouter l'IP dans DJANGO_ALLOWED_HOSTS)
/// - Valeur par défaut à la compilation : `--dart-define=API_URL=https://api.exemple.dz`
class ServerConfig {
  static const String defaultUrl = String.fromEnvironment('API_URL', defaultValue: 'http://10.0.2.2:8000');
  static const _key = 'api_base_url';

  static String baseUrl = defaultUrl;

  static Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    baseUrl = prefs.getString(_key) ?? defaultUrl;
  }

  /// Nettoie une adresse saisie : espaces, `/` final, `http://` ajouté si absent.
  static String normalize(String input) {
    var url = input.trim();
    while (url.endsWith('/')) {
      url = url.substring(0, url.length - 1);
    }
    if (url.isEmpty) return defaultUrl;
    if (!url.startsWith('http://') && !url.startsWith('https://')) url = 'http://$url';
    return url;
  }

  static Future<void> save(String input) async {
    baseUrl = normalize(input);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, baseUrl);
  }
}

/// Intervalle de rafraîchissement de la messagerie (polling REST, pas de WebSocket en v1).
const Duration chatPollInterval = Duration(seconds: 7);

const int maxRequestPhotos = 4;
