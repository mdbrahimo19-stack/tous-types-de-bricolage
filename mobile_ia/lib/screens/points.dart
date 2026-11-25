import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:url_launcher/url_launcher.dart';

import '../api/api_client.dart';
import '../l10n.dart';
import '../theme.dart';
import '../widgets/common.dart';

// ==========================================================================
//  Mes points (bricoleur) : solde, blocage, paiement BaridiMob avec capture
// ==========================================================================
class PointsScreen extends StatefulWidget {
  const PointsScreen({super.key});

  @override
  State<PointsScreen> createState() => _PointsScreenState();
}

class _PointsScreenState extends State<PointsScreen> {
  final _key = GlobalKey<LoadViewState<Json>>();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(context.tr('points_title'))),
      body: LoadView<Json>(
        key: _key,
        load: () async => ((await context.api.get('/api/provider/points/')) as Map).cast<String, dynamic>(),
        builder: (context, p, reload) => _PointsBody(p: p, reload: reload),
      ),
    );
  }
}

class _PointsBody extends StatelessWidget {
  const _PointsBody({required this.p, required this.reload});

  final Json p;
  final Future<void> Function() reload;

  int _int(String k) => (toNum(p[k]) ?? 0).toInt();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;
    final blocked = p['blocked'] == true;
    final due = _int('points_due');
    final blockAt = _int('block_at');
    final pending = p['pending_payment'] as Map?;
    final last = p['last_payment'] as Map?;
    final history = (p['history'] as List? ?? const []).cast<Map>();

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (blocked)
          Card(
            color: scheme.errorContainer,
            child: ListTile(
              leading: Icon(Icons.lock, color: scheme.onErrorContainer),
              title: Text(context.tr('points_blocked'),
                  style: TextStyle(color: scheme.onErrorContainer, fontWeight: FontWeight.bold)),
              subtitle: Text(context.tr('points_blocked_sub', {'amount': money(context, p['amount_due_da'])}),
                  style: TextStyle(color: scheme.onErrorContainer)),
            ),
          ),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: _Figure(label: context.tr('points_free'), value: '${_int('free_points')}')),
                Expanded(child: _Figure(label: context.tr('points_due'), value: '$due / $blockAt')),
              ]),
              const SizedBox(height: 12),
              LinearProgressIndicator(
                value: blockAt > 0 ? (due / blockAt).clamp(0, 1).toDouble() : 0,
                minHeight: 8,
                borderRadius: BorderRadius.circular(4),
                color: blocked ? scheme.error : null,
              ),
              const SizedBox(height: 12),
              Text(context.tr('points_amount', {'amount': money(context, p['amount_due_da'])}),
                  style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              Text(
                context.tr('points_rule', {
                  'n': _int('points_per_contact'),
                  'price': money(context, _int('points_per_contact') * _int('point_value_da')),
                  'max': money(context, blockAt * _int('point_value_da')),
                }),
                style: theme.textTheme.bodySmall,
              ),
            ]),
          ),
        ),
        if (pending != null)
          Card(
            color: scheme.secondaryContainer,
            child: ListTile(
              leading: const Icon(Icons.hourglass_top),
              title: Text(context.tr('pay_pending', {'amount': money(context, pending['amount_da'])})),
              subtitle: Text(context.tr('pay_pending_sub')),
            ),
          )
        else if (due > 0) ...[
          if (last != null && last['status'] == 'rejected')
            Card(
              color: scheme.errorContainer,
              child: ListTile(
                leading: const Icon(Icons.error_outline),
                title: Text(context.tr('pay_rejected')),
                subtitle: Text('${last['admin_note'] ?? ''}'),
              ),
            ),
          if (p['card_enabled'] == true) ...[
            _CardPayCard(p: p, onPaid: reload),
            const SizedBox(height: 12),
          ],
          _PayCard(p: p, onSent: reload),
        ],
        if (history.isNotEmpty) ...[
          SectionTitle(context.tr('points_history')),
          for (final e in history)
            ListTile(
              contentPadding: EdgeInsets.zero,
              dense: true,
              leading: Icon(e['kind'] == 'payment' ? Icons.check_circle_outline : Icons.person_add_alt),
              title: Text(e['kind'] == 'payment'
                  ? context.tr('points_paid', {'n': -(toNum(e['due_delta']) ?? 0)})
                  : context.tr('points_contact', {
                      'n': (toNum(e['due_delta']) ?? 0) + (toNum(e['free_used']) ?? 0),
                      'title': '${e['note'] ?? ''}',
                    })),
              subtitle: Text(formatDate(context, e['created_at'])),
              trailing: (toNum(e['free_used']) ?? 0) > 0 ? Chip(label: Text(context.tr('points_offered'))) : null,
            ),
        ],
      ],
    );
  }
}

class _Figure extends StatelessWidget {
  const _Figure({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(label, style: Theme.of(context).textTheme.bodySmall),
      Text(value, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
    ]);
  }
}

/// Paiement par carte Edahabia / CIB (Chargily) : page sécurisée dans le navigateur,
/// puis vérification automatique au retour dans l'application.
class _CardPayCard extends StatefulWidget {
  const _CardPayCard({required this.p, required this.onPaid});

  final Json p;
  final Future<void> Function() onPaid;

  @override
  State<_CardPayCard> createState() => _CardPayCardState();
}

