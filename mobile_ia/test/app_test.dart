import 'dart:ui' show AccessibilityFeatures;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:ttb_mobile/api/api_client.dart';
import 'package:ttb_mobile/flavor.dart';
import 'package:ttb_mobile/main.dart';
import 'package:ttb_mobile/state/session.dart';
import 'package:ttb_mobile/widgets/floating_services.dart';

/// Simule le réglage Android « Supprimer les animations ».
class _NoAnimations implements AccessibilityFeatures {
  @override
  bool get disableAnimations => true;

  @override
  dynamic noSuchMethod(Invocation invocation) => false;
}

void main() {
  // app unique : l'espace « client » est déjà choisi (l'écran de choix a son propre test)
  setUp(() => AppFlavor.role = 'client');
  tearDown(() => AppFlavor.role = null);

  testWidgets('premier lancement : choix de l\'espace client ou artisan', (tester) async {
    AppFlavor.role = null;
    SharedPreferences.setMockInitialValues({});
    final session = Session(ApiClient());
    await tester.pumpWidget(ChangeNotifierProvider.value(value: session, child: const TtbApp()));
    await tester.pump();
    expect(find.text('Je cherche un artisan'), findsOneWidget);
    await tester.tap(find.text('Je suis artisan'));
    await tester.pump(const Duration(milliseconds: 300));
    expect(session.role, 'pro');
    expect(session.asProvider, isTrue);
  });

  testWidgets('connexion en français puis bascule en arabe (RTL)', (
    tester,
  ) async {
    // animations coupées : l'écran devient statique et pumpAndSettle peut se terminer
    tester.platformDispatcher.accessibilityFeaturesTestValue = _NoAnimations();
    addTearDown(tester.platformDispatcher.clearAccessibilityFeaturesTestValue);
    SharedPreferences.setMockInitialValues({});
    final session = Session(ApiClient());

    await tester.pumpWidget(
      ChangeNotifierProvider.value(value: session, child: const TtbApp()),
    );
    await tester.pumpAndSettle();

    expect(find.text('Continuer'), findsOneWidget);
    expect(find.text('Numéro de téléphone'), findsOneWidget);
    expect(find.byType(ServiceBubble), findsWidgets);

    await tester.tap(find.text('العربية'));
    await tester.pumpAndSettle();

    expect(find.text('متابعة'), findsOneWidget);
    expect(
      Directionality.of(tester.element(find.text('متابعة'))),
      TextDirection.rtl,
    );
    expect(session.locale, 'ar');
  });

  testWidgets('les services flottent et défilent sans erreur', (tester) async {
    SharedPreferences.setMockInitialValues({});
    // téléphone classique : 412 x 915 points logiques
    tester.view.devicePixelRatio = 3;
    tester.view.physicalSize = const Size(412 * 3, 915 * 3);
    addTearDown(tester.view.reset);
    final session = Session(ApiClient());

    await tester.pumpWidget(
      ChangeNotifierProvider.value(value: session, child: const TtbApp()),
    );
    final bubble = find.byType(ServiceBubble).first;
    final before = tester.getTopLeft(bubble);
    // animation infinie : on avance le temps au lieu d'attendre la fin
    await tester.pump(const Duration(seconds: 2));
    expect(tester.getTopLeft(bubble), isNot(before));
    expect(find.byType(ServicesMarquee), findsNWidgets(2));
    expect(find.text('Plomberie'), findsWidgets);
    expect(tester.takeException(), isNull);
  });

  testWidgets('le champ téléphone garde la main quand le clavier s\'ouvre', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({});
    tester.view.devicePixelRatio = 3;
    tester.view.physicalSize = const Size(412 * 3, 915 * 3);
    addTearDown(tester.view.reset);
    final session = Session(ApiClient());

    await tester.pumpWidget(
      ChangeNotifierProvider.value(value: session, child: const TtbApp()),
    );
    await tester.pump(const Duration(milliseconds: 300));

    final field = find.byType(TextField);
    await tester.tap(field);
    await tester.pump();
    // le clavier apparaît : l'écran passe en mode compact
    tester.view.viewInsets = const FakeViewPadding(bottom: 320 * 3);
    await tester.pump(const Duration(milliseconds: 300));

    final editable = tester.state<EditableTextState>(find.byType(EditableText));
    expect(
      editable.widget.focusNode.hasFocus,
      isTrue,
      reason: 'le champ a perdu le focus',
    );
    await tester.enterText(field, '0661234567');
    await tester.pump();
    expect(find.text('0661234567'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('deux applications : BRICOOL (client) et BRICOOL Pro (artisan)', (
    tester,
  ) async {
    tester.platformDispatcher.accessibilityFeaturesTestValue = _NoAnimations();
    addTearDown(tester.platformDispatcher.clearAccessibilityFeaturesTestValue);
    addTearDown(() => AppFlavor.debugOverride = null);
    SharedPreferences.setMockInitialValues({});

    // app client (par défaut)
    final client = Session(ApiClient());
    await tester.pumpWidget(
      ChangeNotifierProvider.value(value: client, child: const TtbApp()),
    );
    await tester.pumpAndSettle();
    expect(find.text('BRICOOL'), findsOneWidget);
    expect(client.asProvider, isFalse);

    // app artisan
    AppFlavor.debugOverride = 'pro';
    final pro = Session(ApiClient());
    await tester.pumpWidget(
      ChangeNotifierProvider.value(value: pro, child: const TtbApp(key: ValueKey('pro'))),
    );
    await tester.pumpAndSettle();
    expect(find.text('BRICOOL Pro'), findsOneWidget);
    expect(pro.asProvider, isTrue);
    expect(tester.takeException(), isNull);
  });

  testWidgets('serveur injoignable au démarrage : écran de chargement puis connexion', (tester) async {
    SharedPreferences.setMockInitialValues({});
    final session = Session(ApiClient());
    session.initializing = true; // démarrage en cours
    await tester.pumpWidget(
      ChangeNotifierProvider.value(value: session, child: const TtbApp()),
    );
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.text('Continuer'), findsNothing);

    session.initializing = false; // démarrage terminé (sans compte enregistré)
    session.notifyListeners();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('Continuer'), findsOneWidget);
  });

  testWidgets('petit écran et clavier ouvert : aucun débordement', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({});
    tester.view.devicePixelRatio = 2;
    tester.view.physicalSize = const Size(360 * 2, 640 * 2);
    addTearDown(tester.view.reset);
    final session = Session(ApiClient());

    await tester.pumpWidget(
      ChangeNotifierProvider.value(value: session, child: const TtbApp()),
    );
    await tester.pump(const Duration(milliseconds: 500));
    expect(tester.takeException(), isNull);
    expect(find.text('Continuer'), findsOneWidget);

    // clavier ouvert : ~300 points occupés en bas de l'écran
    tester.view.viewInsets = const FakeViewPadding(bottom: 300 * 2);
    await tester.pump(const Duration(milliseconds: 500));
    expect(tester.takeException(), isNull);
    expect(find.text('Continuer'), findsOneWidget);
  });
}
