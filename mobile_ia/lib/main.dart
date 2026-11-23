import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:provider/provider.dart';

import 'api/api_client.dart';
import 'config.dart';
import 'screens/auth.dart';
import 'screens/shell.dart';
import 'state/session.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting('fr');
  await initializeDateFormatting('ar');
  await ServerConfig.load();
  final session = Session(ApiClient());
  await session.init();
  runApp(ChangeNotifierProvider.value(value: session, child: const TtbApp()));
}

class TtbApp extends StatelessWidget {
  const TtbApp({super.key});

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    const seed = Color(0xFFE8740C); // orange « chantier »
    return MaterialApp(
      title: 'BRICOOL',
      debugShowCheckedModeBanner: false,
      locale: Locale(session.locale),
      supportedLocales: const [Locale('fr'), Locale('ar')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: seed),
        inputDecorationTheme: const InputDecorationTheme(border: OutlineInputBorder()),
        cardTheme: const CardThemeData(margin: EdgeInsets.zero),
      ),
      // la clé force un nouvel arbre de navigation à la connexion / déconnexion
      home: session.loggedIn ? const HomeShell(key: ValueKey('home')) : const PhoneScreen(key: ValueKey('auth')),
    );
  }
}
