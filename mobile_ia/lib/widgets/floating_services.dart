import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import '../l10n.dart';

/// Un service affiché sur l'écran d'accueil (liste fixe : visible même hors connexion).
class ServiceItem {
  const ServiceItem(this.icon, this.fr, this.ar, this.color);

  final IconData icon;
  final String fr;
  final String ar;
  final Color color;

  String label(BuildContext context) => context.isArabic ? ar : fr;
}

const _blue = Color(0xFF2F80ED);
const _teal = Color(0xFF14A38B);
const _amber = Color(0xFFF2A516);
const _red = Color(0xFFE5533D);
const _purple = Color(0xFF8E5CD9);
const _green = Color(0xFF3BAA4A);
const _pink = Color(0xFFE0568F);
const _slate = Color(0xFF4F6D8F);

/// Les 44 métiers du catalogue (mêmes libellés que `seed_base`).
const kServices = <ServiceItem>[
  ServiceItem(Icons.plumbing, 'Plomberie', 'سباكة', _blue),
  ServiceItem(Icons.electrical_services, 'Électricité', 'كهرباء', _amber),
  ServiceItem(Icons.ac_unit, 'Climatisation', 'تكييف', _teal),
  ServiceItem(Icons.format_paint, 'Peinture', 'دهن', _pink),
  ServiceItem(Icons.foundation, 'Maçonnerie', 'بناء', _slate),
  ServiceItem(Icons.carpenter, 'Menuiserie', 'نجارة', _amber),
  ServiceItem(
    Icons.local_laundry_service,
    'Électroménager',
    'أجهزة كهرومنزلية',
    _blue,
  ),
  ServiceItem(Icons.cleaning_services, 'Nettoyage', 'تنظيف', _teal),
  ServiceItem(Icons.yard, 'Jardinage', 'بستنة', _green),
  ServiceItem(Icons.local_shipping, 'Déménagement', 'نقل الأثاث', _red),
  ServiceItem(Icons.car_repair, 'Mécanique auto', 'ميكانيك السيارات', _slate),
  ServiceItem(Icons.electric_car, 'Électricien auto', 'كهربائي سيارات', _amber),
  ServiceItem(Icons.computer, 'Informatique', 'صيانة معلوماتية', _purple),
  ServiceItem(Icons.tv, 'Réparation TV', 'تصليح تلفزيون', _purple),
  ServiceItem(Icons.grid_on, 'Carrelage', 'تبليط', _slate),
  ServiceItem(Icons.layers, 'Plâtre et faux plafond', 'جبس وأسقف', _blue),
  ServiceItem(Icons.roofing, 'Étanchéité', 'عزل مائي', _teal),
  ServiceItem(Icons.view_quilt, 'Parquet', 'باركي', _amber),
  ServiceItem(Icons.window, 'Vitrerie', 'زجاج', _blue),
  ServiceItem(Icons.key, 'Serrurerie', 'أقفال', _amber),
  ServiceItem(Icons.hardware, 'Ferronnerie et soudure', 'حدادة ولحام', _red),
  ServiceItem(
    Icons.door_sliding,
    'Aluminium et PVC',
    'ألمنيوم وبي في سي',
    _slate,
  ),
  ServiceItem(Icons.fireplace, 'Chauffage', 'تدفئة', _red),
  ServiceItem(Icons.water_damage, 'Débouchage', 'تسليك المجاري', _blue),
  ServiceItem(Icons.water, 'Lavage de citernes', 'تنظيف الخزانات', _teal),
  ServiceItem(Icons.chair, 'Décoration', 'ديكور', _pink),
  ServiceItem(Icons.weekend, 'Montage de meubles', 'تركيب الأثاث', _amber),
  ServiceItem(Icons.curtains, 'Tapisserie et rideaux', 'تنجيد وستائر', _purple),
  ServiceItem(Icons.pool, 'Piscine', 'مسابح', _teal),
  ServiceItem(Icons.videocam, 'Caméras', 'كاميرات المراقبة', _slate),
  ServiceItem(
    Icons.satellite_alt,
    'Antenne et parabole',
    'هوائيات وصحون',
    _blue,
  ),
  ServiceItem(
    Icons.phone_android,
    'Réparation téléphone',
    'تصليح الهواتف',
    _purple,
  ),
  ServiceItem(Icons.pest_control, 'Désinsectisation', 'مكافحة الحشرات', _green),
  ServiceItem(
    Icons.dry_cleaning,
    'Canapés et tapis',
    'الأرائك والزرابي',
    _pink,
  ),
  ServiceItem(Icons.child_care, 'Garde d\'enfants', 'رعاية الأطفال', _pink),
  ServiceItem(Icons.elderly, 'Aide à domicile', 'مساعدة منزلية', _green),
  ServiceItem(Icons.school, 'Cours particuliers', 'دروس خصوصية', _purple),
  ServiceItem(
    Icons.content_cut,
    'Coiffure à domicile',
    'حلاقة في المنزل',
    _pink,
  ),
  ServiceItem(Icons.restaurant, 'Cuisinier et traiteur', 'طباخ وممون', _red),
  ServiceItem(Icons.photo_camera, 'Photographe', 'مصور', _slate),
  ServiceItem(
    Icons.inventory_2,
    'Transport de marchandises',
    'نقل البضائع',
    _amber,
  ),
  ServiceItem(Icons.car_crash, 'Carrosserie', 'هيكلة السيارات', _red),
  ServiceItem(Icons.local_car_wash, 'Lavage auto', 'غسل السيارات', _blue),
  ServiceItem(Icons.fire_truck, 'Dépannage auto', 'سحب السيارات', _red),
];

