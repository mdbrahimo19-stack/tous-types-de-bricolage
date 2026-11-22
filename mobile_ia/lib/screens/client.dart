import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../config.dart';
import '../l10n.dart';
import '../location.dart';
import '../state/session.dart';
import '../widgets/common.dart';
import 'shared.dart';

const _urgencies = ['immediate', 'today', 'this_week', 'flexible'];

// ==========================================================================
//  Accueil client
// ==========================================================================
class ClientHomeScreen extends StatelessWidget {
  const ClientHomeScreen({super.key});

  Future<void> _fromRoot(BuildContext context, Json root) async {
    final children = (root['children'] as List? ?? const []).cast<Map>();
    Json? category = root;
    if (children.isNotEmpty) {
      category = await showModalBottomSheet<Json>(
        context: context,
        showDragHandle: true,
        builder: (ctx) => ListView(shrinkWrap: true, children: [
          for (final c in children)
            ListTile(
              title: Text(ctx.nameOf(c)),
              onTap: () => Navigator.pop(ctx, c.cast<String, dynamic>()),
            ),
        ]),
      );
    }
    if (category != null && context.mounted) {
      Navigator.push(context, MaterialPageRoute(builder: (_) => RequestFormScreen(initialCategory: category)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('app_name')),
        actions: [
          IconButton(
            tooltip: context.tr('support_title'),
            icon: const Icon(Icons.support_agent),
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SupportChatScreen())),
          ),
        ],
      ),
      body: LoadView<List<Json>>(
        load: () => Refs.categories(context.api),
        builder: (context, roots, _) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(context.tr('hello', {'name': session.firstName}),
                style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 16),
            Card(
              color: scheme.primaryContainer,
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  Row(children: [
                    Icon(Icons.auto_awesome, color: scheme.onPrimaryContainer),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(context.tr('describe_title'),
                          style: Theme.of(context)
                              .textTheme
                              .titleLarge
                              ?.copyWith(color: scheme.onPrimaryContainer, fontWeight: FontWeight.bold)),
                    ),
                  ]),
                  const SizedBox(height: 8),
                  Text(context.tr('describe_sub'), style: TextStyle(color: scheme.onPrimaryContainer)),
                  const SizedBox(height: 16),
                  FilledButton.icon(
                    icon: const Icon(Icons.edit_note),
                    label: Text(context.tr('describe_title')),
                    onPressed: () =>
                        Navigator.push(context, MaterialPageRoute(builder: (_) => const DescribeProblemScreen())),
                  ),
                  TextButton(
                    onPressed: () =>
                        Navigator.push(context, MaterialPageRoute(builder: (_) => const RequestFormScreen())),
                    child: Text(context.tr('classic_form')),
                  ),
                ]),
              ),
            ),
            const SizedBox(height: 12),
            Card(
              child: ListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                leading: CircleAvatar(
                  backgroundColor: scheme.secondaryContainer,
                  child: Icon(Icons.near_me, color: scheme.onSecondaryContainer),
                ),
                title: Text(context.tr('home_nearest')),
              ),
            ),
            SectionTitle(context.tr('categories')),
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final root in roots)
                ActionChip(
                  avatar: const Icon(Icons.build_circle_outlined, size: 18),
                  label: Text(context.nameOf(root)),
                  onPressed: () => _fromRoot(context, root),
                ),
            ]),
            const SizedBox(height: 20),
            ListTile(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              tileColor: scheme.surfaceContainerHighest,
              leading: const Icon(Icons.support_agent),
              title: Text(context.tr('need_help')),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SupportChatScreen())),
            ),
          ],
        ),
      ),
    );
  }
}

// ==========================================================================
//  IA : décrire son problème en texte libre
// ==========================================================================
class DescribeProblemScreen extends StatefulWidget {
  const DescribeProblemScreen({super.key});

  @override
  State<DescribeProblemScreen> createState() => _DescribeProblemScreenState();
}

