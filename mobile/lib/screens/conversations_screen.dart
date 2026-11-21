import 'package:flutter/material.dart';

import '../core/api.dart';
import '../core/format.dart';
import '../core/i18n.dart';
import '../widgets/common.dart';
import 'chat_screen.dart';

class ConversationsTab extends StatelessWidget {
  const ConversationsTab({super.key});

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    return AsyncBody<List<Json>>(
      load: () async {
        final list = await Api.instance.getAll('/conversations/');
        list.sort((a, b) => (b['last_message_at'] ?? b['created_at'] ?? '')
            .toString()
            .compareTo((a['last_message_at'] ?? a['created_at'] ?? '').toString()));
        return list;
      },
      builder: (context, items, reload) => RefreshIndicator(
        onRefresh: reload,
        child: items.isEmpty
            ? ListView(children: [EmptyState(s.t('no_conversations'), icon: Icons.chat_bubble_outline)])
            : ListView.separated(
                itemCount: items.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (context, i) {
                  final c = items[i];
                  final other = (c['other_party'] as Map?) ?? {};
                  final name = (other['business_name'] ?? '').toString().isNotEmpty
                      ? other['business_name']
                      : (other['full_name'] ?? '');
                  final last = c['last_message'] as Map?;
                  final unread = (c['unread_count'] as num?)?.toInt() ?? 0;
                  return ListTile(
                    leading: CircleAvatar(
                      child: Text(name.toString().isEmpty ? '?' : name.toString()[0].toUpperCase()),
                    ),
                    title: Text('$name', maxLines: 1, overflow: TextOverflow.ellipsis),
                    subtitle: Text(
                      '${c['request_title'] ?? ''}\n${last == null ? '' : (last['type'] == 'photo' ? '📷' : last['body'] ?? '')}',
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    isThreeLine: true,
                    trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
                      Text(dateOnly(c['last_message_at'] ?? c['created_at']), style: const TextStyle(fontSize: 11)),
                      const SizedBox(height: 4),
                      if (unread > 0) Badge(label: Text('$unread')),
                      if (c['is_locked'] == true) const Icon(Icons.lock, size: 16, color: Colors.grey),
                    ]),
                    onTap: () async {
                      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ChatScreen(conversation: c)));
                      await reload();
                    },
                  );
                },
              ),
      ),
    );
  }
}
