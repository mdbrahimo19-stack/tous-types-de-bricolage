import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';

import 'core/config.dart';
import 'core/session.dart';
import 'screens/home_screen.dart';
import 'screens/onboarding_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await AppConfig.load();
  final session = Session();
  runApp(ChangeNotifierProvider.value(value: session, child: const TtbApp()));
  await session.init();
}

class TtbApp extends StatelessWidget {
  const TtbApp({super.key});

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    const seed = Color(0xFF1565C0);
    return MaterialApp(
      title: 'Tous Types de Bricolages',
      debugShowCheckedModeBanner: false,
      locale: session.locale,
      supportedLocales: const [Locale('fr'), Locale('ar')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: seed),
        useMaterial3: true,
        inputDecorationTheme: const InputDecorationTheme(border: OutlineInputBorder()),
      ),
      home: !session.ready
          ? const Scaffold(body: Center(child: CircularProgressIndicator()))
          : (session.onboardingDone || session.loggedIn)
              ? const HomeScreen()
              : const OnboardingScreen(),
    );
  }
}
