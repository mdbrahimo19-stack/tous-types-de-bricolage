import 'package:flutter/material.dart';

import '../core/api.dart';
import '../core/format.dart';
import '../core/i18n.dart';
import '../widgets/common.dart';
import 'chat_screen.dart';
import 'mission_screen.dart';
import 'requests_screen.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  final _api = Api.instance;
  Key _key = UniqueKey();

  IconData _icon(String type) {
    if (type.startsWith('quote')) return Icons.request_quote;
    if (type.contains('message')) return Icons.chat_bubble;
    if (type.startsWith('mission') || type.startsWith('payment')) return Icons.engineering;
    if (type.startsWith('review')) return Icons.star;
    return Icons.notifications;
  }

  Future<void> _open(Json n) async {
    try {
      await _api.post('/notifications/${n['id']}/read/');
    } catch (_) {}
    if (!mounted) return;
    final data = (n['data'] as Map?) ?? {};
    Widget? target;
    if (data['mission_id'] is int) {
      target = MissionScreen(missionId: data['mission_id'] as int);
    } else if (data['conversation_id'] is int) {
      try {
        final conv = Json.from(await _api.get('/conversations/${data['conversation_id']}/'));
        target = ChatScreen(conversation: conv);
      } catch (_) {}
    } else if (data['request_id'] is int) {
      target = RequestDetailScreen(requestId: data['request_id'] as int);
    }
    if (!mounted) return;
    if (target != null) {
      final page = target;
      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));
    }
    setState(() => _key = UniqueKey());
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(s.t('notifications')),
        actions: [
          IconButton(
            tooltip: s.t('mark_all_read'),
            icon: const Icon(Icons.done_all),
            onPressed: () async {
              try {
                await _api.post('/notifications/read_all/');
              } catch (_) {}
              setState(() => _key = UniqueKey());
            },
          ),
        ],
      ),
      body: AsyncBody<List<Json>>(
        key: _key,
        load: () => _api.getAll('/notifications/', maxPages: 3),
        builder: (context, items, reload) => RefreshIndicator(
          onRefresh: reload,
          child: items.isEmpty
              ? ListView(children: [EmptyState(s.t('no_notifications'), icon: Icons.notifications_none)])
              : ListView.separated(
                  itemCount: items.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (context, i) {
                    final n = items[i];
                    final read = n['is_read'] == true;
                    return ListTile(
                      leading: Icon(_icon('${n['type'] ?? ''}'),
                          color: read ? Colors.grey : Theme.of(context).colorScheme.primary),
                      title: Text('${n['title'] ?? ''}',
                          style: TextStyle(fontWeight: read ? FontWeight.normal : FontWeight.bold)),
                      subtitle: Text('${n['body'] ?? ''}\n${dateTime(n['created_at'])}'),
                      isThreeLine: true,
                      onTap: () => _open(n),
                    );
                  },
                ),
        ),
      ),
    );
  }
}
