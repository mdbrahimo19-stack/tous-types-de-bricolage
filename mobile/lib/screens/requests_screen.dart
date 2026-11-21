import 'package:flutter/material.dart';

import '../core/api.dart';
import '../core/format.dart';
import '../core/i18n.dart';
import '../widgets/common.dart';
import 'chat_screen.dart';
import 'mission_screen.dart';
import 'provider_screen.dart';

/// Onglet « Mes demandes » (historique complet).
class RequestsTab extends StatelessWidget {
  const RequestsTab({super.key});

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    return AsyncBody<List<Json>>(
      load: () => Api.instance.getAll('/requests/'),
      builder: (context, items, reload) => RefreshIndicator(
        onRefresh: reload,
        child: items.isEmpty
            ? ListView(children: [EmptyState(s.t('no_requests'))])
            : ListView(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 88),
                children: [for (final r in items) RequestTile(r, onChanged: reload)],
              ),
      ),
    );
  }
}

class RequestTile extends StatelessWidget {
  const RequestTile(this.r, {super.key, this.onChanged});
  final Json r;
  final Future<void> Function()? onChanged;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final cat = r['category_detail'] as Map?;
    final quotes = (r['quotes_count'] as num?)?.toInt() ?? 0;
    return Card(
      child: ListTile(
        leading: CircleAvatar(child: Icon(categoryIcon(cat?['icon']))),
        title: Text(r['title'] ?? '', maxLines: 1, overflow: TextOverflow.ellipsis),
        subtitle: Text('${s.name(cat)} · ${dateOnly(r['created_at'])}'
            '${quotes > 0 ? ' · $quotes ${s.t('quotes').toLowerCase()}' : ''}'),
        trailing: RequestStatusChip(r['status'] ?? ''),
        onTap: () async {
          await Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => RequestDetailScreen(requestId: r['id'] as int)),
          );
          await onChanged?.call();
        },
      ),
    );
  }
}

/// Détail d'une demande : infos, photos, comparaison des devis, acceptation.
class RequestDetailScreen extends StatefulWidget {
  const RequestDetailScreen({super.key, required this.requestId});
  final int requestId;

  @override
  State<RequestDetailScreen> createState() => _RequestDetailScreenState();
}

class _RequestDetailScreenState extends State<RequestDetailScreen> {
  final _api = Api.instance;
  Key _key = UniqueKey();

  Future<(Json, List<Json>, Json?)> _load() async {
    final id = widget.requestId;
    final req = Json.from(await _api.get('/requests/$id/'));
    final quotes = ((await _api.get('/requests/$id/quotes/')) as List).cast<Json>();
    Json? mission;
    if (const ['assigned', 'in_progress', 'completed', 'evaluated', 'closed'].contains(req['status'])) {
      final missions = await _api.getAll('/missions/');
      for (final m in missions) {
        if (m['request'] == id) {
          mission = m;
          break;
        }
      }
    }
    return (req, quotes, mission);
  }

  void _reload() => setState(() => _key = UniqueKey());

