/// URL du backend Django.
///
/// - Émulateur Android : http://10.0.2.2:8000 (valeur par défaut)
/// - Téléphone réel sur le même Wi-Fi : l'IP du PC, ex.
///   flutter run --dart-define=API_URL=http://192.168.1.20:8000
///   (lancer alors Django avec `python manage.py runserver 0.0.0.0:8000`
///   et ajouter l'IP dans DJANGO_ALLOWED_HOSTS)
const String apiBaseUrl = String.fromEnvironment(
  'API_URL',
  defaultValue: 'http://10.0.2.2:8000',
);

/// Intervalle de rafraîchissement de la messagerie (polling REST, pas de WebSocket en v1).
const Duration chatPollInterval = Duration(seconds: 7);

const int maxRequestPhotos = 4;
