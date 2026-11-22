import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../l10n.dart';
import '../state/session.dart';
import '../widgets/common.dart';
import 'client.dart' show PriceEstimateCard;
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
      appBar: AppBar(title: Text(context.tr('feed_title'))),
      body: session.verificationStatus != 'approved'
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
                  return EmptyState(
                    icon: Icons.search_off,
                    text: context.tr('no_feed'),
                    action: TextButton(
                      onPressed: () =>
                          Navigator.push(context, MaterialPageRoute(builder: (_) => const ProviderSetupScreen())),
                      child: Text(context.tr('setup_profile')),
                    ),
                  );
                }
                return ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: items.length,
                  itemBuilder: (context, i) {
                    final r = items[i];
                    final distance = toNum(r['distance_km']);
                    return Card(
                      child: InkWell(
                        borderRadius: BorderRadius.circular(12),
                        onTap: () async {
                          final sent = await Navigator.push<bool>(
                            context,
                            MaterialPageRoute(builder: (_) => FeedDetailScreen(item: r)),
                          );
                          if (sent == true) reload();
                        },
                        child: Padding(
                          padding: const EdgeInsets.all(14),
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Row(children: [
                              Expanded(
                                child: Text('${r['title']}',
                                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                              ),
                              if (r['for_me'] == true)
                                Padding(
                                  padding: const EdgeInsetsDirectional.only(start: 6),
                                  child: Chip(
                                    avatar: const Icon(Icons.person_pin, size: 18),
                                    label: Text(context.tr('for_you')),
                                    visualDensity: VisualDensity.compact,
                                    backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                                  ),
                                ),
                              if (r['already_quoted'] == true)
                                Chip(
                                  label: Text(context.tr('already_quoted')),
                                  visualDensity: VisualDensity.compact,
                                ),
                            ]),
                            const SizedBox(height: 4),
                            Text(context.nameOf(r['category_detail'] as Map?)),
                            const SizedBox(height: 6),
                            Wrap(spacing: 12, runSpacing: 4, children: [
                              UrgencyChip('${r['urgency']}'),
                              Row(mainAxisSize: MainAxisSize.min, children: [
                                const Icon(Icons.place_outlined, size: 16),
                                Text(' ${r['commune_name']}'
                                    '${distance != null ? ' · ${context.tr('km_away', {'n': distance.toStringAsFixed(1)})}' : ''}'),
                              ]),
                            ]),
                            if (r['budget_min'] != null || r['budget_max'] != null) ...[
                              const SizedBox(height: 4),
                              Text(context.tr('budget_range',
                                  {'range': budgetRange(context, r['budget_min'], r['budget_max'])})),
                            ],
                          ]),
                        ),
                      ),
                    );
                  },
                );
              },
            ),
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
