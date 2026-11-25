import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import 'config.dart';
import 'flavor.dart';
import 'l10n.dart';
import 'state/session.dart';
import 'theme.dart';
import 'widgets/common.dart';

/// Ouvre la politique de confidentialité (page publique du serveur, français + arabe).
Future<void> openPrivacyPolicy(BuildContext context) async {
  final anchor = context.isArabic ? '#ar' : '#fr';
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
