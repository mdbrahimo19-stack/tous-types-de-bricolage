import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ttb_mobile/location.dart';

Widget _wrap(Widget child) => MaterialApp(home: Scaffold(body: child));

void main() {
  test('coordonnées envoyées avec 6 décimales au plus', () {
    const fix = GpsFix(36.75382169, 3.05875614, 8);
    expect(fix.toJson(), {'latitude': 36.753822, 'longitude': 3.058756});
  });

  testWidgets('position trouvée : affichée et transmise au formulaire', (tester) async {
    GpsFix? received;
    await tester.pumpWidget(_wrap(GpsCard(
      onChanged: (f) => received = f,
      locate: () async => const GpsFix(36.72, 3.09, 12.4),
    )));
    await tester.pumpAndSettle();

    expect(find.text('Position trouvée (précision ± 12 m)'), findsOneWidget);
    expect(received?.latitude, 36.72);
    expect(find.text('Actualiser'), findsOneWidget);
  });

  testWidgets('accès refusé : message clair, demande sans position, bouton Réessayer', (tester) async {
    var calls = 0;
    GpsFix? received = const GpsFix(0, 0, 0);
    await tester.pumpWidget(_wrap(GpsCard(
      onChanged: (f) => received = f,
      locate: () async {
        calls++;
        throw const GpsException(GpsError.denied);
      },
    )));
    await tester.pumpAndSettle();

    expect(find.textContaining('refusé'), findsOneWidget);
    expect(find.textContaining('bricoleurs de votre commune'), findsOneWidget);
    expect(received, isNull);

    await tester.tap(find.text('Réessayer'));
    await tester.pumpAndSettle();
    expect(calls, 2);
  });
}