/// Faut-il animer ? Non si l'utilisateur a activé « Supprimer les animations ».
bool _animate(BuildContext context) =>
    !(MediaQuery.maybeOf(context)?.disableAnimations ?? false);

// ==========================================================================
//  Bulles de services qui flottent dans la zone d'accueil
// ==========================================================================
class _Spot {
  const _Spot(this.x, this.y, this.size, this.service, this.phase);

  final double x,
      y,
      size,
      phase; // x, y en fraction de la zone ; size en pixels
  final int service; // index dans kServices
}

// Disposées en couronne : le centre reste libre pour le titre.
const _spots = <_Spot>[
  _Spot(0.06, 0.06, 62, 0, 0.00), // plomberie
  _Spot(0.40, 0.00, 52, 1, 0.35), // électricité
  _Spot(0.74, 0.05, 66, 3, 0.70), // peinture
  _Spot(0.86, 0.33, 50, 2, 0.15), // climatisation
  _Spot(0.00, 0.36, 54, 5, 0.55), // menuiserie
  _Spot(0.83, 0.62, 58, 7, 0.90), // nettoyage
  _Spot(0.03, 0.70, 60, 21, 0.25), // aluminium
  _Spot(0.30, 0.84, 50, 8, 0.60), // jardinage
  _Spot(0.58, 0.80, 56, 29, 0.05), // caméras
  _Spot(0.20, 0.20, 40, 19, 0.80), // serrurerie
  _Spot(0.66, 0.24, 42, 14, 0.45), // carrelage
  _Spot(0.14, 0.52, 38, 34, 0.30), // garde d'enfants
  _Spot(0.72, 0.50, 40, 9, 0.65), // déménagement
];

class FloatingServices extends StatefulWidget {
  const FloatingServices({super.key});

  @override
  State<FloatingServices> createState() => _FloatingServicesState();
}