  Future<void> _accept(Json quote) async {
    final s = S.of(context);
    if (!await confirmDialog(context, s.t('accept_confirm'))) return;
    try {
      final mission = Json.from(await _api.post('/quotes/${quote['id']}/accept/'));
      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => MissionScreen(missionId: mission['id'] as int)),
      );
      _reload();
    } on ApiException catch (e) {
      if (mounted) toast(context, e.message);
    }
  }

  Future<void> _cancel() async {
    final s = S.of(context);
    if (!await confirmDialog(context, s.t('cancel_request_confirm'))) return;
    try {
      await _api.post('/requests/${widget.requestId}/cancel/');
      _reload();
    } on ApiException catch (e) {
      if (mounted) toast(context, e.message);
    }
  }

  Future<void> _openChat(Json quote) async {
    try {
      final convs = await _api.getAll('/conversations/');
      Json? conv;
      for (final c in convs) {
        if (c['request'] == widget.requestId && (c['other_party'] as Map?)?['id'] == quote['provider']) {
          conv = c;
          break;
        }
      }
      if (!mounted) return;
      final found = conv;
      if (found == null) {
        toast(context, S.of(context).t('no_conversations'));
        return;
      }
      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ChatScreen(conversation: found)));
    } on ApiException catch (e) {
      if (mounted) toast(context, e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(s.t('my_requests'))),
      body: AsyncBody<(Json, List<Json>, Json?)>(
        key: _key,
        load: _load,
        builder: (context, data, reload) {
          final (req, quotes, mission) = data;
          final status = req['status'] as String? ?? '';
          final photos = (req['photos'] as List? ?? []).cast<Json>();
          final canAccept = status == 'published' || status == 'quotes_received';
          final canCancel = const ['draft', 'published', 'quotes_received'].contains(status);
          final cat = req['category_detail'] as Map?;
          return RefreshIndicator(
            onRefresh: reload,
            child: ListView(padding: const EdgeInsets.all(16), children: [
              Row(children: [
                Expanded(child: Text(req['title'] ?? '', style: Theme.of(context).textTheme.titleLarge)),
                RequestStatusChip(status),
              ]),
              const SizedBox(height: 8),
              Wrap(spacing: 8, runSpacing: 4, children: [
                Chip(avatar: Icon(categoryIcon(cat?['icon']), size: 18), label: Text(s.name(cat))),
                Chip(avatar: const Icon(Icons.schedule, size: 18), label: Text(s.t('u_${req['urgency']}'))),
                if (req['budget_min'] != null || req['budget_max'] != null)
                  Chip(
                    avatar: const Icon(Icons.payments_outlined, size: 18),
                    label: Text('${money(req['budget_min'])} – ${money(req['budget_max'])}'),
                  ),
              ]),
              if ((req['description'] ?? '').toString().isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(req['description']),
              ],
              if (photos.isNotEmpty) ...[
                const SizedBox(height: 12),
                SizedBox(
                  height: 90,
                  child: ListView(scrollDirection: Axis.horizontal, children: [
                    for (final p in photos)
                      Padding(padding: const EdgeInsetsDirectional.only(end: 8), child: NetImage(p['image'], size: 90)),
                  ]),
                ),
              ],
              if (req['expires_at'] != null && canAccept) ...[
                const SizedBox(height: 8),
                Text('${s.t('valid_until')} ${dateTime(req['expires_at'])}',
                    style: const TextStyle(color: Colors.grey)),
              ],
              if (mission != null) ...[
                const SizedBox(height: 16),
                FilledButton.icon(
                  icon: const Icon(Icons.engineering),
                  label: Text(s.t('open_mission')),
                  onPressed: () async {
                    await Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => MissionScreen(missionId: mission['id'] as int),
                    ));
                    _reload();
                  },
                ),
              ],
              const Divider(height: 32),
              Text('${s.t('quotes')} (${quotes.length})', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              if (quotes.isEmpty)
                Text(s.t('no_quotes'), style: const TextStyle(color: Colors.grey))
              else
                for (final q in quotes)
                  _QuoteCard(
                    q,
                    canAccept: canAccept && q['status'] == 'sent',
                    onAccept: () => _accept(q),
                    onChat: () => _openChat(q),
                  ),
              if (canCancel) ...[
                const SizedBox(height: 24),
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(foregroundColor: Colors.red),
                  icon: const Icon(Icons.close),
                  label: Text(s.t('cancel_request')),
                  onPressed: _cancel,
                ),
              ],
            ]),
          );
        },
      ),
    );
  }
}

class _QuoteCard extends StatelessWidget {
  const _QuoteCard(this.q, {required this.canAccept, required this.onAccept, required this.onChat});
  final Json q;
  final bool canAccept;
  final VoidCallback onAccept;
  final VoidCallback onChat;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final p = (q['provider_detail'] as Map?) ?? {};
    final name = (p['business_name'] ?? '').toString().isNotEmpty ? p['business_name'] : (p['full_name'] ?? '');
    final status = q['status'] as String? ?? '';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(name.toString(), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                const SizedBox(height: 2),
                Row(children: [
                  Stars(toDouble(p['rating_avg']) ?? 0, count: (p['reviews_count'] as num?)?.toInt()),
                  if (p['missions_count'] != null)
                    Text('  · ${p['missions_count']} ${s.t('missions_done')}',
                        style: const TextStyle(color: Colors.grey)),
                ]),
              ]),
            ),
            Text(money(q['amount']),
                style: TextStyle(
                    fontSize: 18, fontWeight: FontWeight.bold, color: Theme.of(context).colorScheme.primary)),
          ]),
          const SizedBox(height: 8),
          Text('${s.t('lead_time')} : ${q['lead_time_days'] ?? '—'} ${s.t('days')}'
              '${(q['estimated_duration'] ?? '').toString().isNotEmpty ? ' · ${s.t('duration')} : ${q['estimated_duration']}' : ''}'),
          if ((q['message'] ?? '').toString().isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(q['message'], style: const TextStyle(fontStyle: FontStyle.italic)),
          ],
          const SizedBox(height: 4),
          Text('${s.t('valid_until')} ${dateTime(q['valid_until'])}',
              style: const TextStyle(color: Colors.grey, fontSize: 12)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 4, crossAxisAlignment: WrapCrossAlignment.center, children: [
            if (status != 'sent') StatusChip(s.t('q_$status'), status == 'accepted' ? Colors.green : Colors.grey),
            if (p['id'] != null)
              TextButton(
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => ProviderScreen(providerId: p['id'] as int)),
                ),
                child: Text(s.t('see_profile')),
              ),
            TextButton.icon(onPressed: onChat, icon: const Icon(Icons.chat_bubble_outline, size: 18), label: Text(s.t('chat'))),
            if (canAccept) FilledButton(onPressed: onAccept, child: Text(s.t('accept'))),
          ]),
        ]),
      ),
    );
  }
}
