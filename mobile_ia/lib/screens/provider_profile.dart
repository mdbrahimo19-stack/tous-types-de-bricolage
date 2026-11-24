import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../l10n.dart';
import '../theme.dart';
import '../widgets/avatar.dart';
import '../widgets/common.dart';

/// Fiche de l'artisan, ouverte depuis un devis reçu (« Voir le profil »).
/// Photo, badges de confiance, chiffres, présentation, métiers et avis des clients.
class ProviderProfileScreen extends StatelessWidget {
  const ProviderProfileScreen({super.key, required this.providerId, this.amount, this.onAccept});

  final int providerId;

  /// Montant du devis et action « Accepter » (barre du bas), si le devis peut encore être accepté.
  final dynamic amount;
  final VoidCallback? onAccept;

  Future<(Json, List<Json>)> _load(BuildContext context) async {
    final api = context.api;
    final results = await Future.wait([
      api.get('/api/providers/$providerId/'),
      api.get('/api/providers/$providerId/reviews/'),
    ]);
    final raw = results[1];
    final list = raw is Map ? (raw['results'] as List? ?? const []) : (raw as List? ?? const []);
    return (
      (results[0] as Map).cast<String, dynamic>(),
      list.cast<Map>().map((e) => e.cast<String, dynamic>()).toList(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.current;
    final accept = onAccept;
    return Scaffold(
      backgroundColor: p.background,
      appBar: AppBar(
        backgroundColor: p.ink,
        foregroundColor: Colors.white,
        title: Text(context.tr('provider_profile_title')),
        titleTextStyle: const TextStyle(fontFamily: 'Poppins', fontSize: 17, fontWeight: FontWeight.w700, color: Colors.white),
      ),
      bottomNavigationBar: accept == null
          ? null
          : SafeArea(
              child: Container(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                decoration: BoxDecoration(color: Colors.white, border: Border(top: BorderSide(color: p.border))),
                child: Row(children: [
                  Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(context.tr('his_quote'), style: TextStyle(fontSize: 12, color: p.muted)),
                    Text(money(context, amount), style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w800)),
                  ]),
                  const SizedBox(width: 12),
                  Expanded(
                    child: FilledButton(
                      onPressed: () {
                        Navigator.pop(context);
                        accept();
                      },
                      child: Text(context.tr('accept_this_quote')),
                    ),
                  ),
                ]),
              ),
            ),
      body: LoadView<(Json, List<Json>)>(
        load: () => _load(context),
        builder: (context, data, _) {
          final (pro, reviews) = data;
          return ListView(padding: EdgeInsets.zero, children: [
            _Header(pro: pro),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                _Stats(pro: pro),
                if ('${pro['bio'] ?? ''}'.trim().isNotEmpty) ...[
                  _Title(context.tr('about')),
                  Text('${pro['bio']}'.trim(), style: TextStyle(fontSize: 14, height: 1.55, color: p.ink)),
                ],
                if ((pro['categories'] as List? ?? const []).isNotEmpty) ...[
                  _Title(context.tr('trades')),
                  Wrap(spacing: 8, runSpacing: 8, children: [
                    for (final c in (pro['categories'] as List).cast<Map>())
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(999),
                          border: Border.all(color: p.border),
                        ),
                        child: Text(context.nameOf(c), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                      ),
                  ]),
                ],
                _Title(context.tr('client_reviews', {'n': pro['reviews_count'] ?? reviews.length})),
                if (reviews.isEmpty)
                  Text(context.tr('no_reviews_yet'), style: TextStyle(color: p.muted))
                else
                  for (final r in reviews) _ReviewCard(review: r),
              ]),
            ),
          ]);
        },
      ),
    );
  }
}

/// Bandeau sombre : photo, nom, métier · wilaya, badges.
class _Header extends StatelessWidget {
  const _Header({required this.pro});

