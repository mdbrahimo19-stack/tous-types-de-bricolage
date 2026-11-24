import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../flavor.dart';
import '../l10n.dart';
import '../location.dart';
import '../state/session.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'client.dart' show PriceEstimateCard;
import 'points.dart';
import 'shared.dart';

// ==========================================================================
//  Fil des demandes disponibles (prestataire validé)
// ==========================================================================
class FeedScreen extends StatelessWidget {
  const FeedScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    return Scaffold(
      body: Column(children: [
        const _ProHeader(),
        Expanded(
          child: session.verificationStatus != 'approved'
              ? RefreshIndicator(
                  onRefresh: session.refreshUser,
                  child: EmptyState(
                    icon: Icons.hourglass_top,
                    text: context.tr(session.verificationStatus == 'rejected' ? 'rejected_provider' : 'not_verified'),
                    action: FilledButton(
                      onPressed: () =>
                          Navigator.push(context, MaterialPageRoute(builder: (_) => const ProviderSetupScreen())),
                      child: Text(context.tr('setup_profile')),
                    ),
                  ),
                )
              : LoadView<List<Json>>(
                  load: () => context.api.listAll('/api/feed/'),
                  builder: (context, items, reload) {
                    if (items.isEmpty) {
                      return Column(children: [
                        const _MissingGpsBanner(),
                        Expanded(
                          child: EmptyState(
                            icon: Icons.search_off,
                            text: context.tr('no_feed'),
                            action: TextButton(
                              onPressed: () => Navigator.push(
                                  context, MaterialPageRoute(builder: (_) => const ProviderSetupScreen())),
                              child: Text(context.tr('setup_profile')),
                            ),
                          ),
                        ),
                      ]);
                    }
                    return ListView.builder(
                      padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
                      itemCount: items.length + 2,
                      itemBuilder: (context, index) {
                        if (index == 0) return const _MissingGpsBanner();
                        if (index == 1) {
                          return Padding(
                            padding: const EdgeInsets.fromLTRB(4, 14, 4, 10),
                            child: Row(children: [
                              Expanded(
                                child: Text(context.tr('feed_title'),
                                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                              ),
                              _Tag(context.tr('n_requests', {'n': items.length}), AppPalette.success,
                                  AppPalette.successSoft),
                            ]),
                          );
                        }
                        final r = items[index - 2];
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: _FeedCard(
                            item: r,
                            onOpen: () async {
                              final sent = await Navigator.push<bool>(
                                context,
                                MaterialPageRoute(builder: (_) => FeedDetailScreen(item: r)),
                              );
                              if (sent == true) reload();
                            },
                          ),
                        );
                      },
                    );
                  },
                ),
        ),
      ]),
    );
  }
}

/// Bandeau bleu nuit de BRICOOL Pro : bonjour, bouton « Disponible », compteur de points.
class _ProHeader extends StatefulWidget {
  const _ProHeader();

  @override
  State<_ProHeader> createState() => _ProHeaderState();
}

