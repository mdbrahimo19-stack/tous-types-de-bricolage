import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api.dart';
import '../core/format.dart';
import '../core/i18n.dart';
import '../core/session.dart';
import '../widgets/common.dart';
import 'conversations_screen.dart';
import 'create_request_screen.dart';
import 'notifications_screen.dart';
import 'profile_screen.dart';
import 'requests_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _tab = 0;
  int _unread = 0;
  Timer? _timer;
  // Clés pour forcer le rechargement des onglets après une action.
  int _refreshKey = 0;

  @override
  void initState() {
    super.initState();
    _pollUnread();
    _timer = Timer.periodic(const Duration(seconds: 30), (_) => _pollUnread());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _pollUnread() async {
    if (!context.read<Session>().loggedIn) return;
    try {
      final data = await Api.instance.get('/notifications/unread_count/');
      if (mounted) setState(() => _unread = (data['unread'] as num?)?.toInt() ?? 0);
    } catch (_) {}
  }

  Future<void> _newRequest([Json? category]) async {
    if (!await ensureLoggedIn(context)) return;
    if (!mounted) return;
    final created = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => CreateRequestScreen(initialCategory: category)),
    );
    if (created == true && mounted) setState(() => _refreshKey++);
  }

  Future<void> _selectTab(int i) async {
    if (i != 0 && !await ensureLoggedIn(context)) return;
    if (mounted) setState(() => _tab = i);
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final session = context.watch<Session>();
    if (!session.loggedIn && _tab != 0) _tab = 0;

    final titles = [s.t('app'), s.t('my_requests'), s.t('messages'), s.t('profile')];
    final body = switch (_tab) {
      0 => _HomeTab(key: ValueKey('home$_refreshKey${session.loggedIn}'), onNewRequest: _newRequest,
          onSeeAll: () => setState(() => _tab = 1)),
      1 => RequestsTab(key: ValueKey('req$_refreshKey')),
      2 => const ConversationsTab(),
      _ => const ProfileTab(),
    };

    return Scaffold(
      appBar: AppBar(
        title: Text(titles[_tab]),
        actions: [
          if (session.loggedIn)
            IconButton(
              tooltip: s.t('notifications'),
              icon: Badge(
                isLabelVisible: _unread > 0,
                label: Text('$_unread'),
                child: const Icon(Icons.notifications_outlined),
              ),
              onPressed: () async {
                await Navigator.of(context)
                    .push(MaterialPageRoute(builder: (_) => const NotificationsScreen()));
                _pollUnread();
              },
            ),
        ],
      ),
      body: body,
      floatingActionButton: _tab == 1
          ? FloatingActionButton.extended(
              onPressed: _newRequest,
              icon: const Icon(Icons.add),
              label: Text(s.t('publish')),
            )
          : null,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: _selectTab,
        destinations: [
          NavigationDestination(icon: const Icon(Icons.home_outlined), selectedIcon: const Icon(Icons.home), label: s.t('home')),
          NavigationDestination(icon: const Icon(Icons.assignment_outlined), selectedIcon: const Icon(Icons.assignment), label: s.t('my_requests')),
          NavigationDestination(icon: const Icon(Icons.chat_bubble_outline), selectedIcon: const Icon(Icons.chat_bubble), label: s.t('messages')),
          NavigationDestination(icon: const Icon(Icons.person_outline), selectedIcon: const Icon(Icons.person), label: s.t('profile')),
        ],
      ),
    );
  }
}

class _HomeTab extends StatelessWidget {
  const _HomeTab({super.key, required this.onNewRequest, required this.onSeeAll});
  final Future<void> Function([Json? category]) onNewRequest;
  final VoidCallback onSeeAll;

  Future<(List<Json>, List<Json>)> _load(bool loggedIn) async {
    final cats = await Api.instance.getAll('/categories/', auth: false);
    var mine = <Json>[];
    if (loggedIn) {
      final data = await Api.instance.get('/requests/');
      mine = ((data['results'] as List).cast<Json>())
          .where((r) => !['cancelled', 'expired', 'closed', 'evaluated'].contains(r['status']))
          .take(3)
          .toList();
    }
    return (cats, mine);
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final loggedIn = context.read<Session>().loggedIn;
    return AsyncBody<(List<Json>, List<Json>)>(
      load: () => _load(loggedIn),
      builder: (context, data, reload) {
        final (cats, mine) = data;
        final scheme = Theme.of(context).colorScheme;
        return RefreshIndicator(
          onRefresh: reload,
          child: ListView(padding: const EdgeInsets.all(16), children: [
            Material(
              color: scheme.primary,
              borderRadius: BorderRadius.circular(16),
              child: InkWell(
                borderRadius: BorderRadius.circular(16),
                onTap: onNewRequest,
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Row(children: [
                    Icon(Icons.add_circle, size: 44, color: scheme.onPrimary),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(s.t('publish_request'),
                            style: TextStyle(color: scheme.onPrimary, fontSize: 20, fontWeight: FontWeight.bold)),
                        const SizedBox(height: 4),
                        Text(s.t('publish_sub'), style: TextStyle(color: scheme.onPrimary)),
                      ]),
                    ),
                  ]),
                ),
              ),
            ),
            const SizedBox(height: 24),
            Text(s.t('categories'), style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            GridView.count(
              crossAxisCount: 3,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 8,
              crossAxisSpacing: 8,
              childAspectRatio: 0.95,
              children: [
                for (final c in cats)
                  Card(
                    margin: EdgeInsets.zero,
                    child: InkWell(
                      borderRadius: BorderRadius.circular(12),
                      onTap: () => onNewRequest(c),
                      child: Padding(
                        padding: const EdgeInsets.all(8),
                        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                          Icon(categoryIcon(c['icon']), size: 32, color: scheme.primary),
                          const SizedBox(height: 6),
                          Text(s.name(c),
                              textAlign: TextAlign.center,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontSize: 12)),
                        ]),
                      ),
                    ),
                  ),
              ],
            ),
            if (loggedIn) ...[
              const SizedBox(height: 24),
              Row(children: [
                Expanded(child: Text(s.t('current_requests'), style: Theme.of(context).textTheme.titleMedium)),
                TextButton(onPressed: onSeeAll, child: Text(s.t('see_all'))),
              ]),
              if (mine.isEmpty)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: Text(s.t('no_requests'), style: const TextStyle(color: Colors.grey)),
                )
              else
                for (final r in mine) RequestTile(r, onChanged: reload),
            ],
          ]),
        );
      },
    );
  }
}
