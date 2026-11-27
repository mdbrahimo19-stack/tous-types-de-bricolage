import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:provider/provider.dart';

import 'api/api_client.dart';
import 'config.dart';
import 'flavor.dart';
import 'l10n.dart';
import 'screens/auth.dart';
import 'screens/shell.dart';
import 'state/session.dart';
import 'theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting('fr');
  await initializeDateFormatting('ar');
  await ServerConfig.load();
  final session = Session(ApiClient());
  // l'app s'affiche tout de suite (écran de chargement) : elle ne reste jamais figée
  // si le serveur est injoignable au démarrage
  runApp(ChangeNotifierProvider.value(value: session, child: const TtbApp()));
  await session.init();
}

/// Premier lancement : l'utilisateur choisit son espace (client ou artisan). Modifiable ensuite dans le Profil.
class _RoleChoiceScreen extends StatelessWidget {
  const _RoleChoiceScreen();

  @override
  Widget build(BuildContext context) {
    final session = context.read<Session>();
    Widget choice(String role, Color color, IconData icon, String titleKey, String subKey) => Material(
          color: color,
          borderRadius: BorderRadius.circular(22),
          child: InkWell(
            borderRadius: BorderRadius.circular(22),
            onTap: () => session.setRole(role),
            child: Padding(
              padding: const EdgeInsets.all(22),
              child: Row(children: [
                Icon(icon, color: Colors.white, size: 40),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(context.tr(titleKey),
                        style: const TextStyle(color: Colors.white, fontSize: 19, fontWeight: FontWeight.w800)),
                    const SizedBox(height: 4),
                    Text(context.tr(subKey), style: const TextStyle(color: Colors.white, fontSize: 13.5)),
                  ]),
                ),
                const Icon(Icons.chevron_right, color: Colors.white),
              ]),
            ),
          ),
        );
    return Scaffold(
      backgroundColor: const Color(0xFFFAF7F3),
      body: SafeArea(
        child: ListView(padding: const EdgeInsets.fromLTRB(20, 48, 20, 24), children: [
          const Text('BRICOOL',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 34, fontWeight: FontWeight.w800, color: Color(0xFFC2560A))),
          const SizedBox(height: 8),
          Text(context.tr('role_question'),
              textAlign: TextAlign.center, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
          const SizedBox(height: 28),
          choice('client', const Color(0xFFC2560A), Icons.home_repair_service_outlined, 'role_client', 'role_client_sub'),
          const SizedBox(height: 14),
          choice('pro', const Color(0xFF1B2A41), Icons.handyman_outlined, 'role_pro', 'role_pro_sub'),
          const SizedBox(height: 20),
          Text(context.tr('role_hint'),
              textAlign: TextAlign.center, style: const TextStyle(fontSize: 13, color: Color(0xFF5E554E))),
        ]),
      ),
    );
  }
}

/// Écran de démarrage (quelques secondes au plus) : nom de l'app sur son dégradé + chargement.
class _StartupScreen extends StatelessWidget {
  const _StartupScreen();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: AppFlavor.heroGradient,
          ),
        ),
        child: Center(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Text(AppFlavor.name,
                style: const TextStyle(color: Colors.white, fontSize: 30, fontWeight: FontWeight.w800)),
            const SizedBox(height: 24),
            const SizedBox(width: 28, height: 28, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 3)),
          ]),
        ),
      ),
    );
  }
}

class TtbApp extends StatelessWidget {
  const TtbApp({super.key});

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    return MaterialApp(
      title: AppFlavor.name,
      debugShowCheckedModeBanner: false,
      locale: Locale(session.locale),
      supportedLocales: const [Locale('fr'), Locale('ar')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      // orange (BRICOOL) ou bleu nuit (BRICOOL Pro), police Poppins : voir theme.dart
      theme: buildAppTheme(),
      // la clé force un nouvel arbre de navigation à la connexion / déconnexion
      home: session.initializing
          ? const _StartupScreen()
          : session.role == null && AppFlavor.debugOverride == null
              ? const _RoleChoiceScreen()
          : session.loggedIn
              ? const HomeShell(key: ValueKey('home'))
              : const PhoneScreen(key: ValueKey('auth')),
    );
  }
}
