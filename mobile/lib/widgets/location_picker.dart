import 'package:flutter/material.dart';

import '../core/api.dart';
import '../core/i18n.dart';

class LocationValue {
  const LocationValue({this.wilayaId, this.wilayaName = '', this.communeId, this.communeName = ''});
  final int? wilayaId;
  final String wilayaName;
  final int? communeId;
  final String communeName;
  bool get complete => wilayaId != null && communeId != null;
}

/// Sélecteur Wilaya → Commune (données de l'API).
class LocationPicker extends StatefulWidget {
  const LocationPicker({super.key, required this.value, required this.onChanged});
  final LocationValue value;
  final ValueChanged<LocationValue> onChanged;

  @override
  State<LocationPicker> createState() => _LocationPickerState();
}

class _LocationPickerState extends State<LocationPicker> {
  final _api = Api.instance;
  List<Json> _wilayas = [];
  List<Json> _communes = [];
  bool _loadingCommunes = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadWilayas();
  }

  Future<void> _loadWilayas() async {
    try {
      final w = await _api.getAll('/wilayas/', query: {'is_active': 'true'}, auth: false);
      if (!mounted) return;
      setState(() => _wilayas = w);
      if (widget.value.wilayaId != null) _loadCommunes(widget.value.wilayaId!);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    }
  }

  Future<void> _loadCommunes(int wilayaId) async {
    setState(() {
      _loadingCommunes = true;
      _communes = [];
    });
    try {
      final c = await _api.getAll('/communes/', query: {'wilaya': wilayaId}, auth: false, maxPages: 10);
      c.sort((a, b) => (a['name_fr'] ?? '').toString().compareTo((b['name_fr'] ?? '').toString()));
      if (mounted) setState(() => _communes = c);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loadingCommunes = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    if (_error != null) return Text(_error!, style: const TextStyle(color: Colors.red));
    final v = widget.value;
    final wilayaIds = _wilayas.map((w) => w['id']).toSet();
    final communeIds = _communes.map((c) => c['id']).toSet();
    return Column(children: [
      DropdownButtonFormField<int>(
        isExpanded: true,
        initialValue: wilayaIds.contains(v.wilayaId) ? v.wilayaId : null,
        decoration: InputDecoration(labelText: s.t('wilaya')),
        items: [
          for (final w in _wilayas)
            DropdownMenuItem(value: w['id'] as int, child: Text('${w['code'] ?? ''} - ${s.name(w)}')),
        ],
        onChanged: (id) {
          if (id == null) return;
          final w = _wilayas.firstWhere((w) => w['id'] == id);
          widget.onChanged(LocationValue(wilayaId: id, wilayaName: s.name(w)));
          _loadCommunes(id);
        },
      ),
      const SizedBox(height: 12),
      DropdownButtonFormField<int>(
        key: ValueKey('communes-${v.wilayaId}-${_communes.length}'),
        isExpanded: true,
        initialValue: communeIds.contains(v.communeId) ? v.communeId : null,
        decoration: InputDecoration(
          labelText: s.t('commune'),
          suffixIcon: _loadingCommunes
              ? const Padding(padding: EdgeInsets.all(12), child: CircularProgressIndicator(strokeWidth: 2))
              : null,
        ),
        items: [
          for (final c in _communes) DropdownMenuItem(value: c['id'] as int, child: Text(s.name(c))),
        ],
        onChanged: (id) {
          if (id == null) return;
          final c = _communes.firstWhere((c) => c['id'] == id);
          widget.onChanged(LocationValue(
            wilayaId: v.wilayaId,
            wilayaName: v.wilayaName,
            communeId: id,
            communeName: s.name(c),
          ));
        },
      ),
    ]);
  }
}