class _DescribeProblemScreenState extends State<DescribeProblemScreen> {
  final _text = TextEditingController();
  bool _busy = false;
  bool _unavailable = false;

  Future<void> _analyze() async {
    final text = _text.text.trim();
    if (text.length < 5) return;
    setState(() {
      _busy = true;
      _unavailable = false;
    });
    try {
      final draft = (await context.api.post('/api/ai/draft-request/', {'text': text}) as Map).cast<String, dynamic>();
      if (!mounted) return;
      Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => RequestFormScreen(draft: draft)));
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.isUnavailable) {
        setState(() => _unavailable = true);
      } else {
        showError(context, e);
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(context.tr('describe_title'))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(context.tr('describe_sub')),
          const SizedBox(height: 16),
          TextField(
            controller: _text,
            minLines: 5,
            maxLines: 10,
            maxLength: 2000,
            decoration: InputDecoration(hintText: context.tr('describe_hint')),
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: _busy ? null : _analyze,
            icon: _busy
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.auto_awesome),
            label: Text(_busy ? context.tr('ai_working') : context.tr('analyze')),
          ),
          if (_unavailable) ...[
            const SizedBox(height: 20),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(children: [
                  Text(context.tr('ai_unavailable')),
                  const SizedBox(height: 8),
                  OutlinedButton(
                    onPressed: () => Navigator.pushReplacement(
                      context,
                      MaterialPageRoute(builder: (_) => RequestFormScreen(initialDescription: _text.text.trim())),
                    ),
                    child: Text(context.tr('classic_form')),
                  ),
                ]),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

// ==========================================================================
//  Formulaire de demande (pré-rempli par l'IA ou vide)
// ==========================================================================
class RequestFormScreen extends StatefulWidget {
  const RequestFormScreen({super.key, this.draft, this.initialCategory, this.initialDescription});

  final Json? draft;
  final Json? initialCategory;
  final String? initialDescription;

  @override
  State<RequestFormScreen> createState() => _RequestFormScreenState();
}

class _RequestFormScreenState extends State<RequestFormScreen> {
  final _form = GlobalKey<FormState>();
  final _title = TextEditingController();
  final _description = TextEditingController();
  final _budgetMin = TextEditingController();
  final _budgetMax = TextEditingController();

  Json? _category;
  int? _wilaya;
  int? _commune;
  GpsFix? _gps; // position du téléphone : sert à trouver les bricoleurs les plus proches
  String _urgency = 'this_week';
  final List<File> _photos = [];
  List<String> _missingInfo = [];
  Json? _estimate;
  bool _estimating = false;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    _category = widget.initialCategory;
    _description.text = widget.initialDescription ?? '';
    final d = widget.draft;
    if (d != null) {
      _title.text = d['title'] as String? ?? '';
      _description.text = d['description'] as String? ?? '';
      if (_urgencies.contains(d['urgency'])) _urgency = d['urgency'] as String;
      if (d['budget_min'] != null) _budgetMin.text = '${d['budget_min']}';
      if (d['budget_max'] != null) _budgetMax.text = '${d['budget_max']}';
      _missingInfo = (d['missing_info'] as List? ?? const []).cast<String>();
      Refs.categoryById(context.api, d['category_id'] as int?).then((c) {
        if (mounted && c != null) setState(() => _category = c);
      });
    }
  }

  Future<void> _addPhoto() async {
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Wrap(children: [
          ListTile(
            leading: const Icon(Icons.photo_camera),
            title: Text(ctx.tr('camera')),
            onTap: () => Navigator.pop(ctx, ImageSource.camera),
          ),
          ListTile(
            leading: const Icon(Icons.photo_library),
            title: Text(ctx.tr('gallery')),
            onTap: () => Navigator.pop(ctx, ImageSource.gallery),
          ),
        ]),
      ),
    );
    if (source == null) return;
    final picked = await ImagePicker().pickImage(source: source, maxWidth: 1600, imageQuality: 75);
    if (picked != null) setState(() => _photos.add(File(picked.path)));
  }

  Future<void> _estimatePrice() async {
    if (_category == null || _description.text.trim().length < 5) {
      showInfo(context, context.tr('estimate_needs'));
      return;
    }
    setState(() => _estimating = true);
    try {
      final data = await context.api.post('/api/ai/price-estimate/', {
        'category': _category!['id'],
        'description': '${_title.text.trim()}\n${_description.text.trim()}',
        'urgency': _urgency,
        if (_wilaya != null) 'wilaya': _wilaya,
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

  Future<void> _submit() async {
    if (_category == null) {
      showInfo(context, context.tr('choose_category'));
      return;
    }
    if (!_form.currentState!.validate()) return;
    setState(() => _submitting = true);
    final api = context.api;
    try {
      final created = await api.post('/api/requests/', {
        'category': _category!['id'],
        'title': _title.text.trim(),
        'description': _description.text.trim(),
        'wilaya': _wilaya,
        'commune': _commune,
        ...?_gps?.toJson(),
        'urgency': _urgency,
        if (toNum(_budgetMin.text) != null) 'budget_min': toNum(_budgetMin.text),
        if (toNum(_budgetMax.text) != null) 'budget_max': toNum(_budgetMax.text),
        'publish_now': true,
      }) as Map;
      final id = created['id'] as int;
      var photosOk = true;
      for (final photo in _photos) {
        try {
          await api.upload('/api/requests/$id/photos/', fileField: 'image', file: photo);
        } on ApiException {
          photosOk = false;
        }
      }
      if (!mounted) return;
      showInfo(context, context.tr(photosOk ? 'published_ok' : 'photo_upload_failed'));
      Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => RequestDetailScreen(requestId: id)));
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(context.tr('new_request'))),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (widget.draft != null)
              Card(
                color: Theme.of(context).colorScheme.secondaryContainer,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      const Icon(Icons.auto_awesome, size: 18),
                      const SizedBox(width: 6),
                      Expanded(child: Text(context.tr('draft_ready'))),
                    ]),
                    if (_missingInfo.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(context.tr('questions_to_add'), style: const TextStyle(fontWeight: FontWeight.w600)),
                      for (final q in _missingInfo) Text('• $q'),
                    ],
                  ]),
                ),
              ),
            const SizedBox(height: 8),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.category),
              title: Text(_category == null ? context.tr('choose_category') : context.nameOf(_category)),
              subtitle: Text(context.tr('category')),
              trailing: const Icon(Icons.edit),
              onTap: () async {
                final c = await pickCategory(context);
                if (c != null) setState(() => _category = c);
              },
            ),
            TextFormField(
              controller: _title,
              maxLength: 140,
              decoration: InputDecoration(labelText: context.tr('title')),
              validator: (v) => (v ?? '').trim().isEmpty ? context.tr('required') : null,
            ),
            TextFormField(
              controller: _description,
              minLines: 3,
              maxLines: 8,
              decoration: InputDecoration(labelText: context.tr('description')),
              validator: (v) => (v ?? '').trim().isEmpty ? context.tr('required') : null,
            ),
            const SizedBox(height: 12),
            GpsCard(onChanged: (fix) => _gps = fix),
            const SizedBox(height: 8),
            LocationFields(onChanged: (w, c) {
              _wilaya = w;
              _commune = c;
            }),
            SectionTitle(context.tr('urgency')),
            Wrap(spacing: 8, children: [
              for (final u in _urgencies)
                ChoiceChip(
                  label: Text(context.tr('urg_$u')),
                  selected: _urgency == u,
                  onSelected: (_) => setState(() => _urgency = u),
                ),
            ]),
            const SizedBox(height: 12),
            Row(children: [
              Expanded(
                child: TextFormField(
                  controller: _budgetMin,
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(labelText: context.tr('budget_min')),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextFormField(
                  controller: _budgetMax,
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(labelText: context.tr('budget_max')),
                ),
              ),
            ]),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: _estimating ? null : _estimatePrice,
              icon: _estimating
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.auto_awesome),
              label: Text(context.tr('estimate_price')),
            ),
            if (_estimate != null) PriceEstimateCard(estimate: _estimate!),
            SectionTitle(context.tr('photos', {'n': _photos.length, 'max': maxRequestPhotos})),
            SizedBox(
              height: 96,
              child: ListView(scrollDirection: Axis.horizontal, children: [
                for (final (i, p) in _photos.indexed)
                  Padding(
                    padding: const EdgeInsetsDirectional.only(end: 8),
                    child: Stack(children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(10),
                        child: Image.file(p, width: 90, height: 90, fit: BoxFit.cover),
                      ),
                      PositionedDirectional(
                        top: 0,
                        end: 0,
                        child: IconButton.filledTonal(
                          iconSize: 16,
                          visualDensity: VisualDensity.compact,
                          icon: const Icon(Icons.close),
                          onPressed: () => setState(() => _photos.removeAt(i)),
                        ),
                      ),
                    ]),
                  ),
                if (_photos.length < maxRequestPhotos)
                  InkWell(
                    onTap: _addPhoto,
                    borderRadius: BorderRadius.circular(10),
                    child: Container(
                      width: 90,
                      height: 90,
                      decoration: BoxDecoration(
                        border: Border.all(color: Theme.of(context).colorScheme.outline),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                        const Icon(Icons.add_a_photo),
                        Text(context.tr('add_photo'), style: const TextStyle(fontSize: 12)),
                      ]),
                    ),
                  ),
              ]),
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _submitting ? null : _submit,
              child: _submitting
                  ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2))
                  : Text(context.tr('publish')),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}

