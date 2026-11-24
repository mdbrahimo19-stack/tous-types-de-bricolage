import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/api_client.dart';
import '../flavor.dart';

/// Session utilisateur : compte connecté et langue.
/// Le rôle (client / artisan) dépend de l'application installée : BRICOOL ou BRICOOL Pro.
class Session extends ChangeNotifier {
  Session(this.api) {
    api.onSessionExpired = _onExpired;
  }

  final ApiClient api;

  static const _kLocale = 'locale';
  static const _kUserCache = 'user_cache';

  Json? user;
  String locale = 'fr';
  bool ready = false;

  bool get loggedIn => user != null;
  bool get isProvider => user?['is_provider'] == true;
  int get userId => user!['id'] as int;
  String get firstName => ((user?['full_name'] as String?) ?? '').split(' ').first;
  Json? get providerProfile => (user?['provider_profile'] as Map?)?.cast<String, dynamic>();
  String get verificationStatus => (providerProfile?['verification_status'] as String?) ?? 'pending';

  /// Écrans artisan dans BRICOOL Pro, écrans client dans BRICOOL.
  bool get asProvider => AppFlavor.isPro;

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    locale = prefs.getString(_kLocale) ??
        (PlatformDispatcher.instance.locale.languageCode == 'ar' ? 'ar' : 'fr');

    await api.loadTokens();
    if (api.hasSession) {
      try {
        user = (await api.get('/api/auth/me/') as Map).cast<String, dynamic>();
        await _cacheUser();
      } on ApiException catch (e) {
        if (e.status == 401) {
          await api.clearTokens();
        } else {
          // hors ligne : on garde le dernier profil connu
          final cached = prefs.getString(_kUserCache);
          if (cached != null) user = (jsonDecode(cached) as Map).cast<String, dynamic>();
        }
      }
    }
    ready = true;
    notifyListeners();
  }

  /// Renvoie le code OTP en mode développement (DEBUG côté Django), sinon null.
  Future<String?> requestOtp(String phone, String purpose) async {
    final data = await api.post('/api/auth/otp/request/', {'phone': phone, 'purpose': purpose}) as Map;
    return data['debug_code'] as String?;
  }

  Future<void> verifyOtp({
    required String phone,
    required String code,
    required String purpose,
    String fullName = '',
  }) async {
    final data = await api.post('/api/auth/otp/verify/', {
      'phone': phone,
      'code': code,
      'purpose': purpose,
      // BRICOOL Pro : le compte devient artisan (même s'il existait déjà comme client)
      'as_provider': AppFlavor.isPro,
      if (purpose == 'registration') ...{
        'full_name': fullName,
        'language': locale,
      },
    }) as Map;
    final tokens = data['tokens'] as Map;
    await api.saveTokens(tokens['access'] as String, tokens['refresh'] as String);
    user = (data['user'] as Map).cast<String, dynamic>();
    final serverLang = user!['language'] as String?;
    if (serverLang == 'fr' || serverLang == 'ar') locale = serverLang!;
    await _savePrefs();
    await _cacheUser();
    notifyListeners();
  }

  Future<void> refreshUser() async {
    user = (await api.get('/api/auth/me/') as Map).cast<String, dynamic>();
    await _cacheUser();
    notifyListeners();
  }

  Future<void> setLocale(String value) async {
    locale = value;
    await _savePrefs();
    notifyListeners();
    if (loggedIn) {
      try {
        await api.patch('/api/auth/me/', {'language': value});
      } on ApiException {
        // la préférence locale suffit ; le serveur sera mis à jour plus tard
      }
    }
  }

  Future<void> logout() async {
    final refresh = api.refreshToken;
    if (refresh != null) {
      try {
        await api.post('/api/auth/logout/', {'refresh': refresh});
      } on ApiException {
        // déconnexion locale quoi qu'il arrive
      }
    }
    await api.clearTokens();
    await _clearUser();
  }

  void _onExpired() => _clearUser();

  Future<void> _clearUser() async {
    user = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kUserCache);
    notifyListeners();
  }

  Future<void> _savePrefs() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kLocale, locale);
  }

  Future<void> _cacheUser() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kUserCache, jsonEncode(user));
  }
}
