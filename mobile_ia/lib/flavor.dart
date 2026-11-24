import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show appFlavor;

/// Deux applications à partir du même code, choisies à la compilation :
///   flutter build apk --flavor client   -> « BRICOOL »     (clients)
///   flutter build apk --flavor pro      -> « BRICOOL Pro » (artisans)
class AppFlavor {
  AppFlavor._();

  /// Pour les tests : force 'client' ou 'pro' sans recompiler.
  static String? debugOverride;

  static bool get isPro => (debugOverride ?? appFlavor) == 'pro';

  static String get name => isPro ? 'BRICOOL Pro' : 'BRICOOL';

  /// Dégradé de l'écran de connexion.
  static List<Color> get heroGradient => isPro
      ? const [Color(0xFF3B5A85), Color(0xFF1F3550), Color(0xFF0F1B2B)]
      : const [Color(0xFFF59A3A), Color(0xFFD9670F), Color(0xFF8A3F0E)];
}
