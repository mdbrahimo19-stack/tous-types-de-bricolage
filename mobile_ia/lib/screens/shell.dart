import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../config.dart';
import '../l10n.dart';
import '../state/session.dart';
import '../widgets/common.dart';
import 'client.dart';
import 'provider.dart';
import 'shared.dart';

/// Navigation principale : onglets différents selon le mode client / prestataire.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;
  bool? _lastMode;

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    final provider = session.asProvider;
    if (_lastMode != provider) {
      _index = 0; // changement de mode : retour au premier onglet
      _lastMode = provider;
    }

    final tabs = provider
        ? [
            (Icons.work_outline, 'tab_feed', const FeedScreen()),
            (Icons.request_quote_outlined, 'tab_quotes', const MyQuotesScreen()),
            (Icons.chat_bubble_outline, 'tab_messages', const ConversationsScreen()),
            (Icons.assignment_outlined, 'tab_missions', const MissionsScreen()),
            (Icons.person_outline, 'tab_profile', const ProfileScreen()),
          ]
        : [
            (Icons.home_outlined, 'tab_home', const ClientHomeScreen()),
            (Icons.list_alt, 'tab_requests', const MyRequestsScreen()),
            (Icons.chat_bubble_outline, 'tab_messages', const ConversationsScreen()),
            (Icons.assignment_outlined, 'tab_missions', const MissionsScreen()),
            (Icons.person_outline, 'tab_profile', const ProfileScreen()),
          ];

    return Scaffold(
      // KeyedSubtree : chaque onglet est reconstruit (et rechargé) quand on y revient
      body: KeyedSubtree(key: ValueKey('$provider-$_index'), child: tabs[_index].$3),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: [
          for (final (icon, label, _) in tabs) NavigationDestination(icon: Icon(icon), label: context.tr(label)),
        ],
      ),
    );
  }
}

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    final user = session.user ?? const {};
    return Scaffold(
      appBar: AppBar(title: Text(context.tr('profile'))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          ListTile(
            leading: const CircleAvatar(radius: 26, child: Icon(Icons.person, size: 28)),
            title: Text('${user['full_name'] ?? ''}', style: Theme.of(context).textTheme.titleMedium),
            subtitle: Text('${user['phone'] ?? ''}', textDirection: TextDirection.ltr),
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.language),
            title: Text(context.tr('language')),
            trailing: SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'fr', label: Text('FR')),
                ButtonSegment(value: 'ar', label: Text('ع')),
              ],
              selected: {session.locale},
              onSelectionChanged: (s) => session.setLocale(s.first),
            ),
          ),
          if (session.isProvider) ...[
            ListTile(
              leading: const Icon(Icons.swap_horiz),
              title: Text(context.tr('mode')),
              trailing: SegmentedButton<bool>(
                segments: [
                  ButtonSegment(value: false, label: Text(context.tr('mode_client'))),
                  ButtonSegment(value: true, label: Text(context.tr('mode_provider'))),
                ],
                selected: {session.providerMode},
                onSelectionChanged: (s) => session.setProviderMode(s.first),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.handyman_outlined),
              title: Text(context.tr('provider_profile')),
              trailing: StatusChip(status: session.verificationStatus, prefix: 'vs'),
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ProviderSetupScreen())),
            ),
          ] else
            ListTile(
              leading: const Icon(Icons.info_outline),
              title: Text(context.tr('become_provider_hint'), style: const TextStyle(fontSize: 13)),
            ),
          ListTile(
            leading: const Icon(Icons.dns_outlined),
            title: Text(context.tr('server')),
            subtitle: Text(ServerConfig.baseUrl, textDirection: TextDirection.ltr),
            onTap: () => showServerDialog(context),
          ),
          ListTile(
            leading: const Icon(Icons.support_agent),
            title: Text(context.tr('support_title')),
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SupportChatScreen())),
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.logout, color: Colors.red),
            title: Text(context.tr('logout'), style: const TextStyle(color: Colors.red)),
            onTap: () async {
              if (await confirmDialog(context, context.tr('logout_confirm'))) await session.logout();
            },
          ),
        ],
      ),
    );
  }
}
