import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:provider/provider.dart';

import 'api/api_client.dart';
import 'config.dart';
import 'flavor.dart';
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
          : session.loggedIn
              ? const HomeShell(key: ValueKey('home'))
              : const PhoneScreen(key: ValueKey('auth')),
    );
  }
}
