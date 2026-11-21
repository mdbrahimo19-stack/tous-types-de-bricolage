import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../config.dart';
import '../l10n.dart';
import '../state/session.dart';
import '../widgets/common.dart';

// ==========================================================================
//  Messagerie
// ==========================================================================

/// Ouvre la conversation d'une demande : avec `otherUserId`, ou la conversation
/// non verrouillée (celle du prestataire retenu) si l'interlocuteur n'est pas connu.
Future<void> openConversation(BuildContext context, {required int requestId, int? otherUserId}) async {
  try {
    final convs = await context.api.listAll('/api/conversations/');
    final forRequest = convs.where((c) => c['request'] == requestId).toList();
    final conv = otherUserId != null
        ? forRequest.where((c) => (c['other_party'] as Map?)?['id'] == otherUserId).firstOrNull
        : (forRequest.where((c) => c['is_locked'] != true).firstOrNull ?? forRequest.firstOrNull);
    if (conv == null || !context.mounted) return;
    await Navigator.push(context, MaterialPageRoute(builder: (_) => ChatScreen(conversation: conv)));
  } catch (e) {
    if (context.mounted) showError(context, e);
  }
}

String _partyName(Map? p) {
  if (p == null) return '';
  final business = p['business_name'] as String?;
  return (business != null && business.isNotEmpty) ? business : '${p['full_name'] ?? ''}';
}

