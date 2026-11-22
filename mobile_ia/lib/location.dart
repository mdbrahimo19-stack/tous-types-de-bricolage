import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';

import 'l10n.dart';

/// Position GPS du téléphone.
class GpsFix {
  const GpsFix(this.latitude, this.longitude, this.accuracy);

  final double latitude;
  final double longitude;

  /// Précision en mètres.
  final double accuracy;

  /// Format attendu par le serveur (6 décimales au plus).
  Map<String, double> toJson() => {'latitude': round6(latitude), 'longitude': round6(longitude)};
}

double round6(double v) => double.parse(v.toStringAsFixed(6));

/// Pourquoi la position n'a pas pu être obtenue (clé de traduction : `gps_<nom>`).
enum GpsError { off, denied, failed }

class GpsException implements Exception {
  const GpsException(this.error);

  final GpsError error;

  String get l10nKey => 'gps_${error.name}';
}

/// Demande la permission si besoin, puis lit la position actuelle.
Future<GpsFix> currentPosition() async {
  try {
    if (!await Geolocator.isLocationServiceEnabled()) throw const GpsException(GpsError.off);
    var perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.denied) perm = await Geolocator.requestPermission();
    if (perm == LocationPermission.denied || perm == LocationPermission.deniedForever) {
      throw const GpsException(GpsError.denied);
    }
    try {
      final p = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high, timeLimit: Duration(seconds: 20)),
      );
      return GpsFix(p.latitude, p.longitude, p.accuracy);
    } catch (_) {
      // pas de signal à temps : dernière position connue, si le téléphone en a une
      final last = await Geolocator.getLastKnownPosition();
      if (last != null) return GpsFix(last.latitude, last.longitude, last.accuracy);
      throw const GpsException(GpsError.failed);
    }
  } on GpsException {
    rethrow;
  } catch (_) {
    throw const GpsException(GpsError.failed);
  }
}

/// Carte « Votre position » du formulaire de demande : localise le client
/// automatiquement à l'ouverture, avec un bouton pour réessayer.
class GpsCard extends StatefulWidget {
  const GpsCard({super.key, required this.onChanged, this.locate = currentPosition});

  final ValueChanged<GpsFix?> onChanged;

  /// Remplaçable dans les tests.
  final Future<GpsFix> Function() locate;

  @override
  State<GpsCard> createState() => _GpsCardState();
}

class _GpsCardState extends State<GpsCard> {
  GpsFix? _fix;
  String? _errorKey;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _locate());
  }

  Future<void> _locate() async {
    if (!mounted) return;
    setState(() {
      _busy = true;
      _errorKey = null;
    });
    GpsFix? fix;
    String? error;
    try {
      fix = await widget.locate();
    } on GpsException catch (e) {
      error = e.l10nKey;
    }
    if (!mounted) return;
    setState(() {
      _busy = false;
      _fix = fix;
      _errorKey = error;
    });
    widget.onChanged(fix);
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final fix = _fix;
    final String status;
    if (_busy) {
      status = context.tr('gps_locating');
    } else if (fix != null) {
      status = context.tr('gps_ok', {'m': fix.accuracy.round()});
    } else {
      status = '${context.tr(_errorKey ?? 'gps_failed')} ${context.tr('gps_without')}';
    }
    return Card(
      color: fix != null ? scheme.primaryContainer : null,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 8, 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(fix != null ? Icons.my_location : Icons.location_searching,
                color: fix != null ? scheme.onPrimaryContainer : scheme.outline),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(context.tr('gps_title'), style: const TextStyle(fontWeight: FontWeight.bold)),
                Text(status),
              ]),
            ),
            if (_busy)
              const Padding(
                padding: EdgeInsets.all(12),
                child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)),
              )
            else
              TextButton(
                onPressed: _locate,
                child: Text(context.tr(fix != null ? 'gps_refresh' : 'gps_retry')),
              ),
          ]),
          const SizedBox(height: 4),
          Text(context.tr('gps_why_client'), style: Theme.of(context).textTheme.bodySmall),
        ]),
      ),
    );
  }
}
