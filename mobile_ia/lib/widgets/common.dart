import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../config.dart';
import '../l10n.dart';
import '../state/session.dart';

extension ApiAccess on BuildContext {
  ApiClient get api => read<Session>().api;
  Session get session => read<Session>();
}

// ==========================================================================
//  Formats
// ==========================================================================
num? toNum(dynamic v) => v == null ? null : (v is num ? v : num.tryParse('$v'));

String money(BuildContext context, dynamic v) {
  final n = toNum(v);
  if (n == null) return '—';
  final f = NumberFormat.decimalPattern(context.isArabic ? 'ar_DZ' : 'fr');
  return '${f.format(n.round())} ${context.tr('da')}';
}

String budgetRange(BuildContext context, dynamic min, dynamic max) {
  if (toNum(min) == null && toNum(max) == null) return '—';
  if (toNum(min) == null) return '≤ ${money(context, max)}';
  if (toNum(max) == null) return '≥ ${money(context, min)}';
  return '${money(context, min)} – ${money(context, max)}';
}

String formatDate(BuildContext context, dynamic iso, {bool withTime = true}) {
  if (iso == null) return '—';
  final d = DateTime.tryParse('$iso')?.toLocal();
  if (d == null) return '—';
  final loc = context.isArabic ? 'ar' : 'fr';
  return withTime ? DateFormat.yMMMd(loc).add_Hm().format(d) : DateFormat.yMMMd(loc).format(d);
}

// ==========================================================================
//  Dialogues / messages
// ==========================================================================
void showError(BuildContext context, Object error) {
  final msg = error is ApiException ? error.message : context.tr('error_generic');
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(msg), backgroundColor: Theme.of(context).colorScheme.error));
}

void showInfo(BuildContext context, String msg) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(msg)));
}

Future<bool> confirmDialog(BuildContext context, String message) async {
  final ok = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      content: Text(message),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(ctx.tr('cancel'))),
        FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(ctx.tr('confirm'))),
      ],
    ),
  );
  return ok ?? false;
}

/// Exécute une action réseau avec gestion d'erreur ; renvoie true si elle a réussi.
Future<bool> runAction(BuildContext context, Future<void> Function() action) async {
  try {
    await action();
    return true;
  } catch (e) {
    if (context.mounted) showError(context, e);
    return false;
  }
}

// ==========================================================================
//  Chargement asynchrone avec erreur + « tirer pour rafraîchir »
// ==========================================================================
class LoadView<T> extends StatefulWidget {
  const LoadView({super.key, required this.load, required this.builder});

  final Future<T> Function() load;
  final Widget Function(BuildContext context, T data, Future<void> Function() reload) builder;

  @override
  State<LoadView<T>> createState() => LoadViewState<T>();
}

class LoadViewState<T> extends State<LoadView<T>> {
  late Future<T> _future = widget.load();

  Future<void> reload() async {
    final f = widget.load();
    setState(() => _future = f);
    try {
      await f;
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<T>(
      future: _future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snap.hasError) {
          final e = snap.error;
          return EmptyState(
            icon: Icons.cloud_off,
            text: e is ApiException ? e.message : context.tr('error_generic'),
            action: FilledButton.tonal(onPressed: reload, child: Text(context.tr('retry'))),
          );
        }
        return RefreshIndicator(onRefresh: reload, child: widget.builder(context, snap.data as T, reload));
      },
    );
  }
}

class EmptyState extends StatelessWidget {
  const EmptyState({super.key, required this.icon, required this.text, this.action});

  final IconData icon;
  final String text;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    // ListView pour que le « tirer pour rafraîchir » fonctionne même sur un écran vide
    return ListView(
      padding: const EdgeInsets.all(32),
      children: [
        const SizedBox(height: 60),
        Icon(icon, size: 56, color: Theme.of(context).colorScheme.outline),
        const SizedBox(height: 16),
        Text(text, textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodyLarge),
        if (action != null) ...[const SizedBox(height: 16), Center(child: action)],
      ],
    );
  }
}

// ==========================================================================
//  Badges de statut
// ==========================================================================
Color statusColor(String status) {
  switch (status) {
    case 'published':
    case 'sent':
    case 'planned':
      return Colors.blue;
    case 'quotes_received':
    case 'confirmed':
      return Colors.indigo;
    case 'assigned':
    case 'in_progress':
      return Colors.orange;
    case 'completed':
    case 'accepted':
    case 'paid':
    case 'evaluated':
    case 'approved':
      return Colors.green;
    case 'cancelled':
    case 'rejected':
    case 'expired':
    case 'withdrawn':
      return Colors.red;
    default:
      return Colors.grey;
  }
}