class _ProHeaderState extends State<_ProHeader> {
  static const _soft = Color(0xFFC5D0E2); // texte secondaire sur fond bleu nuit
  Json? _points;
  bool? _available;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final api = context.api;
    try {
      final r = await Future.wait([api.get('/api/provider/points/'), api.get('/api/provider/me/')]);
      if (!mounted) return;
      setState(() {
        _points = (r[0] as Map).cast<String, dynamic>();
        _available = (r[1] as Map)['is_available'] != false;
      });
    } on ApiException {
      // hors ligne : le bandeau reste simple (bonjour seulement)
    }
  }

  Future<void> _toggleAvailable() async {
    final value = !(_available ?? true);
    setState(() => _available = value);
    try {
      await context.api.patch('/api/provider/me/', {'is_available': value});
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _available = !value);
      showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.current;
    final session = context.watch<Session>();
    final points = _points;
    final available = _available;
    return Container(
      color: p.primary,
      padding: EdgeInsets.fromLTRB(20, MediaQuery.paddingOf(context).top + 16, 20, 20),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(AppFlavor.name, style: const TextStyle(color: _soft, fontSize: 13)),
              Text(context.tr('hello', {'name': session.firstName}),
                  style: const TextStyle(color: Colors.white, fontSize: 21, fontWeight: FontWeight.w800)),
            ]),
          ),
          if (available != null)
            Material(
              color: Colors.white.withValues(alpha: 0.12),
              shape: const StadiumBorder(),
              child: InkWell(
                customBorder: const StadiumBorder(),
                onTap: _toggleAvailable,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Container(
                      width: 10,
                      height: 10,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: available ? const Color(0xFF3DD68C) : const Color(0xFFB0B8C4),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(context.tr(available ? 'available_short' : 'unavailable'),
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 13)),
                  ]),
                ),
              ),
            ),
        ]),
        if (points != null) ...[
          const SizedBox(height: 16),
          _pointsCard(points),
        ],
      ]),
    );
  }

  Widget _pointsCard(Json points) {
    final due = (toNum(points['points_due']) ?? 0).toInt();
    final max = (toNum(points['block_at']) ?? 200).toInt();
    final free = (toNum(points['free_points']) ?? 0).toInt();
    final blocked = points['blocked'] == true;
    return Material(
      color: Colors.white.withValues(alpha: 0.08),
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: () async {
          await Navigator.push(context, MaterialPageRoute(builder: (_) => const PointsScreen()));
          _load();
        },
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text(context.tr('points_title'), style: const TextStyle(color: _soft, fontSize: 13))),
              const Icon(Icons.chevron_right, color: _soft, size: 20),
            ]),
            Row(crossAxisAlignment: CrossAxisAlignment.baseline, textBaseline: TextBaseline.alphabetic, children: [
              Text('$due', style: const TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.w800)),
              const SizedBox(width: 6),
              Expanded(
                child: Text(context.tr('pro_points_line', {'max': max}),
                    style: const TextStyle(color: _soft, fontSize: 13)),
              ),
            ]),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: max > 0 ? (due / max).clamp(0, 1).toDouble() : 0,
                minHeight: 8,
                backgroundColor: Colors.white.withValues(alpha: 0.15),
                color: blocked ? const Color(0xFFFF8A7A) : const Color(0xFFF2A03D),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              blocked ? context.tr('points_blocked') : context.tr('pro_free_left', {'n': free}),
              style: TextStyle(color: blocked ? const Color(0xFFFFB4A8) : _soft, fontSize: 12.5),
            ),
          ]),
        ),
      ),
    );
  }
}

/// Une demande proche : urgence, métier, titre, description, distance, bouton.
class _FeedCard extends StatelessWidget {
  const _FeedCard({required this.item, required this.onOpen});

  final Json item;
  final VoidCallback onOpen;

