import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../l10n.dart';
import '../widgets/common.dart';
import 'client.dart';

// ==========================================================================
//  Annuaire des professionnels : recherche par métier, wilaya, nom
// ==========================================================================
class DirectoryScreen extends StatefulWidget {
  const DirectoryScreen({super.key, this.initialCategory});

  final Json? initialCategory;

  @override
  State<DirectoryScreen> createState() => _DirectoryScreenState();
}

class _DirectoryScreenState extends State<DirectoryScreen> {
  final _search = TextEditingController();
  Json? _category;
  Json? _wilaya;
  bool _availableOnly = false;

  final List<Json> _items = [];
  int _page = 1;
  bool _hasMore = false;
  bool _loading = false;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _category = widget.initialCategory;
    _load(reset: true);
  }

  Map<String, String> get _query => {
        if (_category != null) 'category': '${_category!['id']}',
        if (_wilaya != null) 'wilaya': '${_wilaya!['id']}',
        if (_availableOnly) 'available': '1',
        if (_search.text.trim().isNotEmpty) 'search': _search.text.trim(),
      };

  Future<void> _load({bool reset = false}) async {
    if (_loading) return;
    setState(() {
      _loading = true;
      _error = null;
      if (reset) {
        _page = 1;
        _items.clear();
      }
    });
    try {
      final data = await context.api.get('/api/providers/', query: {..._query, 'page': '$_page'}) as Map;
      final results = (data['results'] as List).cast<Map>().map((e) => e.cast<String, dynamic>());
      if (!mounted) return;
      setState(() {
        _items.addAll(results);
        _hasMore = data['next'] != null;
        _page += 1;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _chooseCategory() async {
    final c = await pickCategory(context);
    if (c == null) return;
    setState(() => _category = c);
    _load(reset: true);
  }

  Future<void> _chooseWilaya() async {
    final api = context.api;
    final result = await showModalBottomSheet<Json>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.7,
        builder: (ctx, scroll) => FutureBuilder<List<Json>>(
          future: Refs.wilayas(api),
          builder: (ctx, snap) {
            if (!snap.hasData) return const Center(child: CircularProgressIndicator());
            return ListView(controller: scroll, children: [
              ListTile(
                leading: const Icon(Icons.public),
                title: Text(ctx.tr('dir_all_wilayas')),
                onTap: () => Navigator.pop(ctx, const <String, dynamic>{}),
              ),
              for (final w in snap.data!)
                ListTile(title: Text('${w['code']} · ${ctx.nameOf(w)}'), onTap: () => Navigator.pop(ctx, w)),
            ]);
          },
        ),
      ),
    );
    if (result == null) return;
    setState(() => _wilaya = result.isEmpty ? null : result);
    _load(reset: true);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(context.tr('dir_title'))),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
          child: TextField(
            controller: _search,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              hintText: context.tr('dir_search_hint'),
              prefixIcon: const Icon(Icons.search),
              isDense: true,
              suffixIcon: _search.text.isEmpty
                  ? null
                  : IconButton(
                      icon: const Icon(Icons.clear),
                      onPressed: () {
                        _search.clear();
                        _load(reset: true);
                      },
                    ),
            ),
            onChanged: (_) => setState(() {}),
            onSubmitted: (_) => _load(reset: true),
          ),
        ),
        SizedBox(
          height: 56,
          child: ListView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            children: [
              InputChip(
                avatar: const Icon(Icons.handyman_outlined, size: 18),
                label: Text(_category == null ? context.tr('dir_all_trades') : context.nameOf(_category)),
                selected: _category != null,
                onPressed: _chooseCategory,
                onDeleted: _category == null
                    ? null
                    : () {
                        setState(() => _category = null);
                        _load(reset: true);
                      },
              ),
              const SizedBox(width: 8),
              InputChip(
                avatar: const Icon(Icons.place_outlined, size: 18),
                label: Text(_wilaya == null ? context.tr('dir_all_wilayas') : context.nameOf(_wilaya)),
                selected: _wilaya != null,
                onPressed: _chooseWilaya,
                onDeleted: _wilaya == null
                    ? null
                    : () {
                        setState(() => _wilaya = null);
                        _load(reset: true);
                      },
              ),
              const SizedBox(width: 8),
              FilterChip(
                label: Text(context.tr('dir_available_only')),
                selected: _availableOnly,
                onSelected: (v) {
                  setState(() => _availableOnly = v);
                  _load(reset: true);
                },
              ),
            ],
          ),
        ),
        Expanded(child: _buildList()),
      ]),
    );
  }

  Widget _buildList() {
    if (_items.isEmpty && _loading) return const Center(child: CircularProgressIndicator());
    if (_items.isEmpty && _error != null) {
      final e = _error;
      return EmptyState(
        icon: Icons.cloud_off,
        text: e is ApiException ? e.message : context.tr('error_generic'),
        action: FilledButton.tonal(onPressed: () => _load(reset: true), child: Text(context.tr('retry'))),
      );
    }
    return RefreshIndicator(
      onRefresh: () => _load(reset: true),
      child: _items.isEmpty
          ? EmptyState(icon: Icons.person_search, text: context.tr('dir_empty'))
          : ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
              itemCount: _items.length + (_hasMore ? 1 : 0),
              separatorBuilder: (_, _) => const SizedBox(height: 10),
              itemBuilder: (context, i) {
                if (i == _items.length) {
                  return Center(
                    child: _loading
                        ? const Padding(padding: EdgeInsets.all(8), child: CircularProgressIndicator())
                        : TextButton(onPressed: _load, child: Text(context.tr('dir_more'))),
                  );
                }
                final p = _items[i];
                return ProviderCard(
                  provider: p,
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => ProviderDetailScreen(providerId: p['id'] as int, category: _category)),
                  ),
                );
              },
            ),
    );
  }
}

