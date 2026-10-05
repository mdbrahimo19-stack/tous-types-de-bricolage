import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:ttb_mobile/api/api_client.dart';
import 'package:ttb_mobile/main.dart';
import 'package:ttb_mobile/state/session.dart';

void main() {
  testWidgets('connexion en français puis bascule en arabe (RTL)', (tester) async {
    SharedPreferences.setMockInitialValues({});
    final session = Session(ApiClient());

    await tester.pumpWidget(ChangeNotifierProvider.value(value: session, child: const TtbApp()));
    await tester.pumpAndSettle();

    expect(find.text('Continuer'), findsOneWidget);
    expect(find.text('Numéro de téléphone'), findsOneWidget);

    await tester.tap(find.text('العربية'));
    await tester.pumpAndSettle();

    expect(find.text('متابعة'), findsOneWidget);
    expect(Directionality.of(tester.element(find.text('متابعة'))), TextDirection.rtl);
    expect(session.locale, 'ar');
  });
}
