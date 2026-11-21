import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api.dart';
import '../core/config.dart';
import '../core/i18n.dart';
import '../core/session.dart';
import '../widgets/common.dart';
import '../widgets/location_picker.dart';

class ProfileTab extends StatelessWidget {
  const ProfileTab({super.key});

  Future<void> _editName(BuildContext context) async {
    final s = S.of(context);
    final session = context.read<Session>();
    final ctrl = TextEditingController(text: session.user?['full_name'] ?? '');
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(s.t('edit_name')),
        content: TextField(controller: ctrl, autofocus: true),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(s.t('cancel'))),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(s.t('save'))),
        ],
      ),
    );
    final name = ctrl.text.trim();
    ctrl.dispose();
    if (ok != true || name.isEmpty) return;
    try {
      await session.updateName(name);
      if (context.mounted) toast(context, s.t('saved'));
    } on ApiException catch (e) {
      if (context.mounted) toast(context, e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final session = context.watch<Session>();
    final user = session.user;
    return ListView(children: [
      const SizedBox(height: 16),
      Center(
        child: CircleAvatar(
          radius: 40,
          child: Text(session.displayName.isEmpty ? '?' : session.displayName[0].toUpperCase(),
              style: const TextStyle(fontSize: 32)),
        ),
      ),
      const SizedBox(height: 8),
      Center(child: Text(session.displayName, style: Theme.of(context).textTheme.titleLarge)),
      if (user != null)
        Center(child: Text('${user['phone'] ?? ''}', textDirection: TextDirection.ltr)),
      const SizedBox(height: 16),
      ListTile(
        leading: const Icon(Icons.badge_outlined),
        title: Text(s.t('edit_name')),
        onTap: () => _editName(context),
      ),
      ListTile(
        leading: const Icon(Icons.location_on_outlined),
        title: Text(s.t('addresses')),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const AddressesScreen())),
      ),
      ListTile(
        leading: const Icon(Icons.language),
        title: Text(s.t('language')),
        trailing: SegmentedButton<String>(
          segments: const [
            ButtonSegment(value: 'fr', label: Text('FR')),
            ButtonSegment(value: 'ar', label: Text('عربي')),
          ],
          selected: {session.locale.languageCode},
          onSelectionChanged: (v) => session.setLanguage(v.first),
        ),
      ),
      ListTile(
        leading: const Icon(Icons.dns_outlined),
        title: Text(s.t('server')),
        subtitle: Text(AppConfig.baseUrl, textDirection: TextDirection.ltr),
        onTap: () => _editServer(context),
      ),
      const Divider(),
      ListTile(
        leading: const Icon(Icons.logout, color: Colors.red),
        title: Text(s.t('logout'), style: const TextStyle(color: Colors.red)),
        onTap: () async {
          if (await confirmDialog(context, '${s.t('logout')} ?')) await session.logout();
        },
      ),
    ]);
  }

  Future<void> _editServer(BuildContext context) async {
    final s = S.of(context);
    final ctrl = TextEditingController(text: AppConfig.baseUrl);
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(s.t('server')),
        content: TextField(
          controller: ctrl,
          keyboardType: TextInputType.url,
          textDirection: TextDirection.ltr,
          decoration: InputDecoration(hintText: s.t('server_hint')),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(s.t('cancel'))),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(s.t('save'))),
        ],
      ),
    );
    final url = ctrl.text;
    ctrl.dispose();
    if (ok == true) {
      await AppConfig.setBaseUrl(url);
      if (context.mounted) toast(context, s.t('saved'));
    }
  }
}

/// Carnet d'adresses (1 à 3 adresses conseillées).
class AddressesScreen extends StatefulWidget {
  const AddressesScreen({super.key});

  @override
  State<AddressesScreen> createState() => _AddressesScreenState();
}

class _AddressesScreenState extends State<AddressesScreen> {
  final _api = Api.instance;
  Key _key = UniqueKey();

  void _reload() => setState(() => _key = UniqueKey());

  Future<void> _add() async {
    final added = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => const _AddressForm()),
    );
    if (added == true) _reload();
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(s.t('addresses'))),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _add,
        icon: const Icon(Icons.add_location_alt),
        label: Text(s.t('add_address')),
      ),
      body: AsyncBody<List<Json>>(
        key: _key,
        load: () => _api.getAll('/addresses/'),
        builder: (context, items, reload) => items.isEmpty
            ? EmptyState(s.t('add_address'), icon: Icons.location_off_outlined)
            : ListView(children: [
                for (final a in items)
                  ListTile(
                    leading: Icon(a['is_default'] == true ? Icons.home : Icons.location_on_outlined),
                    title: Text((a['label'] ?? '').toString().isEmpty ? '${a['commune_name'] ?? ''}' : a['label']),
                    subtitle: Text([a['quartier'], a['street'], a['commune_name'], a['wilaya_name']]
                        .where((x) => x != null && x.toString().isNotEmpty)
                        .join(', ')),
                    trailing: IconButton(
                      icon: const Icon(Icons.delete_outline),
                      tooltip: s.t('delete'),
                      onPressed: () async {
                        if (!await confirmDialog(context, '${s.t('delete')} ?')) return;
                        try {
                          await _api.delete('/addresses/${a['id']}/');
                          _reload();
                        } on ApiException catch (e) {
                          if (context.mounted) toast(context, e.message);
                        }
                      },
                    ),
                  ),
              ]),
      ),
    );
  }
}

class _AddressForm extends StatefulWidget {
  const _AddressForm();

  @override
  State<_AddressForm> createState() => _AddressFormState();
}

class _AddressFormState extends State<_AddressForm> {
  final _label = TextEditingController();
  final _quartier = TextEditingController();
  final _street = TextEditingController();
  final _notes = TextEditingController();
  LocationValue _loc = const LocationValue();
  bool _default = true;
  bool _busy = false;

  @override
  void dispose() {
    for (final c in [_label, _quartier, _street, _notes]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    final s = S.of(context);
    if (!_loc.complete) {
      toast(context, s.t('pick_location'));
      return;
    }
    setState(() => _busy = true);
    try {
      await Api.instance.post('/addresses/', data: {
        'label': _label.text.trim(),
        'wilaya': _loc.wilayaId,
        'commune': _loc.communeId,
        'quartier': _quartier.text.trim(),
        'street': _street.text.trim(),
        'notes': _notes.text.trim(),
        'is_default': _default,
      });
      if (mounted) Navigator.of(context).pop(true);
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
      appBar: AppBar(title: Text(s.t('add_address'))),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        TextField(controller: _label, decoration: InputDecoration(labelText: s.t('label'))),
        const SizedBox(height: 12),
        LocationPicker(value: _loc, onChanged: (v) => setState(() => _loc = v)),
        const SizedBox(height: 12),
        TextField(controller: _quartier, decoration: InputDecoration(labelText: s.t('quartier'))),
        const SizedBox(height: 12),
        TextField(controller: _street, decoration: InputDecoration(labelText: s.t('street'))),
        const SizedBox(height: 12),
        TextField(controller: _notes, decoration: InputDecoration(labelText: s.t('notes'))),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          value: _default,
          onChanged: (v) => setState(() => _default = v),
          title: Text(s.t('default_address')),
        ),
        const SizedBox(height: 12),
        FilledButton(onPressed: _busy ? null : _save, child: Text(s.t('save'))),
      ]),
    );
  }
}