  final Json pro;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.current;
    final name = '${(pro['business_name'] as String?)?.isNotEmpty == true ? pro['business_name'] : pro['full_name'] ?? ''}';
    final cats = (pro['categories'] as List? ?? const []).cast<Map>();
    final wilaya = pro['base_wilaya'] as Map?;
    final subtitle = [
      if (cats.isNotEmpty) context.nameOf(cats.first),
      if (wilaya != null) context.nameOf(wilaya),
    ].join(' · ');
    final badges = (pro['badges'] as List? ?? const []).cast<String>();
    return Stack(children: [
      Container(height: 60, color: p.ink),
      Padding(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
        child: Center(
          child: Column(children: [
            Container(
              decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: p.background, width: 4)),
              child: PersonAvatar(
                name: name,
                photoUrl: pro['photo'] as String?,
                size: 96,
                verified: pro['is_verified'] == true,
              ),
            ),
            const SizedBox(height: 10),
            Text(name, textAlign: TextAlign.center, style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w800)),
            if (subtitle.isNotEmpty)
              Text(subtitle, textAlign: TextAlign.center, style: TextStyle(fontSize: 13, color: p.muted)),
            const SizedBox(height: 10),
            Wrap(alignment: WrapAlignment.center, spacing: 6, runSpacing: 6, children: [
              if (pro['is_verified'] == true)
                _Badge(Icons.verified_user_outlined, context.tr('verified_by_bricool'), strong: true),
              if (pro['member_since'] != null) _Badge(null, context.tr('member_since', {'y': pro['member_since']})),
              if (badges.contains('professionnel_declare')) _Badge(null, context.tr('badge_declared')),
              if (badges.contains('top_prestataire')) _Badge(Icons.workspace_premium_outlined, context.tr('badge_top')),
            ]),
          ]),
        ),
      ),
    ]);
  }
}

class _Badge extends StatelessWidget {
  const _Badge(this.icon, this.text, {this.strong = false});

  final IconData? icon;
  final String text;
  final bool strong;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.current;
    final fg = strong ? AppPalette.success : p.ink;
    final bg = strong ? AppPalette.successSoft : const Color(0xFFEFEAE4);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(999)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        if (icon != null) ...[Icon(icon, size: 15, color: fg), const SizedBox(width: 4)],
        Text(text, style: TextStyle(fontSize: 12, fontWeight: strong ? FontWeight.w700 : FontWeight.w600, color: fg)),
      ]),
    );
  }
}

/// Les 4 chiffres : note, avis, missions, années d'expérience.
class _Stats extends StatelessWidget {
  const _Stats({required this.pro});

  final Json pro;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.current;
    final rating = (toNum(pro['rating_avg']) ?? 0).toDouble();
    final cells = [
      (rating > 0 ? rating.toStringAsFixed(1) : '–', context.tr('stat_rating')),
      ('${pro['reviews_count'] ?? 0}', context.tr('stat_reviews')),
      ('${pro['missions_count'] ?? 0}', context.tr('stat_missions')),
      ('${pro['years_experience'] ?? 0}', context.tr('stat_years')),
    ];
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 4),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: p.border),
      ),
      child: Row(children: [
        for (final (value, label) in cells)
          Expanded(
            child: Column(children: [
              Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
              Text(label, textAlign: TextAlign.center, style: TextStyle(fontSize: 11, color: p.muted)),
            ]),
          ),
      ]),
    );
  }
}

class _Title extends StatelessWidget {
  const _Title(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 22, bottom: 8),
        child: Text(text, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
      );
}

/// Un avis : auteur (prénom + initiale), étoiles, date, commentaire, réponse de l'artisan.
class _ReviewCard extends StatelessWidget {
  const _ReviewCard({required this.review});

  final Json review;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.current;
    final rating = (toNum(review['rating']) ?? 0).toInt();
    final comment = '${review['comment'] ?? ''}'.trim();
    final reply = '${review['reply'] ?? ''}'.trim();
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: p.border),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(
            child: Text('${review['author_name'] ?? ''}', style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
          ),
          Text(formatDate(context, review['created_at'], withTime: false), style: TextStyle(fontSize: 12, color: p.muted)),
        ]),
        const SizedBox(height: 4),
        Semantics(
          label: context.tr('stars_label', {'n': rating}),
          child: Row(children: [
            for (var i = 1; i <= 5; i++)
              Icon(Icons.star_rounded, size: 17, color: i <= rating ? AppPalette.star : p.border),
          ]),
        ),
        if (comment.isNotEmpty) ...[
          const SizedBox(height: 6),
          Text(comment, style: TextStyle(fontSize: 13.5, height: 1.5, color: p.ink)),
        ],
        if (reply.isNotEmpty) ...[
          const SizedBox(height: 8),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: p.background, borderRadius: BorderRadius.circular(12)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(context.tr('provider_reply'), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
              const SizedBox(height: 2),
              Text(reply, style: TextStyle(fontSize: 12.5, height: 1.45, color: p.ink)),
            ]),
          ),
        ],
      ]),
    );
  }
}
