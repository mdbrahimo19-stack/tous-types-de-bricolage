import 'package:flutter/material.dart';

import '../core/api.dart';
import '../core/format.dart';
import '../core/i18n.dart';
import '../widgets/common.dart';

/// Fiche publique d'un prestataire + ses avis.
class ProviderScreen extends StatelessWidget {
  const ProviderScreen({super.key, required this.providerId});
  final int providerId;

  Future<(Json, List<Json>)> _load() async {
    final api = Api.instance;
    final p = Json.from(await api.get('/providers/$providerId/', auth: false));
    final reviews = await api.getAll('/providers/$providerId/reviews/', auth: false, maxPages: 3);
    return (p, reviews);
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(s.t('see_profile'))),
      body: AsyncBody<(Json, List<Json>)>(
        load: _load,
        builder: (context, data, reload) {
          final (p, reviews) = data;
          final name = (p['business_name'] ?? '').toString().isNotEmpty ? p['business_name'] : p['full_name'];
          final badges = (p['badges'] as List? ?? []).cast<String>();
          final cats = (p['categories'] as List? ?? []).cast<Json>();
          return ListView(padding: const EdgeInsets.all(16), children: [
            Row(children: [
              CircleAvatar(radius: 32, child: Text(name.toString().isEmpty ? '?' : name.toString()[0].toUpperCase(),
                  style: const TextStyle(fontSize: 28))),
              const SizedBox(width: 16),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(name.toString(), style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 4),
                  Stars(toDouble(p['rating_avg']) ?? 0, count: (p['reviews_count'] as num?)?.toInt()),
                  Text('${p['missions_count'] ?? 0} ${s.t('missions_done')} · '
                      '${s.t('experience')} : ${p['years_experience'] ?? 0} ${s.t('years')}',
                      style: const TextStyle(color: Colors.grey)),
                ]),
              ),
            ]),
            const SizedBox(height: 12),
            Wrap(spacing: 8, runSpacing: 4, children: [
              for (final b in badges)
                Chip(avatar: const Icon(Icons.verified, size: 18, color: Colors.green), label: Text(s.t('badge_$b'))),
              if (p['legal_status'] == 'non_declare') Chip(label: Text(s.t('not_declared'))),
            ]),
            if ((p['bio'] ?? '').toString().isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(p['bio']),
            ],
            if (cats.isNotEmpty) ...[
              const SizedBox(height: 12),
              Wrap(spacing: 8, runSpacing: 4, children: [
                for (final c in cats) Chip(label: Text(s.name(c))),
              ]),
            ],
            const Divider(height: 32),
            Text('${s.t('reviews')} (${reviews.length})', style: Theme.of(context).textTheme.titleMedium),
            if (reviews.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Text(s.t('no_reviews'), style: const TextStyle(color: Colors.grey)),
              ),
            for (final r in reviews)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Stars(toDouble(r['rating']) ?? 0),
                title: Text((r['comment'] ?? '').toString().isEmpty ? '—' : r['comment']),
                subtitle: Text([
                  r['author_name'] ?? '',
                  dateOnly(r['created_at']),
                  if ((r['reply'] ?? '').toString().isNotEmpty) '↳ ${r['reply']}',
                ].join(' · ')),
              ),
          ]);
        },
      ),
    );
  }
}