class _CardPayCardState extends State<_CardPayCard> with WidgetsBindingObserver {
  int? _paymentId;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _paymentId = (toNum(widget.p['pending_card_id']))?.toInt();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  /// Retour dans l'app après la page de paiement : on vérifie tout de suite.
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && _paymentId != null && !_busy) _check(silent: true);
  }

  Future<void> _pay() async {
    setState(() => _busy = true);
    Uri? url;
    final ok = await runAction(context, () async {
      final r = (await context.api.post('/api/provider/payments/card/')) as Map;
      _paymentId = (toNum(r['payment_id']))?.toInt();
      url = Uri.tryParse('${r['checkout_url']}');
    });
    if (!mounted) return;
    setState(() => _busy = false);
    final target = url;
    if (!ok || target == null) return;
    if (!await launchUrl(target, mode: LaunchMode.externalApplication) && mounted) {
      showInfo(context, context.tr('card_open_failed'));
    }
  }

  Future<void> _check({bool silent = false}) async {
    final id = _paymentId;
    if (id == null) return;
    setState(() => _busy = true);
    String? status;
    try {
      final r = (await context.api.post('/api/provider/payments/$id/sync/')) as Map;
      status = '${r['status']}';
    } on ApiException catch (e) {
      if (mounted && !silent) showError(context, e);
    }
    if (!mounted) return;
    setState(() => _busy = false);
    if (status == 'approved') {
      showInfo(context, context.tr('card_ok'));
      await widget.onPaid();
    } else if (status == 'rejected') {
      setState(() => _paymentId = null);
      if (!silent) showInfo(context, context.tr('card_failed'));
    } else if (!silent && status != null) {
      showInfo(context, context.tr('card_waiting'));
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.current;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(color: p.primary.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(12)),
              child: Icon(Icons.credit_card, color: p.primary),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(context.tr('card_title'), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                Text(context.tr('card_sub'), style: TextStyle(fontSize: 12.5, color: p.muted)),
              ]),
            ),
          ]),
          const SizedBox(height: 14),
          FilledButton.icon(
            onPressed: _busy ? null : _pay,
            icon: _busy
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.lock_outline),
            label: Text(context.tr('card_button', {'amount': money(context, widget.p['amount_due_da'])})),
          ),
          if (_paymentId != null) ...[
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: _busy ? null : () => _check(),
              icon: const Icon(Icons.refresh),
              label: Text(context.tr('card_check')),
            ),
          ],
        ]),
      ),
    );
  }
}

/// Étapes du paiement BaridiMob + envoi de la capture.
class _PayCard extends StatefulWidget {
  const _PayCard({required this.p, required this.onSent});

  final Json p;
  final Future<void> Function() onSent;

  @override
  State<_PayCard> createState() => _PayCardState();
}

class _PayCardState extends State<_PayCard> {
  final _reference = TextEditingController();
  File? _capture;
  bool _sending = false;

  Future<void> _pick() async {
    final picked = await ImagePicker().pickImage(source: ImageSource.gallery, maxWidth: 1800, imageQuality: 85);
    if (picked != null) setState(() => _capture = File(picked.path));
  }

  Future<void> _send() async {
    final file = _capture;
    if (file == null) {
      showInfo(context, context.tr('pay_need_capture'));
      return;
    }
    setState(() => _sending = true);
    final ok = await runAction(context, () async {
      await context.api.upload('/api/provider/payments/',
          fileField: 'screenshot', file: file, fields: {'reference': _reference.text.trim()});
    });
    if (!mounted) return;
    setState(() => _sending = false);
    if (ok) {
      showInfo(context, context.tr('pay_sent'));
      await widget.onSent();
    }
  }

  @override
  Widget build(BuildContext context) {
    final bm = (widget.p['baridimob'] as Map?) ?? const {};
    final rip = '${bm['rip'] ?? ''}';
    final name = '${bm['name'] ?? ''}';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(context.tr(widget.p['card_enabled'] == true ? 'pay_title_or' : 'pay_title'),
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 8),
          Text(context.tr('pay_step1', {'amount': money(context, widget.p['amount_due_da'])})),
          if (rip.isNotEmpty)
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: SelectableText(rip, textDirection: TextDirection.ltr,
                  style: const TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1)),
              subtitle: name.isNotEmpty ? Text(name) : null,
              trailing: IconButton(
                icon: const Icon(Icons.copy),
                tooltip: context.tr('copy'),
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: rip));
                  showInfo(context, context.tr('copied'));
                },
              ),
            ),
          Text(context.tr('pay_step2')),
          const SizedBox(height: 4),
          Text(context.tr('pay_step3')),
          const SizedBox(height: 12),
          if (_capture != null)
            ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: Image.file(_capture!, height: 220, fit: BoxFit.contain),
            ),
          OutlinedButton.icon(
            onPressed: _sending ? null : _pick,
            icon: const Icon(Icons.image_outlined),
            label: Text(context.tr(_capture == null ? 'pay_pick' : 'pay_change')),
          ),
          TextField(
            controller: _reference,
            maxLength: 80,
            decoration: InputDecoration(labelText: context.tr('pay_reference')),
          ),
          FilledButton.icon(
            onPressed: _sending ? null : _send,
            icon: _sending
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.send),
            label: Text(context.tr('pay_send')),
          ),
        ]),
      ),
    );
  }
}
