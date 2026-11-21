import 'dart:ui' show AccessibilityFeatures;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:ttb_mobile/api/api_client.dart';
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
