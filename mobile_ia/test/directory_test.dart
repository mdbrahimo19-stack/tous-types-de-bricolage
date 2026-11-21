import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ttb_mobile/screens/directory.dart';

void main() {
  final provider = <String, dynamic>{
    'id': 1,
    'full_name': 'Karim B.',
    'business_name': 'Karim Plomberie',
    'photo': null,
    'rating_avg': '4.80',
    'reviews_count': 12,
    'missions_count': 30,
    'is_available': true,
    'badges': ['identite_verifiee'],
    'base_wilaya': {'id': 16, 'code': '16', 'name_fr': 'Alger', 'name_ar': 'الجزائر'},
    'categories': [
      {'id': 1, 'name_fr': 'Plomberie', 'name_ar': 'سباكة', 'flat_rate': '3000.00', 'hourly_rate': null},
      {'id': 2, 'name_fr': 'Chauffage', 'name_ar': 'تدفئة', 'flat_rate': null, 'hourly_rate': '1500.00'},
    ],
  };

  test('nom commercial prioritaire, sinon nom complet', () {
    expect(providerName(provider), 'Karim Plomberie');
    expect(providerName({...provider, 'business_name': '  '}), 'Karim B.');
  });

  test('prix « à partir de » = plus petit tarif annoncé', () {
    expect(lowestPrice(provider), 1500);
    expect(lowestPrice({...provider, 'categories': []}), isNull);
  });

  testWidgets('la carte affiche nom, métiers, wilaya, note et prix', (tester) async {
    var tapped = false;
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: ProviderCard(provider: provider, onTap: () => tapped = true)),
    ));
    expect(find.text('Karim Plomberie'), findsOneWidget);
    expect(find.text('Plomberie · Chauffage'), findsOneWidget);
    expect(find.text('Alger'), findsOneWidget);
    expect(find.textContaining('4.8'), findsOneWidget);
    // séparateur de milliers français = espace insécable (fine), pas une espace simple
    expect(find.textContaining(RegExp(r'1\s?500')), findsOneWidget);
    expect(find.byIcon(Icons.verified), findsOneWidget);
    await tester.tap(find.byType(ProviderCard));
    expect(tapped, isTrue);
  });
}