// ==========================================================================
//  Aides d'affichage
// ==========================================================================
String providerName(Json p) {
  final business = (p['business_name'] as String?)?.trim() ?? '';
  return business.isNotEmpty ? business : (p['full_name'] as String? ?? '');
}

/// Plus petit tarif annoncé (forfait ou taux horaire) parmi les métiers du prestataire.
num? lowestPrice(Json p) {
  num? best;
  for (final c in (p['categories'] as List? ?? const [])) {
    for (final key in const ['flat_rate', 'hourly_rate']) {
      final v = toNum((c as Map)[key]);
      if (v != null && v > 0 && (best == null || v < best)) best = v;
    }
  }
  return best;
}

class ProviderAvatar extends StatelessWidget {
  const ProviderAvatar(this.provider, {super.key, this.radius = 26});

  final Json provider;
  final double radius;

  @override
  Widget build(BuildContext context) {
    final photo = provider['photo'] as String?;
    final name = providerName(provider);
    return CircleAvatar(
      radius: radius,
      foregroundImage: photo == null || photo.isEmpty ? null : NetworkImage(photo),
      child: Text(name.isEmpty ? '?' : name.characters.first.toUpperCase()),
    );
  }
}

class RatingLine extends StatelessWidget {
  const RatingLine(this.provider, {super.key});

  final Json provider;

  @override
  Widget build(BuildContext context) {
    final reviews = toNum(provider['reviews_count']) ?? 0;
    final missions = toNum(provider['missions_count']) ?? 0;
    final rating = toNum(provider['rating_avg']) ?? 0;
    final style = Theme.of(context).textTheme.bodySmall;
    return Wrap(spacing: 10, crossAxisAlignment: WrapCrossAlignment.center, children: [
      if (reviews > 0)
        Row(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.star_rounded, size: 18, color: Colors.amber),
          Text(' ${rating.toStringAsFixed(1)} (${context.tr('dir_reviews', {'n': reviews})})', style: style),
        ])
      else
        Text(context.tr('dir_new'), style: style),
      Text(context.tr('dir_missions', {'n': missions}), style: style),
    ]);
  }
}

class ProviderCard extends StatelessWidget {
  const ProviderCard({super.key, required this.provider, required this.onTap});