  static const _urgencyColors = {
    'immediate': (Color(0xFF9A2B12), Color(0xFFFCE7E1)),
    'today': (Color(0xFF8A3D06), Color(0xFFFDEBDD)),
    'this_week': (Color(0xFF7A4A06), Color(0xFFFCEFD9)),
  };

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.current;
    final r = item;
    final urgency = '${r['urgency']}';
    final (urgFg, urgBg) = _urgencyColors[urgency] ?? (p.muted, const Color(0xFFEDF0F5));
    final distance = toNum(r['distance_km']);
    final quoted = r['already_quoted'] == true;
    final description = '${r['description'] ?? ''}'.trim();
    final hasBudget = r['budget_min'] != null || r['budget_max'] != null;
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onOpen,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Wrap(spacing: 8, runSpacing: 6, children: [
              _Tag(context.tr('urg_$urgency'), urgFg, urgBg),
              _Tag(context.nameOf(r['category_detail'] as Map?), p.muted, const Color(0xFFEDF0F5)),
              if (quoted) _Tag(context.tr('already_quoted'), AppPalette.success, AppPalette.successSoft),
            ]),
            const SizedBox(height: 10),
            Text('${r['title']}', style: const TextStyle(fontSize: 15.5, fontWeight: FontWeight.w700)),
            if (description.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(description,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 13, color: p.muted, height: 1.45)),
            ],
            const SizedBox(height: 10),
            Wrap(spacing: 14, runSpacing: 4, children: [
              Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(Icons.place_outlined, size: 16, color: p.muted),
                const SizedBox(width: 4),
                Text(
                  '${r['commune_name'] ?? ''}'
                  '${distance != null ? ' · ${context.tr('km_away', {'n': distance.toStringAsFixed(1)})}' : ''}',
                  style: TextStyle(fontSize: 12.5, color: p.muted),
                ),
              ]),
              if (hasBudget)
                Row(mainAxisSize: MainAxisSize.min, children: [
                  Icon(Icons.payments_outlined, size: 16, color: p.muted),
                  const SizedBox(width: 4),
                  Text(budgetRange(context, r['budget_min'], r['budget_max']),
                      style: TextStyle(fontSize: 12.5, color: p.muted)),
                ]),
            ]),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: quoted
                  ? OutlinedButton(onPressed: onOpen, child: Text(context.tr('see_request')))
                  : FilledButton(onPressed: onOpen, child: Text(context.tr('send_quote'))),
            ),
          ]),
        ),
      ),
    );
  }
}

/// Petite étiquette colorée (urgence, métier, « Devis envoyé »…).
class _Tag extends StatelessWidget {
  const _Tag(this.text, this.fg, this.bg);

  final String text;
  final Color fg;
  final Color bg;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(8)),
      child: Text(text, style: TextStyle(color: fg, fontSize: 11.5, fontWeight: FontWeight.w700)),
    );
  }
}

/// Rappel affiché dans le fil tant que le bricoleur n'a pas enregistré sa position de travail.
class _MissingGpsBanner extends StatefulWidget {
  const _MissingGpsBanner();

  @override
  State<_MissingGpsBanner> createState() => _MissingGpsBannerState();
}

class _MissingGpsBannerState extends State<_MissingGpsBanner> {
  late final Future<bool> _hasGps = context.api
      .get('/api/provider/me/')
      .then((p) => (p as Map)['latitude'] != null && p['longitude'] != null)
      .catchError((_) => true);
  late final Future<bool> _blocked = context.api
      .get('/api/provider/points/')
      .then((p) => (p as Map)['blocked'] == true)
      .catchError((_) => false);

  @override
  Widget build(BuildContext context) {
    return Column(mainAxisSize: MainAxisSize.min, children: [
      FutureBuilder<bool>(
        future: _blocked,
        builder: (context, snap) {
          if (snap.data != true) return const SizedBox.shrink();
          final scheme = Theme.of(context).colorScheme;
          return Card(
            color: scheme.errorContainer,
            margin: const EdgeInsets.fromLTRB(12, 12, 12, 4),
            child: ListTile(
              leading: Icon(Icons.lock, color: scheme.onErrorContainer),
              title: Text(context.tr('points_blocked'), style: TextStyle(color: scheme.onErrorContainer)),
              subtitle: Text(context.tr('pay_title'), style: TextStyle(color: scheme.onErrorContainer)),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const PointsScreen())),
            ),
          );
        },
      ),
      _gpsBanner(),
    ]);
  }

  Widget _gpsBanner() {
    return FutureBuilder<bool>(
      future: _hasGps,
      builder: (context, snap) {
        if (snap.data != false) return const SizedBox.shrink();
        final scheme = Theme.of(context).colorScheme;
        return Card(
          color: scheme.tertiaryContainer,
          margin: const EdgeInsets.fromLTRB(12, 12, 12, 4),
          child: ListTile(
            leading: Icon(Icons.location_off, color: scheme.onTertiaryContainer),
            title: Text(context.tr('feed_no_gps'), style: TextStyle(color: scheme.onTertiaryContainer)),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ProviderSetupScreen())),
          ),
        );
      },
    );
  }
}