class ConversationsScreen extends StatelessWidget {
  const ConversationsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(context.tr('conversations'))),
      body: LoadView<List<Json>>(
        load: () => context.api.listAll('/api/conversations/'),
        builder: (context, convs, reload) {
          if (convs.isEmpty) {
            return EmptyState(icon: Icons.chat_bubble_outline, text: context.tr('no_conversations'));
          }
          return ListView.separated(
            itemCount: convs.length,
            separatorBuilder: (_, _) => const Divider(height: 1),
            itemBuilder: (context, i) {
              final c = convs[i];
              final last = c['last_message'] as Map?;
              final unread = (c['unread_count'] as num?) ?? 0;
              return ListTile(
                leading: CircleAvatar(child: Text(_initial(_partyName(c['other_party'] as Map?)))),
                title: Text(_partyName(c['other_party'] as Map?), style: const TextStyle(fontWeight: FontWeight.w600)),
                subtitle: Text(
                  '${c['request_title']}\n${last == null ? '' : (last['type'] == 'photo' ? '📷' : last['body'])}',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                isThreeLine: true,
                trailing: unread > 0
                    ? Badge(label: Text('$unread'))
                    : (c['is_locked'] == true ? const Icon(Icons.lock_outline, size: 18) : null),
                onTap: () async {
                  await Navigator.push(context, MaterialPageRoute(builder: (_) => ChatScreen(conversation: c)));
                  reload();
                },
              );
            },
          );
        },
      ),
    );
  }

  static String _initial(String s) => s.isEmpty ? '?' : s.characters.first.toUpperCase();
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key, required this.conversation});

  final Json conversation;

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _input = TextEditingController();
  List<Json> _messages = [];
  bool _loading = true;
  bool _sending = false;
  Timer? _timer;

  int get _convId => widget.conversation['id'] as int;
  bool get _locked => widget.conversation['is_locked'] == true;

  @override
  void initState() {
    super.initState();
    _refresh();
    _timer = Timer.periodic(chatPollInterval, (_) => _refresh());
  }

  @override
  void dispose() {
    _timer?.cancel();
    _input.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final list = await context.api.listAll('/api/conversations/$_convId/messages/');
      if (mounted) setState(() => _messages = list);
    } catch (e) {
      if (mounted && _loading) showError(context, e);
    } finally {
      if (mounted && _loading) setState(() => _loading = false);
    }
  }

  Future<void> _sendText() async {
    final text = _input.text.trim();
    if (text.isEmpty) return;
    setState(() => _sending = true);
    final ok = await runAction(
      context,
      () => context.api.post('/api/conversations/$_convId/messages/', {'type': 'text', 'body': text}),
    );
    if (!mounted) return;
    setState(() => _sending = false);
    if (ok) {
      _input.clear();
      _refresh();
    }
  }

  Future<void> _sendPhoto() async {
    final picked = await ImagePicker().pickImage(source: ImageSource.gallery, maxWidth: 1600, imageQuality: 75);
    if (picked == null || !mounted) return;
    setState(() => _sending = true);
    await runAction(
      context,
      () => context.api.upload(
        '/api/conversations/$_convId/messages/',
        fileField: 'attachment',
        file: File(picked.path),
        fields: {'type': 'photo'},
      ),
    );
    if (!mounted) return;
    setState(() => _sending = false);
    _refresh();
  }

  Future<void> _report(Json msg) async {
    if (!await confirmDialog(context, '${context.tr('report')} ?') || !mounted) return;
    final ok = await runAction(context, () => context.api.post('/api/messages/${msg['id']}/flag/'));
    if (ok && mounted) showInfo(context, context.tr('reported'));
  }

  @override
  Widget build(BuildContext context) {
    final me = context.read<Session>().userId;
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_partyName(widget.conversation['other_party'] as Map?)),
          Text('${widget.conversation['request_title']}', style: Theme.of(context).textTheme.bodySmall),
        ]),
      ),
      body: Column(children: [
        if (_locked || widget.conversation['contacts_unlocked'] != true)
          MaterialBanner(
            content: Text(context.tr(_locked ? 'locked' : 'contacts_hidden'), style: const TextStyle(fontSize: 13)),
            leading: Icon(_locked ? Icons.lock_outline : Icons.privacy_tip_outlined),
            actions: const [SizedBox.shrink()],
          ),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : ListView.builder(
                  reverse: true,
                  padding: const EdgeInsets.all(12),
                  itemCount: _messages.length,
                  itemBuilder: (context, i) {
                    final m = _messages[_messages.length - 1 - i];
                    if (m['type'] == 'system') {
                      return Center(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(vertical: 6),
                          child: Text('${m['body']}', style: TextStyle(color: scheme.outline, fontSize: 12)),
                        ),
                      );
                    }
                    final mine = m['sender'] == me;
                    return Align(
                      alignment: mine ? AlignmentDirectional.centerEnd : AlignmentDirectional.centerStart,
                      child: GestureDetector(
                        onLongPress: mine ? null : () => _report(m),
                        child: Container(
                          margin: const EdgeInsets.symmetric(vertical: 3),
                          padding: const EdgeInsets.all(10),
                          constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.75),
                          decoration: BoxDecoration(
                            color: mine ? scheme.primaryContainer : scheme.surfaceContainerHighest,
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            if (m['attachment'] != null) NetImage(m['attachment'] as String, size: 180),
                            if ((m['body'] as String?)?.isNotEmpty == true) Text('${m['body']}'),
                            const SizedBox(height: 2),
                            Row(mainAxisSize: MainAxisSize.min, children: [
                              if (m['was_filtered'] == true) ...[
                                Icon(Icons.shield_outlined, size: 12, color: scheme.outline),
                                Text(' ${context.tr('filtered_notice')} · ',
                                    style: TextStyle(fontSize: 10, color: scheme.outline)),
                              ],
                              Text(formatDate(context, m['created_at']),
                                  style: TextStyle(fontSize: 10, color: scheme.outline)),
                            ]),
                          ]),
                        ),
                      ),
                    );
                  },
                ),
        ),
        if (!_locked)
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(8, 4, 8, 8),
              child: Row(children: [
                IconButton(onPressed: _sending ? null : _sendPhoto, icon: const Icon(Icons.photo)),
                Expanded(
                  child: TextField(
                    controller: _input,
                    minLines: 1,
                    maxLines: 4,
                    textInputAction: TextInputAction.send,
                    onSubmitted: (_) => _sendText(),
                    decoration: InputDecoration(hintText: context.tr('type_message')),
                  ),
                ),
                IconButton.filled(onPressed: _sending ? null : _sendText, icon: const Icon(Icons.send)),
              ]),
            ),
          ),
      ]),
    );
  }
}