/// Résultat de l'estimation de prix IA (client et prestataire).
class PriceEstimateCard extends StatelessWidget {
  const PriceEstimateCard({super.key, required this.estimate});

  final Json estimate;

  @override
  Widget build(BuildContext context) {
    final basedOn = (estimate['based_on_quotes'] as num?) ?? 0;
    return Card(
      margin: const EdgeInsets.only(top: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(context.tr('estimate_title'), style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 4),
          Text(
            '${money(context, estimate['min_da'])} – ${money(context, estimate['max_da'])}',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
          ),
          Text(context.tr('confidence_${estimate['confidence']}'),
              style: TextStyle(color: Theme.of(context).colorScheme.outline)),
          const SizedBox(height: 8),
          Text('${estimate['explanation'] ?? ''}'),
          if (basedOn > 0) ...[
            const SizedBox(height: 6),
            Text(context.tr('based_on_quotes', {'n': basedOn}), style: const TextStyle(fontSize: 12)),
          ],
        ]),
      ),
    );
  }
}

// ==========================================================================
//  Mes demandes
// ==========================================================================
class MyRequestsScreen extends StatefulWidget {
  const MyRequestsScreen({super.key});

  @override
  State<MyRequestsScreen> createState() => _MyRequestsScreenState();
}

class _MyRequestsScreenState extends State<MyRequestsScreen> {
  final _key = GlobalKey<LoadViewState<List<Json>>>();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(context.tr('my_requests'))),
      floatingActionButton: FloatingActionButton.extended(
        icon: const Icon(Icons.add),
        label: Text(context.tr('new_request')),
        onPressed: () async {
          await Navigator.push(context, MaterialPageRoute(builder: (_) => const DescribeProblemScreen()));
          _key.currentState?.reload();
        },
      ),
      body: LoadView<List<Json>>(
        key: _key,
        load: () => context.api.listAll('/api/requests/'),
        builder: (context, items, reload) {
          if (items.isEmpty) return EmptyState(icon: Icons.inbox_outlined, text: context.tr('no_requests'));
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 96),
            itemCount: items.length,
            separatorBuilder: (_, _) => const SizedBox(height: 8),
            itemBuilder: (context, i) {
              final r = items[i];
              return Card(
                child: ListTile(
                  title: Text('${r['title']}', maxLines: 2, overflow: TextOverflow.ellipsis),
                  subtitle: Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(context.nameOf(r['category_detail'] as Map?)),
                      const SizedBox(height: 4),
                      Row(children: [
                        StatusChip(status: '${r['status']}', prefix: 'rs'),
                        const SizedBox(width: 8),
                        Text(context.tr('quotes_count', {'n': r['quotes_count'] ?? 0})),
                      ]),
                    ]),
                  ),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () async {
                    await Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => RequestDetailScreen(requestId: r['id'] as int)),
                    );
                    reload();
                  },
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
//  Détail d'une demande + comparaison des devis
// ==========================================================================
class RequestDetailScreen extends StatefulWidget {
  const RequestDetailScreen({super.key, required this.requestId});