class FeedDetailScreen extends StatefulWidget {
  const FeedDetailScreen({super.key, required this.item});

  final Json item;

  @override
  State<FeedDetailScreen> createState() => _FeedDetailScreenState();
}

class _FeedDetailScreenState extends State<FeedDetailScreen> {
  final _form = GlobalKey<FormState>();
  final _amount = TextEditingController();
  final _leadTime = TextEditingController(text: '1');
  final _duration = TextEditingController();
  final _message = TextEditingController();
  Json? _estimate;
  bool _estimating = false;
  bool _sending = false;

  Json get r => widget.item;

  Future<void> _priceHelp() async {
    setState(() => _estimating = true);
    try {
      final data = await context.api.post('/api/ai/price-estimate/', {
        'category': r['category'],
        'description': '${r['title']}\n${r['description']}',
        'urgency': r['urgency'],
        'language': context.isArabic ? 'ar' : 'fr',
      });
      if (mounted) setState(() => _estimate = (data as Map).cast<String, dynamic>());
    } catch (e) {
      if (mounted) {
        showError(context, e is ApiException && e.isUnavailable ? ApiException(context.tr('ai_unavailable')) : e);
      }
    } finally {
      if (mounted) setState(() => _estimating = false);
    }
  }

  Future<void> _send() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _sending = true);
    final ok = await runAction(
      context,
      () => context.api.post('/api/quotes/', {
        'request': r['id'],
        'amount': toNum(_amount.text),
        'lead_time_days': int.tryParse(_leadTime.text) ?? 1,
        'estimated_duration': _duration.text.trim(),
        'message': _message.text.trim(),
      }),
    );
    if (!mounted) return;
    setState(() => _sending = false);
    if (ok) {
      showInfo(context, context.tr('quote_sent'));
      Navigator.pop(context, true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final photos = (r['photos'] as List? ?? const []).cast<Map>();
    final quoted = r['already_quoted'] == true;
    return Scaffold(
      appBar: AppBar(),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text('${r['title']}', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Wrap(spacing: 12, runSpacing: 6, children: [
              UrgencyChip('${r['urgency']}'),
              Text(context.nameOf(r['category_detail'] as Map?)),
              Text('${r['commune_name']}, ${r['wilaya_name']}'),
            ]),
            const SizedBox(height: 12),
            Text('${r['description']}'),
            if (r['budget_min'] != null || r['budget_max'] != null) ...[
              const SizedBox(height: 8),
              Text(context.tr('budget_range', {'range': budgetRange(context, r['budget_min'], r['budget_max'])}),
                  style: const TextStyle(fontWeight: FontWeight.w600)),
            ],
            if (photos.isNotEmpty) ...[
              const SizedBox(height: 12),
              SizedBox(
                height: 120,
                child: ListView(scrollDirection: Axis.horizontal, children: [
                  for (final p in photos)
                    Padding(
                      padding: const EdgeInsetsDirectional.only(end: 8),
                      child: NetImage(p['image'] as String?, size: 120),
                    ),
                ]),
              ),
            ],
            const Divider(height: 32),
            if (quoted)
              ListTile(
                leading: const Icon(Icons.check_circle, color: Colors.green),
                title: Text(context.tr('already_quoted')),
                trailing: TextButton(
                  onPressed: () => openConversation(context, requestId: r['id'] as int),
                  child: Text(context.tr('chat')),
                ),
              )
            else ...[
              Text(context.tr('send_quote'), style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed: _estimating ? null : _priceHelp,
                icon: _estimating
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.auto_awesome),
                label: Text(context.tr('price_help')),
              ),
              if (_estimate != null) PriceEstimateCard(estimate: _estimate!),
              const SizedBox(height: 12),
              TextFormField(
                controller: _amount,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(labelText: context.tr('amount_da')),
                validator: (v) => (toNum(v) ?? 0) <= 0 ? context.tr('required') : null,
              ),
              const SizedBox(height: 8),
              TextFormField(
                controller: _leadTime,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(labelText: context.tr('lead_time')),
              ),
              const SizedBox(height: 8),
              TextFormField(controller: _duration, decoration: InputDecoration(labelText: context.tr('duration'))),
              const SizedBox(height: 8),
              TextFormField(
                controller: _message,
                minLines: 2,
                maxLines: 5,
                decoration: InputDecoration(labelText: context.tr('message')),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: _sending ? null : _send,
                child: _sending
                    ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2))
                    : Text(context.tr('send_quote')),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// ==========================================================================
//  Mes devis envoyés
// ==========================================================================
class MyQuotesScreen extends StatelessWidget {
  const MyQuotesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final me = context.read<Session>().userId;
    return Scaffold(
      appBar: AppBar(title: Text(context.tr('my_quotes'))),
      body: LoadView<List<Json>>(
        load: () async => (await context.api.listAll('/api/quotes/')).where((q) => q['provider'] == me).toList(),
        builder: (context, quotes, reload) {
          if (quotes.isEmpty) return EmptyState(icon: Icons.request_quote_outlined, text: context.tr('no_quotes_sent'));
          return ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: quotes.length,
            itemBuilder: (context, i) {
              final q = quotes[i];
              final status = '${q['status']}';
              return Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      Expanded(
                        child: Text('${q['request_title'] ?? '#${q['request']}'}',
                            style: const TextStyle(fontWeight: FontWeight.bold)),
                      ),
                      StatusChip(status: status, prefix: 'qs'),
                    ]),
                    const SizedBox(height: 6),
                    Text('${money(context, q['amount'])} · ${context.tr('lead_time_days', {'n': q['lead_time_days']})}'),
                    Text(formatDate(context, q['created_at']), style: const TextStyle(fontSize: 12)),
                    Row(mainAxisAlignment: MainAxisAlignment.end, children: [
                      TextButton.icon(
                        icon: const Icon(Icons.chat_bubble_outline),
                        label: Text(context.tr('chat')),
                        onPressed: () => openConversation(context, requestId: q['request'] as int),
                      ),
                      if (status == 'sent')
                        TextButton(
                          onPressed: () async {
                            if (!await confirmDialog(context, context.tr('withdraw_confirm'))) return;
                            if (!context.mounted) return;
                            final ok = await runAction(
                                context, () => context.api.post('/api/quotes/${q['id']}/withdraw/'));
                            if (ok) reload();
                          },
                          child: Text(context.tr('withdraw'), style: const TextStyle(color: Colors.red)),
                        ),
                    ]),
                  ]),
                ),
              );
            },
          );
        },
      ),
    );
  }
}