// ==========================================================================
//  Missions
// ==========================================================================
class MissionsScreen extends StatelessWidget {
  const MissionsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    return Scaffold(
      appBar: AppBar(title: Text(context.tr('missions'))),
      body: LoadView<List<Json>>(
        key: ValueKey(session.asProvider),
        load: () async {
          // un compte peut être client ET prestataire : on filtre selon le mode actif
          final all = await context.api.listAll('/api/missions/');
          return all.where((m) => _isProviderSide(m, session) == session.asProvider).toList();
        },
        builder: (context, missions, reload) {
          if (missions.isEmpty) return EmptyState(icon: Icons.assignment_outlined, text: context.tr('no_missions'));
          return ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: missions.length,
            itemBuilder: (context, i) {
              final m = missions[i];
              final detail = (m['request_detail'] as Map?) ?? const {};
              final other = session.asProvider ? m['client_contact'] : m['provider_contact'];
              return Card(
                child: ListTile(
                  title: Text('${detail['title'] ?? ''}'),
                  subtitle: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${_partyName(other as Map?)} · ${money(context, m['amount_due'])}'),
                    const SizedBox(height: 4),
                    Row(children: [
                      StatusChip(status: '${m['status']}', prefix: 'ms'),
                      const SizedBox(width: 8),
                      if (m['scheduled_at'] != null)
                        Expanded(child: Text(formatDate(context, m['scheduled_at']), style: const TextStyle(fontSize: 12))),
                    ]),
                  ]),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () async {
                    await Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => MissionDetailScreen(missionId: m['id'] as int)),
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

/// Le serializer de mission n'expose pas les ids : on compare le téléphone du prestataire.
bool _isProviderSide(Json mission, Session session) =>
    (mission['provider_contact'] as Map?)?['phone'] == session.user?['phone'];

class MissionDetailScreen extends StatefulWidget {
  const MissionDetailScreen({super.key, required this.missionId});

  final int missionId;

  @override
  State<MissionDetailScreen> createState() => _MissionDetailScreenState();
}

class _MissionDetailScreenState extends State<MissionDetailScreen> {
  final _key = GlobalKey<LoadViewState<Json>>();
  bool _reviewed = false;

  String get _base => '/api/missions/${widget.missionId}';

  Future<void> _do(String action, {Object? body, String? confirmKey}) async {
    if (confirmKey != null && !await confirmDialog(context, context.tr(confirmKey))) return;
    if (!mounted) return;
    final ok = await runAction(context, () => context.api.post('$_base/$action/', body));
    if (ok) _key.currentState?.reload();
  }

  Future<void> _schedule() async {
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
    final at = DateTime(date.year, date.month, date.day, time.hour, time.minute);
    await _do('schedule', body: {'scheduled_at': at.toUtc().toIso8601String()});
  }

  Future<void> _review() async {
    int rating = 5;
    final comment = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) => AlertDialog(
          title: Text(ctx.tr('leave_review')),
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
              maxLines: 5,
              decoration: InputDecoration(labelText: ctx.tr('comment')),
            ),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(ctx.tr('cancel'))),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(ctx.tr('send'))),
          ],
        ),
      ),
    );
    if (ok != true || !mounted) return;
    final sent = await runAction(
      context,
      () => context.api.post('$_base/review/', {'rating': rating, 'comment': comment.text.trim()}),
    );
    if (sent && mounted) {
      setState(() => _reviewed = true);
      showInfo(context, context.tr('review_sent'));
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = context.read<Session>();
    return Scaffold(
      appBar: AppBar(title: Text(context.tr('mission'))),
      body: LoadView<Json>(
        key: _key,
        load: () async => (await context.api.get('$_base/') as Map).cast<String, dynamic>(),
        builder: (context, m, reload) {
          final isProvider = _isProviderSide(m, session);
          final status = '${m['status']}';
          final d = (m['request_detail'] as Map?) ?? const {};
          final other = (isProvider ? m['client_contact'] : m['provider_contact']) as Map? ?? const {};
          final confirmedByMe = isProvider ? m['confirmed_by_provider'] == true : m['confirmed_by_client'] == true;
          final bothConfirmed = m['confirmed_by_provider'] == true && m['confirmed_by_client'] == true;
          final schedulable = status == 'planned' || status == 'confirmed';
          final address = [d['street'], d['quartier'], d['commune'], d['wilaya']]
              .where((s) => s != null && '$s'.isNotEmpty)
              .join(', ');

          final actions = <Widget>[
            if (schedulable && m['scheduled_at'] != null && !confirmedByMe)
              FilledButton(onPressed: () => _do('confirm'), child: Text(context.tr('confirm_slot'))),
            if (schedulable)
              OutlinedButton.icon(
                icon: const Icon(Icons.event),
                onPressed: _schedule,
                label: Text(context.tr('propose_slot')),
              ),
            if (isProvider && schedulable)
              FilledButton.icon(
                icon: const Icon(Icons.play_arrow),
                onPressed: () => _do('start'),
                label: Text(context.tr('start')),
              ),
            if (isProvider && status == 'in_progress')
              FilledButton.icon(
                icon: const Icon(Icons.check),
                onPressed: () => _do('complete'),
                label: Text(context.tr('complete')),
              ),
            if (!isProvider && status == 'completed' && m['paid_at'] == null)
              FilledButton.icon(
                icon: const Icon(Icons.payments),
                onPressed: () => _do('pay'),
                label: Text(context.tr('i_paid')),
              ),
            if (isProvider && (status == 'completed' || status == 'paid') && m['payment_confirmed_by_provider'] != true)
              FilledButton.icon(
                icon: const Icon(Icons.payments),
                onPressed: () => _do('confirm-payment'),
                label: Text(context.tr('confirm_payment')),
              ),
            if (!isProvider && (status == 'completed' || status == 'paid') && !_reviewed)
              OutlinedButton.icon(
                icon: const Icon(Icons.star_outline),
                onPressed: _review,
                label: Text(context.tr('leave_review')),
              ),
            if (schedulable)
              TextButton(
                onPressed: () => _do('cancel', confirmKey: 'cancel_mission_confirm'),
                child: Text(context.tr('cancel_mission'), style: const TextStyle(color: Colors.red)),
              ),
          ];

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text('${d['title'] ?? ''}', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Wrap(spacing: 12, crossAxisAlignment: WrapCrossAlignment.center, children: [
                StatusChip(status: status, prefix: 'ms'),
                Text('${d['category'] ?? ''}'),
              ]),
              const SizedBox(height: 12),
              Text('${d['description'] ?? ''}'),
              SectionTitle(context.tr('amount_due')),
              Text(money(context, m['amount_due']), style: Theme.of(context).textTheme.titleLarge),
              if (!isProvider && m['paid_at'] != null && m['payment_confirmed_by_provider'] != true)
                Text(context.tr('paid_waiting_provider'), style: const TextStyle(color: Colors.orange)),
              SectionTitle(context.tr('appointment')),
              if (m['scheduled_at'] == null)
                Text(context.tr('not_scheduled'))
              else ...[
                Text(formatDate(context, m['scheduled_at']), style: Theme.of(context).textTheme.titleMedium),
                Text(context.tr(bothConfirmed ? 'slot_confirmed' : 'waiting_other'),
                    style: TextStyle(color: bothConfirmed ? Colors.green : Colors.orange)),
              ],
              SectionTitle(context.tr('contact')),
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const CircleAvatar(child: Icon(Icons.person)),
                title: Text(_partyName(other)),
                subtitle: Text('${other['phone'] ?? ''}', textDirection: TextDirection.ltr),
                trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                  IconButton(
                    icon: const Icon(Icons.copy),
                    onPressed: () {
                      Clipboard.setData(ClipboardData(text: '${other['phone'] ?? ''}'));
                      showInfo(context, '${other['phone']}');
                    },
                  ),
                  IconButton(
                    icon: const Icon(Icons.chat_bubble_outline),
                    onPressed: () => openConversation(context, requestId: m['request'] as int),
                  ),
                ]),
              ),
              if (address.isNotEmpty) ...[
                SectionTitle(context.tr('address')),
                Text(address),
                if ((d['notes'] as String?)?.isNotEmpty == true) Text('${d['notes']}'),
              ],
              const SizedBox(height: 20),
              for (final a in actions) Padding(padding: const EdgeInsets.only(bottom: 8), child: a),
            ],
          );
        },
      ),
    );
  }
}