  final int requestId;

  @override
  State<RequestDetailScreen> createState() => _RequestDetailScreenState();
}

class _RequestDetailScreenState extends State<RequestDetailScreen> {
  final _key = GlobalKey<LoadViewState<(Json, List<Json>)>>();

  Future<(Json, List<Json>)> _load() async {
    final api = context.api;
    final results = await Future.wait([
      api.get('/api/requests/${widget.requestId}/'),
      api.get('/api/requests/${widget.requestId}/quotes/'),
    ]);
    final quotes = (results[1] as List).cast<Map>().map((e) => e.cast<String, dynamic>()).toList();
    return ((results[0] as Map).cast<String, dynamic>(), quotes);
  }

  Future<void> _accept(Json quote) async {
    final ok = await confirmDialog(context, context.tr('accept_confirm', {'amount': money(context, quote['amount'])}));
    if (!ok || !mounted) return;
    Json? mission;
    final done = await runAction(context, () async {
      mission = (await context.api.post('/api/quotes/${quote['id']}/accept/') as Map).cast<String, dynamic>();
    });
    if (!done || !mounted) return;
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => MissionDetailScreen(missionId: mission!['id'] as int)),
    );
    _key.currentState?.reload();
  }

  Future<void> _requestAction(String action, {String? confirmKey}) async {
    if (confirmKey != null && !await confirmDialog(context, context.tr(confirmKey))) return;
    if (!mounted) return;
    final ok = await runAction(context, () => context.api.post('/api/requests/${widget.requestId}/$action/'));
    if (ok) _key.currentState?.reload();
  }

  Future<void> _openMission() async {
    final missions = await context.api.listAll('/api/missions/');
    final m = missions.where((m) => m['request'] == widget.requestId).firstOrNull;
    if (m != null && mounted) {
      Navigator.push(context, MaterialPageRoute(builder: (_) => MissionDetailScreen(missionId: m['id'] as int)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(),
      body: LoadView<(Json, List<Json>)>(
        key: _key,
        load: _load,
        builder: (context, data, reload) {
          final (r, quotes) = data;
          final status = '${r['status']}';
          final open = status == 'published' || status == 'quotes_received';
          final hasMission = const ['assigned', 'in_progress', 'completed', 'evaluated', 'closed'].contains(status);
          final photos = (r['photos'] as List? ?? const []).cast<Map>();
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text('${r['title']}', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Wrap(spacing: 12, runSpacing: 6, crossAxisAlignment: WrapCrossAlignment.center, children: [
                StatusChip(status: status, prefix: 'rs'),
                UrgencyChip('${r['urgency']}'),
                Text(context.nameOf(r['category_detail'] as Map?)),
              ]),
              if (open) ...[
                const SizedBox(height: 12),
                Row(children: [
                  const Icon(Icons.near_me, size: 18),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text((r['dispatched_count'] as num? ?? 0) > 0
                        ? context.tr('dispatched', {'n': r['dispatched_count']})
                        : context.tr('dispatched_none')),
                  ),
                ]),
              ],
              const SizedBox(height: 12),
              Text('${r['description']}'),
              if (r['budget_min'] != null || r['budget_max'] != null) ...[
                const SizedBox(height: 8),
                Text(context.tr('budget_range', {'range': budgetRange(context, r['budget_min'], r['budget_max'])})),
              ],
              if (photos.isNotEmpty) ...[
                const SizedBox(height: 12),
                SizedBox(
                  height: 90,
                  child: ListView(scrollDirection: Axis.horizontal, children: [
                    for (final p in photos)
                      Padding(
                        padding: const EdgeInsetsDirectional.only(end: 8),
                        child: NetImage(p['image'] as String?),
                      ),
                  ]),
                ),
              ],
              const SizedBox(height: 12),
              Wrap(spacing: 8, children: [
                if (hasMission)
                  FilledButton.icon(
                    icon: const Icon(Icons.assignment_turned_in),
                    label: Text(context.tr('see_mission')),
                    onPressed: _openMission,
                  ),
                if (status == 'draft' || status == 'expired')
                  FilledButton(onPressed: () => _requestAction('publish'), child: Text(context.tr('publish_again'))),
                if (open || status == 'draft')
                  OutlinedButton(
                    onPressed: () => _requestAction('cancel', confirmKey: 'cancel_request_confirm'),
                    child: Text(context.tr('cancel_request')),
                  ),
              ]),
              SectionTitle('${context.tr('quotes_received')} (${quotes.length})'),
              if (quotes.isEmpty) Text(context.tr('no_quotes')),
              for (final q in quotes)
                _QuoteCard(
                  quote: q,
                  canAccept: open && q['status'] == 'sent',
                  onAccept: () => _accept(q),
                  onChat: () => openConversation(context, requestId: widget.requestId, otherUserId: q['provider'] as int),
                ),
            ],
          );
        },
      ),
    );
  }
}

