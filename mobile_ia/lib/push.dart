import 'dart:io' show Platform;

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import 'api/api_client.dart';

/// Notifications push (Firebase) : le téléphone sonne à chaque nouvelle demande, devis ou message,
/// même quand l'application est fermée.
///
/// Sans le fichier Firebase (google-services.json), par exemple dans les tests, tout est désactivé
/// sans erreur : l'application marche comme avant.
class Push {
  Push._();

  /// Même identifiant que le serveur (backend/apps/marketplace/push_fcm.py).
  static const channelId = 'bricool_alerts';

  static bool available = false;
  static String? _token;
  static ApiClient? _api;
  static final _local = FlutterLocalNotificationsPlugin();

  /// Au démarrage de l'app.
  static Future<void> init() async {
    if (kIsWeb || !(Platform.isAndroid || Platform.isIOS)) return;
    try {
      await Firebase.initializeApp();
    } catch (e) {
      debugPrint('Push désactivé (Firebase non configuré) : $e');
      return;
    }
    available = true;

    // canal Android : priorité haute, sonnerie et vibration
    await _local.initialize(
      settings: const InitializationSettings(
        android: AndroidInitializationSettings('@mipmap/ic_launcher'),
        iOS: DarwinInitializationSettings(),
      ),
    );
    await _local
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(const AndroidNotificationChannel(
          channelId,
          'Nouvelles demandes et messages',
          description: 'Sonne quand un client publie une demande près de vous, envoie un devis ou un message.',
          importance: Importance.high,
        ));

    // app ouverte : Android n'affiche rien tout seul, on montre la notification nous-mêmes (avec le son)
    FirebaseMessaging.onMessage.listen((message) {
      final n = message.notification;
      if (n == null) return;
      _local.show(
        id: message.hashCode,
        title: n.title,
        body: n.body,
        notificationDetails: const NotificationDetails(
          android: AndroidNotificationDetails(
            channelId,
            'Nouvelles demandes et messages',
            importance: Importance.high,
            priority: Priority.high,
          ),
          iOS: DarwinNotificationDetails(presentSound: true),
        ),
      );
    });

    // jeton FCM classique (accepté par l'API HTTP v1 du serveur) ; la nouvelle API « onRegistered »
    // renvoie un autre identifiant, on la gardera pour plus tard
    // ignore: deprecated_member_use
    FirebaseMessaging.instance.onTokenRefresh.listen((t) {
      final api = _api;
      if (api != null) _send(api, t);
    });
  }

  /// Après la connexion : demande l'autorisation (Android 13+) et enregistre ce téléphone sur le serveur.
  static Future<void> register(ApiClient api) async {
    _api = api;
    if (!available) return;
    try {
      await FirebaseMessaging.instance.requestPermission();
      // ignore: deprecated_member_use
      final token = await FirebaseMessaging.instance.getToken();
      if (token != null) await _send(api, token);
    } catch (e) {
      debugPrint('Enregistrement push impossible : $e');
    }
  }

  static Future<void> _send(ApiClient api, String token) async {
    try {
      await api.post('/api/devices/', {'token': token, 'platform': Platform.isIOS ? 'ios' : 'android'});
      _token = token;
    } on ApiException catch (e) {
      debugPrint('Enregistrement push refusé : ${e.status}');
    }
  }

  /// À la déconnexion : ce téléphone ne reçoit plus les notifications de ce compte.
  static Future<void> unregister(ApiClient api) async {
    final token = _token;
    _api = null;
    _token = null;
    if (!available || token == null) return;
    try {
      await api.delete('/api/devices/', {'token': token});
    } on ApiException {
      // le serveur oubliera ce jeton tout seul dès qu'il deviendra invalide
    }
  }
}
