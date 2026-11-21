import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api.dart';

/// État global : utilisateur connecté, langue, onboarding.
class Session extends ChangeNotifier {
  final api = Api.instance;

  Json? user;
  Locale locale = const Locale('fr');
  bool onboardingDone = false;
  bool ready = false;

  bool get loggedIn => user != null;
  String get displayName =>
      (user?['full_name']?.toString().isNotEmpty ?? false) ? user!['full_name'] : (user?['phone'] ?? '');

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    locale = Locale(prefs.getString('lang') ?? 'fr');
    onboardingDone = prefs.getBool('onboarding_done') ?? false;
    api.onSessionExpired = () {
      user = null;
      notifyListeners();
    };
    await api.loadTokens();
    if (api.hasSession) {
      try {
        user = Map<String, dynamic>.from(await api.get('/auth/me/'));
      } on ApiException catch (e) {
        if (e.statusCode == 401) await api.clearTokens();
        // Hors ligne : on garde la session, l'utilisateur sera rechargé plus tard.
      }
    }
    ready = true;
    notifyListeners();
  }

  Future<void> setLanguage(String code) async {
    locale = Locale(code);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('lang', code);
    notifyListeners();
    if (loggedIn) {
      try {
        await api.patch('/auth/me/', data: {'language': code});
      } catch (_) {}
    }
  }

  Future<void> finishOnboarding() async {
    onboardingDone = true;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('onboarding_done', true);
    notifyListeners();
  }

  /// Étape 1 : demande d'un code OTP. Renvoie le code en mode développement.
  Future<String?> requestOtp(String phone) async {
    final data = await api.post('/auth/otp/request/',
        data: {'phone': phone, 'purpose': 'registration'}, auth: false);
    return (data as Map)['debug_code']?.toString();
  }

  /// Étape 2 : vérification du code (crée le compte s'il n'existe pas).
  Future<void> verifyOtp({
    required String phone,
    required String code,
    String fullName = '',
    bool asProvider = false,
  }) async {
    final data = await api.post('/auth/otp/verify/', auth: false, data: {
      'phone': phone,
      'code': code,
      'purpose': 'registration',
      'full_name': fullName,
      'as_provider': asProvider,
      'language': locale.languageCode,
    }) as Map;
    final tokens = data['tokens'] as Map;
    await api.saveTokens(tokens['access'], tokens['refresh']);
    user = Map<String, dynamic>.from(data['user']);
    notifyListeners();
  }

  Future<void> refreshUser() async {
    if (!api.hasSession) return;
    user = Map<String, dynamic>.from(await api.get('/auth/me/'));
    notifyListeners();
  }

  Future<void> updateName(String name) async {
    user = Map<String, dynamic>.from(await api.patch('/auth/me/', data: {'full_name': name}));
    notifyListeners();
  }

  Future<void> logout() async {
    final refresh = api.refreshToken;
    if (refresh != null) {
      try {
        await api.post('/auth/logout/', data: {'refresh': refresh});
      } catch (_) {}
    }
    await api.clearTokens();
    user = null;
    notifyListeners();
  }
}