// ==========================================================================
//  Profil prestataire : zone, catégories, présentation
// ==========================================================================
const _legalStatuses = ['non_declare', 'auto_entrepreneur', 'artisan', 'entreprise'];

class ProviderSetupScreen extends StatefulWidget {
  const ProviderSetupScreen({super.key});

  @override
  State<ProviderSetupScreen> createState() => _ProviderSetupScreenState();
}

class _ProviderSetupScreenState extends State<ProviderSetupScreen> {
  final _businessName = TextEditingController();
  final _bio = TextEditingController();
  final _years = TextEditingController();
  String _legal = 'non_declare';
  bool _available = true;
  int? _baseWilaya;
  Set<int> _communes = {};
  double? _lat; // position de travail (GPS) : les demandes proches arrivent en priorité
  double? _lng;
  int _radius = 10;
  bool _locating = false;
  String _verification = 'pending';
  List<Json> _categories = [];
  List<Json> _wilayas = [];
  List<Json> _wilayaCommunes = [];
  bool _loading = true;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final api = context.api;
    try {
      final results = await Future.wait([
        api.get('/api/provider/me/'),
        api.listAll('/api/provider/categories/'),
        Refs.wilayas(api),
      ]);
      final p = (results[0] as Map).cast<String, dynamic>();
      _businessName.text = '${p['business_name'] ?? ''}';
      _bio.text = '${p['bio'] ?? ''}';
      _years.text = '${p['years_experience'] ?? 0}';
      _legal = _legalStatuses.contains(p['legal_status']) ? p['legal_status'] as String : 'non_declare';
      _available = p['is_available'] != false;
      _baseWilaya = p['base_wilaya'] as int?;
      _communes = ((p['service_communes'] as List?) ?? const []).cast<int>().toSet();
      _lat = toNum(p['latitude'])?.toDouble();
      _lng = toNum(p['longitude'])?.toDouble();
      _radius = (toNum(p['radius_km'])?.toInt() ?? 10).clamp(1, 50);
      _verification = '${p['verification_status'] ?? 'pending'}';
      _categories = results[1] as List<Json>;
      _wilayas = results[2] as List<Json>;
      _baseWilaya ??= _wilayas.length == 1 ? _wilayas.first['id'] as int : null;
      if (_baseWilaya != null) _wilayaCommunes = await Refs.communes(api, _baseWilaya!);
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _changeWilaya(int? id) async {
    setState(() {
      _baseWilaya = id;
      _wilayaCommunes = [];
    });
    if (id != null) {
      final list = await Refs.communes(context.api, id);
      if (mounted) setState(() => _wilayaCommunes = list);
    }
  }

  Future<void> _takePosition() async {
    setState(() => _locating = true);
    try {
      final fix = await currentPosition();
      if (mounted) {
        setState(() {
          _lat = round6(fix.latitude);
          _lng = round6(fix.longitude);
        });
      }
    } on GpsException catch (e) {
      if (mounted) showInfo(context, context.tr(e.l10nKey));
    } finally {
      if (mounted) setState(() => _locating = false);
    }
  }

  Future<void> _pickCommunes() async {
    final selected = {..._communes};
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) => DraggableScrollableSheet(
          expand: false,
          initialChildSize: 0.8,
          builder: (ctx, scroll) => Column(children: [
            Expanded(
              child: ListView(controller: scroll, children: [
                for (final c in _wilayaCommunes)
                  CheckboxListTile(
                    value: selected.contains(c['id']),
                    title: Text(ctx.nameOf(c)),
                    onChanged: (v) => setLocal(() => v == true ? selected.add(c['id'] as int) : selected.remove(c['id'])),
                  ),
              ]),
            ),
            SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(ctx.tr('ok'))),
              ),
            ),
          ]),
        ),
      ),
    );
    if (ok == true) setState(() => _communes = selected);
  }

  Future<void> _addCategory() async {
    final c = await pickCategory(context);
    if (c == null || !mounted) return;
    final ok = await runAction(context, () => context.api.post('/api/provider/categories/', {'category': c['id']}));
    if (ok && mounted) {
      final list = await context.api.listAll('/api/provider/categories/');
      if (mounted) setState(() => _categories = list);
    }
  }

  Future<void> _removeCategory(Json pc) async {
    final ok = await runAction(context, () => context.api.delete('/api/provider/categories/${pc['id']}/'));
    if (ok && mounted) setState(() => _categories.remove(pc));
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    final session = context.read<Session>();
    final ok = await runAction(context, () async {
      await context.api.patch('/api/provider/me/', {
        'business_name': _businessName.text.trim(),
        'bio': _bio.text.trim(),
        'years_experience': int.tryParse(_years.text) ?? 0,
        'legal_status': _legal,
        'is_available': _available,
        'base_wilaya': _baseWilaya,
        'service_communes': _communes.toList(),
        'radius_km': _radius,
        if (_lat != null && _lng != null) ...{'latitude': _lat, 'longitude': _lng},
      });
      await session.refreshUser();
    });
    if (!mounted) return;
    setState(() => _saving = false);
    if (ok) showInfo(context, context.tr('saved'));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(context.tr('provider_profile'))),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.verified_user_outlined),
                  title: Text(context.tr('verification')),
                  trailing: StatusChip(status: _verification, prefix: 'vs'),
                ),
                SectionTitle(context.tr('my_categories', {'n': _categories.length})),
                Wrap(spacing: 8, runSpacing: 4, children: [
                  for (final pc in _categories)
                    InputChip(
                      label: Text(context.nameOf(pc['category_detail'] as Map?)),
                      onDeleted: () => _removeCategory(pc),
                    ),
                  if (_categories.length < 5)
                    ActionChip(
                      avatar: const Icon(Icons.add, size: 18),
                      label: Text(context.tr('add_category')),
                      onPressed: _addCategory,
                    ),
                ]),
                SectionTitle(context.tr('work_zone')),
                Text(context.tr('work_zone_sub'), style: Theme.of(context).textTheme.bodySmall),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(_lat != null ? Icons.my_location : Icons.location_off,
                      color: _lat != null ? Theme.of(context).colorScheme.primary : null),
                  title: Text(context.tr(_lat != null ? 'work_pos_set' : 'work_pos_missing')),
                  subtitle: _lat != null ? Text('${_lat!.toStringAsFixed(4)}, ${_lng!.toStringAsFixed(4)}') : null,
                ),
                OutlinedButton.icon(
                  onPressed: _locating ? null : _takePosition,
                  icon: _locating
                      ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.gps_fixed),
                  label: Text(context.tr('work_pos_update')),
                ),
                const SizedBox(height: 8),
                Text(context.tr('work_radius', {'n': _radius})),
                Slider(
                  value: _radius.toDouble(),
                  min: 1,
                  max: 50,
                  divisions: 49,
                  label: '$_radius km',
                  onChanged: (v) => setState(() => _radius = v.round()),
                ),
                SectionTitle(context.tr('base_wilaya')),
                DropdownButtonFormField<int>(
                  initialValue: _baseWilaya,
                  isExpanded: true,
                  items: [
                    for (final w in _wilayas)
                      DropdownMenuItem(value: w['id'] as int, child: Text('${w['code']} · ${context.nameOf(w)}')),
                  ],
                  onChanged: _changeWilaya,
                ),
                const SizedBox(height: 8),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.map_outlined),
                  title: Text(context.tr('service_communes', {'n': _communes.length})),
                  subtitle: Text(
                    _wilayaCommunes.where((c) => _communes.contains(c['id'])).map(context.nameOf).join(', '),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  trailing: const Icon(Icons.edit),
                  onTap: _baseWilaya == null ? null : _pickCommunes,
                ),
                SectionTitle(context.tr('profile')),
                TextField(controller: _businessName, decoration: InputDecoration(labelText: context.tr('business_name'))),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  initialValue: _legal,
                  decoration: InputDecoration(labelText: context.tr('legal_status')),
                  items: [
                    for (final s in _legalStatuses) DropdownMenuItem(value: s, child: Text(context.tr('ls_$s'))),
                  ],
                  onChanged: (v) => setState(() => _legal = v ?? _legal),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _years,
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(labelText: context.tr('years_experience')),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _bio,
                  minLines: 3,
                  maxLines: 6,
                  decoration: InputDecoration(labelText: context.tr('bio')),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  value: _available,
                  onChanged: (v) => setState(() => _available = v),
                  title: Text(context.tr('available')),
                ),
                const SizedBox(height: 12),
                FilledButton(
                  onPressed: _saving ? null : _save,
                  child: _saving
                      ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2))
                      : Text(context.tr('save')),
                ),
                const SizedBox(height: 24),
              ],
            ),
    );
  }
}