class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.status, required this.prefix});

  /// prefix : 'rs' (demande), 'qs' (devis), 'ms' (mission), 'vs' (vérification)
  final String status;
  final String prefix;

  @override
  Widget build(BuildContext context) {
    final color = statusColor(status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
      child: Text(
        context.tr('${prefix}_$status'),
        style: TextStyle(color: color, fontWeight: FontWeight.w600, fontSize: 12),
      ),
    );
  }
}

class UrgencyChip extends StatelessWidget {
  const UrgencyChip(this.urgency, {super.key});

  final String urgency;

  @override
  Widget build(BuildContext context) {
    final urgent = urgency == 'immediate' || urgency == 'today';
    return Row(mainAxisSize: MainAxisSize.min, children: [
      Icon(urgent ? Icons.bolt : Icons.schedule, size: 16, color: urgent ? Colors.red : Colors.grey),
      const SizedBox(width: 4),
      Text(context.tr('urg_$urgency'), style: TextStyle(color: urgent ? Colors.red : null, fontSize: 13)),
    ]);
  }
}

// ==========================================================================
//  Réglage de l'adresse du serveur (accessible avant et après connexion)
// ==========================================================================
Future<void> showServerDialog(BuildContext context) {
  return showDialog<void>(context: context, builder: (_) => const _ServerDialog());
}

class _ServerDialog extends StatefulWidget {
  const _ServerDialog();

  @override
  State<_ServerDialog> createState() => _ServerDialogState();
}

class _ServerDialogState extends State<_ServerDialog> {
  late final _url = TextEditingController(text: ServerConfig.baseUrl);
  bool _testing = false;
  bool? _reachable;

  Future<void> _test() async {
    setState(() {
      _testing = true;
      _reachable = null;
    });
    final ok = await context.api.ping(ServerConfig.normalize(_url.text));
    if (mounted) {
      setState(() {
        _testing = false;
        _reachable = ok;
      });
    }
  }

  Future<void> _save() async {
    await ServerConfig.save(_url.text);
    if (!mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    final saved = context.tr('server_saved');
    Navigator.pop(context);
    messenger.showSnackBar(SnackBar(content: Text(saved)));
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(context.tr('server')),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: _url,
            keyboardType: TextInputType.url,
            autocorrect: false,
            decoration: InputDecoration(labelText: context.tr('server_url'), helperText: context.tr('server_help'), helperMaxLines: 2),
            onChanged: (_) => setState(() => _reachable = null),
          ),
          const SizedBox(height: 12),
          if (_testing)
            const Center(child: SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2)))
          else if (_reachable != null)
            Text(
              context.tr(_reachable! ? 'server_ok' : 'server_ko'),
              style: TextStyle(color: _reachable! ? Colors.green.shade700 : Theme.of(context).colorScheme.error),
            ),
        ],
      ),
      actions: [
        TextButton(onPressed: _testing ? null : _test, child: Text(context.tr('server_test'))),
        TextButton(onPressed: () => Navigator.pop(context), child: Text(context.tr('cancel'))),
        FilledButton(onPressed: _save, child: Text(context.tr('save'))),
      ],
    );
  }
}

class NetImage extends StatelessWidget {
  const NetImage(this.url, {super.key, this.size = 90});

  final String? url;
  final double size;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(10),
      child: url == null
          ? SizedBox(width: size, height: size)
          : Image.network(
              url!,
              width: size,
              height: size,
              fit: BoxFit.cover,
              errorBuilder: (_, _, _) =>
                  SizedBox(width: size, height: size, child: const Icon(Icons.broken_image_outlined)),
            ),
    );
  }
}

// ==========================================================================
//  Référentiels (catalogue, wilayas, communes) — mis en cache en mémoire
// ==========================================================================
class Refs {
  static List<Json>? _categories;
  static List<Json>? _wilayas;
  static final Map<int, List<Json>> _communes = {};

  /// Catégories racines avec leurs prestations (`children`).
  static Future<List<Json>> categories(ApiClient api) async =>
      _categories ??= await api.listAll('/api/categories/');

