import 'package:flutter_test/flutter_test.dart';
import 'package:ttb/core/config.dart';
import 'package:ttb/core/format.dart';
import 'package:ttb/core/i18n.dart';

void main() {
  test('toDouble lit les DecimalField DRF', () {
    expect(toDouble('1500.00'), 1500);
    expect(toDouble(12), 12);
    expect(toDouble(null), isNull);
  });

  test('money affiche le montant en DA', () {
    expect(money('2500.00'), contains('DA'));
    expect(money(null), '—');
  });

  test('mediaUrl gère les chemins relatifs et absolus', () {
    AppConfig.baseUrl = 'http://10.0.2.2:8000';
    expect(AppConfig.mediaUrl('/media/a.jpg'), 'http://10.0.2.2:8000/media/a.jpg');
    expect(AppConfig.mediaUrl('media/a.jpg'), 'http://10.0.2.2:8000/media/a.jpg');
    expect(AppConfig.mediaUrl('https://x.dz/a.jpg'), 'https://x.dz/a.jpg');
  });

  test('traductions FR et AR complètes', () {
    final fr = S('fr');
    final ar = S('ar');
    for (final key in ['publish_request', 'u_today', 's_published', 'm_paid', 'accept']) {
      expect(fr.t(key), isNot(key));
      expect(ar.t(key), isNot(key));
      expect(ar.t(key), isNot(fr.t(key)));
    }
    expect(ar.name({'name_fr': 'Plomberie', 'name_ar': 'سباكة'}), 'سباكة');
    expect(fr.name({'name_fr': 'Plomberie', 'name_ar': 'سباكة'}), 'Plomberie');
  });
}
