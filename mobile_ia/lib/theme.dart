import 'package:flutter/material.dart';

import 'flavor.dart';

/// Couleurs de la maquette (orange pour BRICOOL, bleu nuit pour BRICOOL Pro).
/// Les couleurs de texte et de boutons sont assez foncées pour rester lisibles (contraste ≥ 4,5:1).
class AppPalette {
  const AppPalette({
    required this.primary,
    required this.background,
    required this.ink,
    required this.muted,
    required this.border,
  });

  final Color primary; // boutons, onglet actif, liens
  final Color background; // fond des écrans
  final Color ink; // texte principal
  final Color muted; // texte secondaire
  final Color border; // contours des cartes et des champs

  static const success = Color(0xFF0E7A55); // badge « Vérifié »
  static const successSoft = Color(0xFFE4F3EC);
  static const star = Color(0xFFE0A100);

  static const client = AppPalette(
    primary: Color(0xFFC2560A),
    background: Color(0xFFFAF7F3),
    ink: Color(0xFF1F1A17),
    muted: Color(0xFF5E554E),
    border: Color(0xFFEDE5DC),
  );

  static const pro = AppPalette(
    primary: Color(0xFF1B2A41),
    background: Color(0xFFF3F5F9),
    ink: Color(0xFF141B26),
    muted: Color(0xFF5A6577),
    border: Color(0xFFE1E6EE),
  );

  static AppPalette get current => AppFlavor.isPro ? pro : client;
}

/// Thème commun aux deux applications : police Poppins, cartes et boutons arrondis.
ThemeData buildAppTheme() {
  final p = AppPalette.current;
  final scheme = ColorScheme.fromSeed(seedColor: p.primary).copyWith(
    primary: p.primary,
    onPrimary: Colors.white,
    surface: Colors.white,
    onSurface: p.ink,
    onSurfaceVariant: p.muted,
    outline: p.border,
    outlineVariant: p.border,
  );
  final rounded14 = RoundedRectangleBorder(borderRadius: BorderRadius.circular(14));
  const buttonText = TextStyle(fontSize: 15, fontWeight: FontWeight.w700);

  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    fontFamily: 'Poppins',
    scaffoldBackgroundColor: p.background,
    appBarTheme: AppBarTheme(
      backgroundColor: p.background,
      foregroundColor: p.ink,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0,
      titleTextStyle: TextStyle(fontFamily: 'Poppins', fontSize: 18, fontWeight: FontWeight.w700, color: p.ink),
    ),
    cardTheme: CardThemeData(
      margin: EdgeInsets.zero,
      color: Colors.white,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: p.border),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(minimumSize: const Size(64, 48), shape: rounded14, textStyle: buttonText),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(64, 48),
        shape: rounded14,
        textStyle: buttonText,
        foregroundColor: p.ink,
        side: BorderSide(color: p.border, width: 1.5),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(textStyle: const TextStyle(fontWeight: FontWeight.w600)),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: p.border)),
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: p.border)),
      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: p.primary, width: 2)),
    ),
    chipTheme: ChipThemeData(
      shape: const StadiumBorder(),
      side: BorderSide(color: p.border),
      backgroundColor: Colors.white,
      labelStyle: TextStyle(fontFamily: 'Poppins', fontWeight: FontWeight.w600, color: p.ink),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: Colors.white,
      surfaceTintColor: Colors.transparent,
      indicatorColor: p.primary.withValues(alpha: 0.12),
      iconTheme: WidgetStateProperty.resolveWith(
        (s) => IconThemeData(color: s.contains(WidgetState.selected) ? p.primary : p.muted),
      ),
      labelTextStyle: WidgetStateProperty.resolveWith(
        (s) => TextStyle(
          fontFamily: 'Poppins',
          fontSize: 11.5,
          fontWeight: s.contains(WidgetState.selected) ? FontWeight.w700 : FontWeight.w500,
          color: s.contains(WidgetState.selected) ? p.primary : p.muted,
        ),
      ),
    ),
    dividerTheme: DividerThemeData(color: p.border, space: 24),
    listTileTheme: ListTileThemeData(iconColor: p.muted),
    snackBarTheme: SnackBarThemeData(behavior: SnackBarBehavior.floating, backgroundColor: p.ink),
  );
}