  final Json provider;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final p = provider;
    final theme = Theme.of(context);
    final cats = (p['categories'] as List? ?? const []).map((c) => context.nameOf(c as Map)).join(' · ');
    final wilaya = p['base_wilaya'] as Map?;
    final price = lowestPrice(p);
    final available = p['is_available'] == true;
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            ProviderAvatar(p),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Flexible(
                    child: Text(providerName(p),
                        style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
                        overflow: TextOverflow.ellipsis),
                  ),
                  if ((p['badges'] as List? ?? const []).contains('identite_verifiee')) ...[
                    const SizedBox(width: 4),
                    Icon(Icons.verified, size: 18, color: theme.colorScheme.primary),
                  ],
                ]),
                if (cats.isNotEmpty) Text(cats, maxLines: 2, overflow: TextOverflow.ellipsis),
                const SizedBox(height: 4),
                RatingLine(p),
                const SizedBox(height: 4),
                Wrap(spacing: 12, runSpacing: 2, children: [
                  if (wilaya != null)
                    Row(mainAxisSize: MainAxisSize.min, children: [
                      const Icon(Icons.place_outlined, size: 16),
                      Text(context.nameOf(wilaya), style: theme.textTheme.bodySmall),
                    ]),
                  Row(mainAxisSize: MainAxisSize.min, children: [
                    Icon(Icons.circle, size: 10, color: available ? Colors.green : Colors.grey),
                    const SizedBox(width: 4),
                    Text(context.tr(available ? 'dir_available' : 'dir_busy'), style: theme.textTheme.bodySmall),
                  ]),
                  if (price != null)
                    Text(context.tr('dir_from', {'price': money(context, price)}),
                        style: theme.textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w600)),
                ]),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}

// ==========================================================================
//  Fiche d'un professionnel
// ==========================================================================
class ProviderDetailScreen extends StatelessWidget {
  const ProviderDetailScreen({super.key, required this.providerId, this.category});

  final int providerId;

  /// Métier recherché dans l'annuaire : proposé en premier pour la demande de devis.
  final Json? category;

  Future<(Json, List<Json>)> _load(ApiClient api) async {
    final profile = (await api.get('/api/providers/$providerId/') as Map).cast<String, dynamic>();
    final reviews = await api.list('/api/providers/$providerId/reviews/');
    return (profile, reviews);
  }

  Future<void> _requestQuote(BuildContext context, Json p) async {
    final cats = (p['categories'] as List? ?? const []).cast<Map>().map((c) => c.cast<String, dynamic>()).toList();
    Json? chosen;
    if (category != null && cats.any((c) => c['id'] == category!['id'])) {
      chosen = category;
    } else if (cats.length == 1) {
      chosen = cats.first;
    } else if (cats.isNotEmpty) {
      chosen = await showModalBottomSheet<Json>(
        context: context,
        showDragHandle: true,
        builder: (ctx) => ListView(shrinkWrap: true, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: Text(ctx.tr('choose_category'), style: Theme.of(ctx).textTheme.titleMedium),
          ),
          for (final c in cats) ListTile(title: Text(ctx.nameOf(c)), onTap: () => Navigator.pop(ctx, c)),
        ]),
      );
      if (chosen == null) return;
    }
    if (!context.mounted) return;
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => RequestFormScreen(
          initialCategory: chosen == null ? null : {'id': chosen['id'], 'name_fr': chosen['name_fr'], 'name_ar': chosen['name_ar']},
          // demande adressée à ce professionnel uniquement
          targetProvider: {'id': p['id'], 'name': providerName(p)},
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final api = context.api;
    return Scaffold(
      appBar: AppBar(title: Text(context.tr('dir_profile'))),
      body: LoadView<(Json, List<Json>)>(
        load: () => _load(api),
        builder: (context, data, _) {
          final (p, reviews) = data;
          return _ProviderDetailBody(provider: p, reviews: reviews, onRequestQuote: () => _requestQuote(context, p));
        },
      ),
    );
  }
}

class _ProviderDetailBody extends StatelessWidget {
  const _ProviderDetailBody({required this.provider, required this.reviews, required this.onRequestQuote});

  final Json provider;
  final List<Json> reviews;
  final VoidCallback onRequestQuote;

