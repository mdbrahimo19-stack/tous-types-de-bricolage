import 'dart:async';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../core/api.dart';
import '../core/format.dart';
import '../core/i18n.dart';
import '../core/session.dart';
import '../widgets/common.dart';

/// Conversation client ↔ prestataire (polling REST toutes les 7 s).
class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key, required this.conversation});
  final Json conversation;

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _api = Api.instance;
  final _text = TextEditingController();
  final _scroll = ScrollController();
  List<Json> _messages = [];
  bool _loading = true;
  bool _sending = false;
  String? _error;
  Timer? _timer;

  int get _id => widget.conversation['id'] as int;
  bool get _locked => widget.conversation['is_locked'] == true;
  bool get _unlocked => widget.conversation['contacts_unlocked'] == true;

  @override
  void initState() {
    super.initState();
    _fetch();
    _timer = Timer.periodic(const Duration(seconds: 7), (_) => _fetch(silent: true));
  }

  @override
  void dispose() {
    _timer?.cancel();
    _text.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _fetch({bool silent = false}) async {
    try {
      final msgs = await _api.getAll('/conversations/$_id/messages/');
      if (!mounted) return;
      final grew = msgs.length != _messages.length;
      setState(() {
        _messages = msgs;
        _error = null;
        _loading = false;
      });
      if (grew) _scrollToEnd();
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        if (!silent) _error = e.message;
      });
    }
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) _scroll.jumpTo(_scroll.position.maxScrollExtent);
    });
  }

  Future<void> _sendText() async {
    final body = _text.text.trim();
    if (body.isEmpty) return;
    setState(() => _sending = true);
    try {
      await _api.post('/conversations/$_id/messages/', data: {'type': 'text', 'body': body});
      _text.clear();
      await _fetch();
    } on ApiException catch (e) {
      if (mounted) toast(context, e.message);
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  Future<void> _sendPhoto() async {
    final file = await ImagePicker().pickImage(source: ImageSource.gallery, maxWidth: 1600, imageQuality: 80);
    if (file == null) return;
    setState(() => _sending = true);
    try {
      await _api.upload('/conversations/$_id/messages/', 'attachment', file.path, fields: {'type': 'photo'});
      await _fetch();
    } on ApiException catch (e) {
      if (mounted) toast(context, e.message);
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  Future<void> _flag(Json m) async {
    final s = S.of(context);
    if (!await confirmDialog(context, '${s.t('report')} ?')) return;
    try {
      await _api.post('/messages/${m['id']}/flag/');
      if (mounted) toast(context, s.t('reported'));
    } on ApiException catch (e) {
      if (mounted) toast(context, e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final other = (widget.conversation['other_party'] as Map?) ?? {};
    final name = (other['business_name'] ?? '').toString().isNotEmpty ? other['business_name'] : other['full_name'];
    final scheme = Theme.of(context).colorScheme;
    final myId = context.read<Session>().user?['id'];

    return Scaffold(
      appBar: AppBar(
        title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${name ?? ''}'),
          Text('${widget.conversation['request_title'] ?? ''}', style: const TextStyle(fontSize: 12)),
        ]),
      ),
      body: Column(children: [
        if (!_unlocked && !_locked)
          Container(
            width: double.infinity,
            color: Colors.amber.shade50,
            padding: const EdgeInsets.all(8),
            child: Text(s.t('filtered_note'), style: const TextStyle(fontSize: 12)),
          ),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _error != null
                  ? Center(child: Text(_error!))
                  : ListView.builder(
                      controller: _scroll,
                      padding: const EdgeInsets.all(12),
                      itemCount: _messages.length,
                      itemBuilder: (context, i) {
                        final m = _messages[i];
                        if (m['sender_role'] == 'system') {
                          return Padding(
                            padding: const EdgeInsets.symmetric(vertical: 6),
                            child: Text('${m['body'] ?? ''}',
                                textAlign: TextAlign.center, style: const TextStyle(color: Colors.grey, fontSize: 12)),
                          );
                        }
                        final mine = m['sender'] == myId;
                        return Align(
                          alignment: mine ? AlignmentDirectional.centerEnd : AlignmentDirectional.centerStart,
                          child: GestureDetector(
                            onLongPress: mine ? null : () => _flag(m),
                            child: Container(
                              constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
                              margin: const EdgeInsets.symmetric(vertical: 3),
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: mine ? scheme.primaryContainer : scheme.surfaceContainerHighest,
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                if (m['type'] == 'photo' && m['attachment'] != null)
                                  NetImage(m['attachment'], size: 200),
                                if ((m['body'] ?? '').toString().isNotEmpty) Text(m['body']),
                                const SizedBox(height: 2),
                                Text(dateTime(m['created_at']), style: const TextStyle(fontSize: 10, color: Colors.grey)),
                              ]),
                            ),
                          ),
                        );
                      },
                    ),
        ),
        if (_locked)
          Padding(
            padding: const EdgeInsets.all(12),
            child: Text(s.t('locked_conv'), style: const TextStyle(color: Colors.grey)),
          )
        else
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(8, 4, 8, 8),
              child: Row(children: [
                IconButton(onPressed: _sending ? null : _sendPhoto, icon: const Icon(Icons.photo)),
                Expanded(
                  child: TextField(
                    controller: _text,
                    minLines: 1,
                    maxLines: 4,
                    decoration: InputDecoration(
                      hintText: s.t('type_message'),
                      isDense: true,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(24)),
                    ),
                  ),
                ),
                IconButton.filled(
                  onPressed: _sending ? null : _sendText,
                  icon: _sending
                      ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.send),
                ),
              ]),
            ),
          ),
      ]),
    );
  }
}