class _FloatingServicesState extends State<FloatingServices>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 9),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_animate(context)) {
      if (!_ctrl.isAnimating) _ctrl.repeat();
    } else {
      _ctrl.stop();
    }
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, box) {
        // zone trop petite (clavier ouvert) : on n'affiche que les grosses bulles
        final small = box.maxHeight < 260;
        final spots = small
            ? _spots.where((s) => s.size >= 56).toList()
            : _spots;
        final scale = (box.maxHeight / 360).clamp(0.6, 1.15);
        return RepaintBoundary(
          child: AnimatedBuilder(
            animation: _ctrl,
            builder: (context, _) {
              final t = _ctrl.value * 2 * math.pi;
              return Stack(
                clipBehavior: Clip.none,
                children: [
                  for (final s in spots)
                    Positioned(
                      left: s.x * (box.maxWidth - s.size * scale),
                      top: s.y * (box.maxHeight - s.size * scale),
                      child: Transform.translate(
                        offset: Offset(
                          math.cos(t + s.phase * 2 * math.pi) * 5,
                          math.sin(t * 2 + s.phase * 2 * math.pi) * 9,
                        ),
                        child: Transform.rotate(
                          angle: math.sin(t + s.phase * 6) * 0.08,
                          child: ServiceBubble(
                            kServices[s.service],
                            size: s.size * scale,
                          ),
                        ),
                      ),
                    ),
                ],
              );
            },
          ),
        );
      },
    );
  }
}

/// Pastille ronde colorée avec l'icône du service.
class ServiceBubble extends StatelessWidget {
  const ServiceBubble(this.service, {super.key, this.size = 56});

  final ServiceItem service;
  final double size;

  @override
  Widget build(BuildContext context) {
    final c = service.color;
    return Semantics(
      label: service.label(context),
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color.lerp(c, Colors.white, 0.25)!, c],
          ),
          border: Border.all(
            color: Colors.white.withValues(alpha: 0.85),
            width: 2.5,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.22),
              blurRadius: 14,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        child: Icon(service.icon, color: Colors.white, size: size * 0.5),
      ),
    );
  }
}

// ==========================================================================
//  Bandeau défilant avec tous les services
// ==========================================================================
class ServicesMarquee extends StatefulWidget {
  const ServicesMarquee({
    super.key,
    this.reverse = false,
    this.offset = 0,
    this.speed = 28,
  });

  /// Sens de défilement inversé (pour alterner deux bandeaux).
  final bool reverse;

  /// Décalage de départ dans la liste, pour que deux bandeaux ne montrent pas les mêmes services.
  final int offset;

  /// Vitesse en pixels par seconde.
  final double speed;

  @override
  State<ServicesMarquee> createState() => _ServicesMarqueeState();
}

class _ServicesMarqueeState extends State<ServicesMarquee>
    with SingleTickerProviderStateMixin {
  final _scroll = ScrollController();
  late final Ticker _ticker = createTicker(_tick);
  Duration _last = Duration.zero;

  void _tick(Duration elapsed) {
    final dt = (elapsed - _last).inMicroseconds / 1e6;
    _last = elapsed;
    if (_scroll.hasClients) _scroll.jumpTo(_scroll.offset + widget.speed * dt);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_animate(context)) {
      if (!_ticker.isActive) {
        _last = Duration.zero;
        _ticker.start();
      }
    } else if (_ticker.isActive) {
      _ticker.stop();
    }
  }

  @override
  void dispose() {
    _ticker.dispose();
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 40,
      child: ListView.builder(
        controller: _scroll,
        scrollDirection: Axis.horizontal,
        reverse: widget.reverse,
        physics: const NeverScrollableScrollPhysics(),
        padding: const EdgeInsets.symmetric(horizontal: 8),
        // liste « infinie » : on reboucle sur les 44 services
        itemBuilder: (context, i) {
          final s = kServices[(i + widget.offset) % kServices.length];
          return Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Container(
              padding: const EdgeInsets.fromLTRB(6, 4, 14, 4),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.16),
                borderRadius: BorderRadius.circular(30),
                border: Border.all(color: Colors.white.withValues(alpha: 0.28)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  CircleAvatar(
                    radius: 14,
                    backgroundColor: s.color,
                    child: Icon(s.icon, size: 16, color: Colors.white),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    s.label(context),
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