  String _price(BuildContext context, Map c) {
    final parts = <String>[];
    if (toNum(c['flat_rate']) != null) parts.add(context.tr('dir_flat', {'price': money(context, c['flat_rate'])}));
    if (toNum(c['hourly_rate']) != null) parts.add(context.tr('dir_hourly', {'price': money(context, c['hourly_rate'])}));
    if (toNum(c['callout_fee']) != null) parts.add(context.tr('dir_callout', {'price': money(context, c['callout_fee'])}));
    return parts.isEmpty ? context.tr('dir_price_on_quote') : parts.join(' · ');
  }

  @override
  Widget build(BuildContext context) {
    final p = provider;
    final theme = Theme.of(context);
    final badges = (p['badges'] as List? ?? const []).cast<String>();
    final wilaya = p['base_wilaya'] as Map?;
    final bio = (p['bio'] as String?)?.trim() ?? '';
    final years = toNum(p['years_experience']) ?? 0;
    return Column(children: [
      Expanded(
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Row(children: [
            ProviderAvatar(p, radius: 36),
            const SizedBox(width: 16),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(providerName(p), style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
                if ((p['business_name'] as String? ?? '').trim().isNotEmpty) Text(p['full_name'] as String? ?? ''),
                const SizedBox(height: 4),
                RatingLine(p),
                if (wilaya != null)
                  Text('${context.tr('wilaya')} : ${context.nameOf(wilaya)}', style: theme.textTheme.bodySmall),
              ]),
            ),
          ]),
          const SizedBox(height: 12),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final b in badges)
              Chip(
                avatar: Icon(
                  b == 'identite_verifiee' ? Icons.verified : (b == 'top_prestataire' ? Icons.emoji_events : Icons.badge),
                  size: 18,
                ),
                label: Text(context.tr('badge_$b')),
              ),
            Chip(
              avatar: Icon(Icons.circle, size: 12, color: p['is_available'] == true ? Colors.green : Colors.grey),
              label: Text(context.tr(p['is_available'] == true ? 'dir_available' : 'dir_busy')),
            ),
            if (years > 0) Chip(label: Text(context.tr('dir_years', {'n': years}))),
          ]),
          if (bio.isNotEmpty) ...[SectionTitle(context.tr('dir_about')), Text(bio)],
          SectionTitle(context.tr('dir_trades_prices')),
          for (final c in (p['categories'] as List? ?? const []).cast<Map>())
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.handyman_outlined),
              title: Text(context.nameOf(c)),
              subtitle: Text(_price(context, c)),
            ),
          SectionTitle(context.tr('dir_reviews_title', {'n': reviews.length})),
          if (reviews.isEmpty) Text(context.tr('dir_no_reviews'), style: theme.textTheme.bodyMedium),
          for (final r in reviews) _ReviewTile(review: r),
        ]),
      ),
      SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min, children: [
            Text(context.tr('dir_quote_note'), style: theme.textTheme.bodySmall, textAlign: TextAlign.center),
            const SizedBox(height: 8),
            FilledButton.icon(
              icon: const Icon(Icons.request_quote_outlined),
              label: Text(context.tr('dir_request_quote')),
              onPressed: onRequestQuote,
            ),
          ]),
        ),
      ),
    ]);
  }
}

class _ReviewTile extends StatelessWidget {
  const _ReviewTile({required this.review});

  final Json review;

  @override
  Widget build(BuildContext context) {
    final rating = (toNum(review['rating']) ?? 0).toInt();
    final comment = (review['comment'] as String?)?.trim() ?? '';
    final reply = (review['reply'] as String?)?.trim() ?? '';
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          for (var i = 0; i < 5; i++)
            Icon(i < rating ? Icons.star_rounded : Icons.star_outline_rounded, size: 18, color: Colors.amber),
          const SizedBox(width: 8),
          Expanded(
            child: Text('${review['author_name'] ?? ''} · ${formatDate(context, review['created_at'], withTime: false)}',
                style: theme.textTheme.bodySmall, overflow: TextOverflow.ellipsis),
          ),
        ]),
        if (comment.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 4), child: Text(comment)),
        if (reply.isNotEmpty)
          Container(
            margin: const EdgeInsets.only(top: 6),
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: theme.colorScheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text('${context.tr('dir_reply')} : $reply', style: theme.textTheme.bodySmall),
          ),
        const Divider(height: 20),
      ]),
    );
  }
}