// ==========================================================================
//  Assistance IA
// ==========================================================================
class SupportChatScreen extends StatefulWidget {
  const SupportChatScreen({super.key});

  @override
  State<SupportChatScreen> createState() => _SupportChatScreenState();
}

class _SupportChatScreenState extends State<SupportChatScreen> {
  final _input = TextEditingController();
  final List<({String role, String content})> _history = [];
  bool _busy = false;

  Future<void> _send() async {
    final text = _input.text.trim();
    if (text.isEmpty || _busy) return;
    setState(() {
      _history.add((role: 'user', content: text));
      _busy = true;
      _input.clear();
    });
    try {
      final data = await context.api.post('/api/ai/support/', {
        'messages': [for (final m in _history) {'role': m.role, 'content': m.content}],
      }) as Map;
      if (mounted) setState(() => _history.add((role: 'assistant', content: '${data['reply']}')));
    } on ApiException catch (e) {
      if (!mounted) return;
      _history.removeLast(); // la question n'a pas abouti : on la rend à l'utilisateur
      _input.text = text;
      showError(context, e.isUnavailable ? ApiException(context.tr('ai_unavailable')) : e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final bubbles = [(role: 'assistant', content: context.tr('support_welcome')), ..._history];
    return Scaffold(
      appBar: AppBar(title: Row(children: [
        const Icon(Icons.auto_awesome, size: 20),
        const SizedBox(width: 8),
        Text(context.tr('support_title')),
      ])),
      body: Column(children: [
        Expanded(
          child: ListView.builder(
            reverse: true,
            padding: const EdgeInsets.all(12),
            itemCount: bubbles.length + (_busy ? 1 : 0),
            itemBuilder: (context, i) {
              if (_busy && i == 0) {
                return const Align(
                  alignment: AlignmentDirectional.centerStart,
                  child: Padding(padding: EdgeInsets.all(12), child: CircularProgressIndicator(strokeWidth: 2)),
                );
              }
              final m = bubbles[bubbles.length - 1 - (i - (_busy ? 1 : 0))];
              final mine = m.role == 'user';
              return Align(
                alignment: mine ? AlignmentDirectional.centerEnd : AlignmentDirectional.centerStart,
                child: Container(
                  margin: const EdgeInsets.symmetric(vertical: 4),
                  padding: const EdgeInsets.all(12),
                  constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.8),
                  decoration: BoxDecoration(
                    color: mine ? scheme.primaryContainer : scheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: SelectableText(m.content),
                ),
              );
            },
          ),
        ),
        SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 4, 8, 8),
            child: Row(children: [
              Expanded(
                child: TextField(
                  controller: _input,
                  minLines: 1,
                  maxLines: 4,
                  maxLength: 2000,
                  textInputAction: TextInputAction.send,
                  onSubmitted: (_) => _send(),
                  decoration: InputDecoration(hintText: context.tr('support_hint'), counterText: ''),
                ),
              ),
              IconButton.filled(onPressed: _busy ? null : _send, icon: const Icon(Icons.send)),
            ]),
          ),
        ),
      ]),
    );
  }
}
