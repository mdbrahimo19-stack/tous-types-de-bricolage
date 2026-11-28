import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import 'api/api_client.dart';
import 'config.dart';
import 'flavor.dart';
import 'l10n.dart';
import 'state/session.dart';
import 'theme.dart';
import 'widgets/common.dart';

/// Ouvre la politique de confidentialité (page publique du serveur, français + arabe).
Future<void> openPrivacyPolicy(BuildContext context) async {
  final anchor = '#${context.lang}';
  final url = Uri.parse('${ServerConfig.baseUrl}/confidentialite/$anchor');
  if (!await launchUrl(url, mode: LaunchMode.externalApplication) && context.mounted) {
    showInfo(context, context.tr('card_open_failed'));
  }
}

/// Écran affiché aux utilisateurs déjà inscrits tant qu'ils n'ont pas accepté
/// la version actuelle de la politique (loi 18-07 : consentement explicite).
class PrivacyGateScreen extends StatefulWidget {
  const PrivacyGateScreen({super.key});

  @override
  State<PrivacyGateScreen> createState() => _PrivacyGateScreenState();
}

class _PrivacyGateScreenState extends State<PrivacyGateScreen> {
  bool _checked = false;
  bool _busy = false;

  Future<void> _accept() async {
    setState(() => _busy = true);
    await runAction(context, () => context.read<Session>().acceptPrivacy());
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.current;
    return Scaffold(
      body: SafeArea(
        child: ListView(padding: const EdgeInsets.fromLTRB(24, 40, 24, 24), children: [
          Icon(Icons.privacy_tip_outlined, size: 56, color: p.primary),
          const SizedBox(height: 16),
          Text(context.tr('privacy_gate_title'),
              textAlign: TextAlign.center, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
          const SizedBox(height: 12),
          Text(context.tr('privacy_gate_text', {'app': AppFlavor.name}),
              textAlign: TextAlign.center, style: TextStyle(fontSize: 15, height: 1.5, color: p.muted)),
          const SizedBox(height: 20),
          OutlinedButton.icon(
            onPressed: () => openPrivacyPolicy(context),
            icon: const Icon(Icons.open_in_new),
            label: Text(context.tr('privacy_read')),
          ),
          const SizedBox(height: 12),
          PrivacyCheckbox(value: _checked, onChanged: (v) => setState(() => _checked = v)),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: _checked && !_busy ? _accept : null,
            child: _busy
                ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2))
                : Text(context.tr('privacy_accept_btn')),
          ),
          const SizedBox(height: 8),
          TextButton(
            onPressed: () => context.read<Session>().logout(),
            child: Text(context.tr('logout')),
          ),
        ]),
      ),
    );
  }
}

/// Droit d'accès : tout ce que BRICOOL conserve sur la personne, par rubrique, + copie complète.
class MyDataScreen extends StatelessWidget {
  const MyDataScreen({super.key});

  static const _sections = {
    'compte': 'data_account',
    'adresses': 'data_addresses',
    'demandes': 'data_requests',
    'devis_envoyes': 'data_quotes',
    'missions': 'data_missions',
    'messages_envoyes': 'data_messages',
    'avis_ecrits': 'data_reviews_written',
    'avis_recus': 'data_reviews_received',
    'notifications': 'data_notifications',
    'profil_artisan': 'data_provider',
    'realisations': 'data_portfolio',
    'points': 'data_points',
    'paiements': 'data_payments',
  };

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.current;
    return Scaffold(
      appBar: AppBar(title: Text(context.tr('data_title'))),
      body: LoadView<Json>(
        load: () async => ((await context.api.get('/api/auth/me/export/')) as Map).cast<String, dynamic>(),
        builder: (context, data, _) {
          const encoder = JsonEncoder.withIndent('  ');
          return ListView(padding: const EdgeInsets.all(16), children: [
            Text(context.tr('data_intro'), style: TextStyle(color: p.muted, height: 1.45)),
            const SizedBox(height: 12),
            FilledButton.icon(
              icon: const Icon(Icons.copy_all_outlined),
              label: Text(context.tr('data_copy')),
              onPressed: () {
                Clipboard.setData(ClipboardData(text: encoder.convert(data)));
                showInfo(context, context.tr('copied'));
              },
            ),
            const SizedBox(height: 12),
            for (final entry in _sections.entries)
              if (data.containsKey(entry.key))
                Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ExpansionTile(
                    shape: const Border(),
                    title: Text(context.tr(entry.value), style: const TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: Text(_count(context, data[entry.key]), style: TextStyle(color: p.muted, fontSize: 12.5)),
                    childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                    children: [
                      SelectableText(
                        encoder.convert(data[entry.key]),
                        textDirection: TextDirection.ltr,
                        style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
                      ),
                    ],
                  ),
                ),
          ]);
        },
      ),
    );
  }

  String _count(BuildContext context, Object? value) =>
      value is List ? context.tr('data_items', {'n': value.length}) : context.tr('data_details');
}

/// Droit à l'effacement : confirmation, puis anonymisation définitive du compte et déconnexion.
Future<void> confirmDeleteAccount(BuildContext context) async {
  final ok = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      icon: const Icon(Icons.warning_amber_rounded, color: Colors.red, size: 36),
      title: Text(ctx.tr('delete_title')),
      content: Text(ctx.tr('delete_text')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(ctx.tr('cancel'))),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: Colors.red.shade700),
          onPressed: () => Navigator.pop(ctx, true),
          child: Text(ctx.tr('delete_confirm')),
        ),
      ],
    ),
  );
  if (ok != true || !context.mounted) return;
  final session = context.read<Session>();
  final done = await runAction(context, session.deleteAccount);
  if (done && context.mounted) showInfo(context, context.tr('delete_done'));
}

/// Case « J'accepte la politique de confidentialité » avec lien pour la lire.
class PrivacyCheckbox extends StatelessWidget {
  const PrivacyCheckbox({super.key, required this.value, required this.onChanged});

  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Checkbox(value: value, onChanged: (v) => onChanged(v ?? false)),
      Expanded(
        child: Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            GestureDetector(
              onTap: () => onChanged(!value),
              child: Text(context.tr('privacy_accept_label'), style: const TextStyle(fontSize: 13.5, height: 1.4)),
            ),
            TextButton(
              style: TextButton.styleFrom(padding: EdgeInsets.zero, minimumSize: const Size(0, 36)),
              onPressed: () => openPrivacyPolicy(context),
              child: Text(context.tr('privacy_read')),
            ),
          ]),
        ),
      ),
    ]);
  }
}