  static Future<Json?> categoryById(ApiClient api, int? id) async {
    if (id == null) return null;
    for (final root in await categories(api)) {
      if (root['id'] == id) return root;
      for (final child in (root['children'] as List? ?? const [])) {
        if ((child as Map)['id'] == id) return child.cast<String, dynamic>();
      }
    }
    return null;
  }

  static Future<List<Json>> wilayas(ApiClient api) async =>
      _wilayas ??= await api.listAll('/api/wilayas/', query: {'is_active': 'true'});

  static Future<List<Json>> communes(ApiClient api, int wilayaId) async =>
      _communes[wilayaId] ??= await api.listAll('/api/communes/', query: {'wilaya': '$wilayaId'});
}

/// Sélecteur de catégorie (familles -> prestations) en feuille modale.
Future<Json?> pickCategory(BuildContext context) async {
  final api = context.api;
  return showModalBottomSheet<Json>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (ctx) => DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.75,
      builder: (ctx, scroll) => FutureBuilder<List<Json>>(
        future: Refs.categories(api),
        builder: (ctx, snap) {
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          return ListView(
            controller: scroll,
            children: [
              for (final root in snap.data!)
                ExpansionTile(
                  title: Text(ctx.nameOf(root), style: const TextStyle(fontWeight: FontWeight.w600)),
                  children: [
                    for (final child in (root['children'] as List? ?? const []))
                      ListTile(
                        title: Text(ctx.nameOf(child as Map)),
                        onTap: () => Navigator.pop(ctx, child.cast<String, dynamic>()),
                      ),
                    if ((root['children'] as List? ?? const []).isEmpty)
                      ListTile(title: Text(ctx.nameOf(root)), onTap: () => Navigator.pop(ctx, root)),
                  ],
                ),
            ],
          );
        },
      ),
    ),
  );
}

/// Champs wilaya + commune liés.
class LocationFields extends StatefulWidget {
  const LocationFields({
    super.key,
    this.wilayaId,
    this.communeId,
    required this.onChanged,
  });

  final int? wilayaId;
  final int? communeId;
  final void Function(int? wilayaId, int? communeId) onChanged;

  @override
  State<LocationFields> createState() => _LocationFieldsState();
}

class _LocationFieldsState extends State<LocationFields> {
  List<Json> _wilayas = [];
  List<Json> _communes = [];
  int? _wilaya;
  int? _commune;

  @override
  void initState() {
    super.initState();
    _wilaya = widget.wilayaId;
    _commune = widget.communeId;
    _loadWilayas();
  }

  Future<void> _loadWilayas() async {
    try {
      final list = await Refs.wilayas(context.api);
      if (!mounted) return;
      setState(() => _wilayas = list);
      if (_wilaya == null && list.length == 1) _selectWilaya(list.first['id'] as int);
      if (_wilaya != null) await _loadCommunes(_wilaya!);
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  Future<void> _loadCommunes(int wilayaId) async {
    final list = await Refs.communes(context.api, wilayaId);
    if (mounted) setState(() => _communes = list);
  }

  void _selectWilaya(int? id) {
    setState(() {
      _wilaya = id;
      _commune = null;
      _communes = [];
    });
    widget.onChanged(_wilaya, null);
    if (id != null) _loadCommunes(id);
  }

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      DropdownButtonFormField<int>(
        initialValue: _wilayas.any((w) => w['id'] == _wilaya) ? _wilaya : null,
        isExpanded: true,
        decoration: InputDecoration(labelText: context.tr('wilaya')),
        items: [
          for (final w in _wilayas)
            DropdownMenuItem(value: w['id'] as int, child: Text('${w['code']} · ${context.nameOf(w)}')),
        ],
        onChanged: _selectWilaya,
        validator: (v) => v == null ? context.tr('required') : null,
      ),
      const SizedBox(height: 12),
      DropdownButtonFormField<int>(
        key: ValueKey(_wilaya),
        initialValue: _communes.any((c) => c['id'] == _commune) ? _commune : null,
        isExpanded: true,
        decoration: InputDecoration(labelText: context.tr('commune')),
        items: [
          for (final c in _communes) DropdownMenuItem(value: c['id'] as int, child: Text(context.nameOf(c))),
        ],
        onChanged: (v) {
          setState(() => _commune = v);
          widget.onChanged(_wilaya, v);
        },
        validator: (v) => v == null ? context.tr('required') : null,
      ),
    ]);
  }
}

class SectionTitle extends StatelessWidget {
  const SectionTitle(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 20, bottom: 8),
        child: Text(text, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
      );
}
