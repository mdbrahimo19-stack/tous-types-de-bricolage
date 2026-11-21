import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/api.dart';
import '../core/format.dart';
import '../core/i18n.dart';
import '../widgets/common.dart';

/// Suivi de mission côté client : RDV, coordonnées, paiement espèces, avis.
class MissionScreen extends StatefulWidget {
  const MissionScreen({super.key, required this.missionId});
  final int missionId;

  @override
  State<MissionScreen> createState() => _MissionScreenState();
}

class _MissionScreenState extends State<MissionScreen> {
  final _api = Api.instance;
  Key _key = UniqueKey();
  bool _busy = false;

  Future<(Json, String)> _load() async {
    final m = Json.from(await _api.get('/missions/${widget.missionId}/'));
    var reqStatus = '';
    try {
      final r = await _api.get('/requests/${m['request']}/');
      reqStatus = (r['status'] ?? '').toString();
    } catch (_) {}
    return (m, reqStatus);
  }

  void _reload() => setState(() => _key = UniqueKey());

  Future<void> _action(String path, {Object? data, String? confirm}) async {
    if (confirm != null && !await confirmDialog(context, confirm)) return;
    setState(() => _busy = true);
    try {
      await _api.post('/missions/${widget.missionId}/$path/', data: data);
      _reload();
    } on ApiException catch (e) {
      if (mounted) toast(context, e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _proposeSlot() async {
    final now = DateTime.now();
    final date = await showDatePicker(
      context: context,
      firstDate: now,
      lastDate: now.add(const Duration(days: 60)),
      initialDate: now,
    );
    if (date == null || !mounted) return;
    final time = await showTimePicker(context: context, initialTime: const TimeOfDay(hour: 9, minute: 0));
    if (time == null) return;
    final slot = DateTime(date.year, date.month, date.day, time.hour, time.minute);
    await _action('schedule', data: {'scheduled_at': slot.toUtc().toIso8601String()});
  }

  Future<void> _review() async {
    final s = S.of(context);
    var rating = 5;
    final comment = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) => AlertDialog(
          title: Text(s.t('leave_review')),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              for (var i = 1; i <= 5; i++)
                IconButton(
                  icon: Icon(i <= rating ? Icons.star : Icons.star_border, color: Colors.amber, size: 32),
                  onPressed: () => setLocal(() => rating = i),
                ),
            ]),
            TextField(
              controller: comment,
              minLines: 2,
              maxLines: 4,
              decoration: InputDecoration(labelText: s.t('comment')),
            ),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(s.t('cancel'))),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(s.t('send'))),
          ],
        ),
      ),
    );
    final text = comment.text.trim();
    comment.dispose();
    if (ok != true || !mounted) return;
    setState(() => _busy = true);
    try {
      await _api.post('/missions/${widget.missionId}/review/', data: {'rating': rating, 'comment': text});
      if (mounted) toast(context, s.t('thanks_review'));
      _reload();
    } on ApiException catch (e) {
      if (mounted) toast(context, e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(s.t('mission'))),
      body: AsyncBody<(Json, String)>(
        key: _key,
        load: _load,
        builder: (context, data, reload) {
          final (m, reqStatus) = data;
          final status = m['status'] as String? ?? '';
          final req = (m['request_detail'] as Map?) ?? {};
          final prov = (m['provider_contact'] as Map?) ?? {};
          final scheduled = m['scheduled_at'];
          final byClient = m['confirmed_by_client'] == true;
          final byProvider = m['confirmed_by_provider'] == true;
          final open = status == 'planned' || status == 'confirmed';
          final done = status == 'completed' || status == 'paid';
          final provName = (prov['business_name'] ?? '').toString().isNotEmpty ? prov['business_name'] : prov['full_name'];
          final phone = (prov['phone'] ?? '').toString();

          return RefreshIndicator(
            onRefresh: reload,
            child: ListView(padding: const EdgeInsets.all(16), children: [
              Row(children: [
                Expanded(child: Text('${req['title'] ?? ''}', style: Theme.of(context).textTheme.titleLarge)),
                StatusChip(s.t('m_$status'), status == 'cancelled' ? Colors.grey : Colors.indigo),
              ]),
              const SizedBox(height: 4),
              Text('${req['category'] ?? ''} · ${req['commune'] ?? ''}, ${req['wilaya'] ?? ''}',
                  style: const TextStyle(color: Colors.grey)),
              if ('${req['street'] ?? ''}${req['quartier'] ?? ''}'.isNotEmpty)
                Text('${req['quartier'] ?? ''} ${req['street'] ?? ''}'),

              const SizedBox(height: 16),
              Card(
                child: ListTile(
                  leading: const Icon(Icons.person),
                  title: Text('${provName ?? ''}'),
                  subtitle: Text(phone, textDirection: TextDirection.ltr),
                  trailing: IconButton(
                    tooltip: s.t('copied'),
                    icon: const Icon(Icons.copy),
                    onPressed: () async {
                      await Clipboard.setData(ClipboardData(text: phone));
                      if (context.mounted) toast(context, s.t('copied'));
                    },
                  ),
                ),
              ),

              const SizedBox(height: 8),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(s.t('appointment'), style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 8),
                    if (scheduled == null)
                      Text(s.t('no_slot'), style: const TextStyle(color: Colors.grey))
                    else ...[
                      Row(children: [
                        const Icon(Icons.event, size: 20),
                        const SizedBox(width: 8),
                        Text(dateTime(scheduled), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                      ]),
                      const SizedBox(height: 4),
                      Text(
                        byClient && byProvider ? s.t('slot_confirmed') : s.t('waiting_other'),
                        style: TextStyle(color: byClient && byProvider ? Colors.green : Colors.orange),
                      ),
                    ],
                    if (open) ...[
                      const SizedBox(height: 8),
                      Wrap(spacing: 8, runSpacing: 4, children: [
                        OutlinedButton.icon(
                          onPressed: _busy ? null : _proposeSlot,
                          icon: const Icon(Icons.edit_calendar),
                          label: Text(s.t('propose_slot')),
                        ),
                        if (scheduled != null && !byClient)
                          FilledButton(
                            onPressed: _busy ? null : () => _action('confirm'),
                            child: Text(s.t('confirm_slot')),
                          ),
                      ]),
                    ],
                  ]),
                ),
              ),

              const SizedBox(height: 8),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(s.t('amount_due'), style: const TextStyle(color: Colors.grey)),
                    Text(money(m['amount_due']), style: Theme.of(context).textTheme.headlineSmall),
                    if (done && m['paid_at'] == null) ...[
                      const SizedBox(height: 8),
                      FilledButton.icon(
                        onPressed: _busy ? null : () => _action('pay'),
                        icon: const Icon(Icons.payments),
                        label: Text(s.t('i_paid')),
                      ),
                    ],
                    if (m['paid_at'] != null && status != 'paid') ...[
                      const SizedBox(height: 8),
                      Text(s.t('paid_declared'), style: const TextStyle(color: Colors.orange)),
                    ],
                  ]),
                ),
              ),

              if (done && reqStatus != 'evaluated' && reqStatus != 'closed') ...[
                const SizedBox(height: 8),
                FilledButton.tonalIcon(
                  onPressed: _busy ? null : _review,
                  icon: const Icon(Icons.star),
                  label: Text(s.t('leave_review')),
                ),
              ],
              if (reqStatus == 'evaluated')
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(s.t('review_done'), style: const TextStyle(color: Colors.green)),
                ),

              if (open) ...[
                const SizedBox(height: 24),
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(foregroundColor: Colors.red),
                  onPressed: _busy ? null : () => _action('cancel', confirm: s.t('cancel_mission_confirm')),
                  icon: const Icon(Icons.close),
                  label: Text(s.t('cancel_mission')),
                ),
              ],
            ]),
          );
        },
      ),
    );
  }
}