class _QuoteCard extends StatelessWidget {
  const _QuoteCard({required this.quote, required this.canAccept, required this.onAccept, required this.onChat});

  final Json quote;
  final bool canAccept;
  final VoidCallback onAccept;
  final VoidCallback onChat;

  @override
  Widget build(BuildContext context) {
    final p = (quote['provider_detail'] as Map?) ?? const {};
    final name = (p['business_name'] as String?)?.isNotEmpty == true ? p['business_name'] : p['full_name'];
    final rating = toNum(p['rating_avg']) ?? 0;
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const CircleAvatar(child: Icon(Icons.person)),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${name ?? ''}', style: const TextStyle(fontWeight: FontWeight.bold)),
                Row(children: [
                  const Icon(Icons.star, size: 16, color: Colors.amber),
                  Text(' ${rating.toStringAsFixed(1)} · ${context.tr('reviews_count', {'n': p['reviews_count'] ?? 0})}'
                      ' · ${context.tr('missions_done', {'n': p['missions_count'] ?? 0})}',
                      style: const TextStyle(fontSize: 12)),
                ]),
              ]),
            ),
            StatusChip(status: '${quote['status']}', prefix: 'qs'),
          ]),
          const SizedBox(height: 10),
          Text(money(context, quote['amount']),
              style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
          Text([
            context.tr('lead_time_days', {'n': quote['lead_time_days']}),
            if ((quote['estimated_duration'] as String?)?.isNotEmpty == true) quote['estimated_duration'],
          ].join(' · ')),
          if ((quote['message'] as String?)?.isNotEmpty == true) ...[
            const SizedBox(height: 6),
            Text('${quote['message']}', style: const TextStyle(fontStyle: FontStyle.italic)),
          ],
          const SizedBox(height: 10),
          Row(mainAxisAlignment: MainAxisAlignment.end, children: [
            TextButton.icon(onPressed: onChat, icon: const Icon(Icons.chat_bubble_outline), label: Text(context.tr('chat'))),
            if (canAccept) ...[
              const SizedBox(width: 8),
              FilledButton(onPressed: onAccept, child: Text(context.tr('accept'))),
            ],
          ]),
        ]),
      ),
    );
  }
}
