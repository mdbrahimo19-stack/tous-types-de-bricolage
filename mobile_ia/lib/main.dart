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
  await session.init();
  runApp(ChangeNotifierProvider.value(value: session, child: const TtbApp()));
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
      home: session.loggedIn ? const HomeShell(key: ValueKey('home')) : const PhoneScreen(key: ValueKey('auth')),
    );
  }
}
