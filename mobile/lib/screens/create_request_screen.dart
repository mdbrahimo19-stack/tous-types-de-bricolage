import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../core/api.dart';
import '../core/format.dart';
import '../core/i18n.dart';
import '../widgets/common.dart';
import '../widgets/location_picker.dart';

/// Assistant de création de demande :
/// catégorie → détails + photos → adresse → urgence + budget → récapitulatif.
class CreateRequestScreen extends StatefulWidget {
  const CreateRequestScreen({super.key, this.initialCategory});
  final Json? initialCategory;

  @override
  State<CreateRequestScreen> createState() => _CreateRequestScreenState();
}

class _CreateRequestScreenState extends State<CreateRequestScreen> {
  final _api = Api.instance;
  int _step = 0;
  bool _busy = false;

  List<Json> _categories = [];
  List<Json> _addresses = [];
  bool _loading = true;
  String? _loadError;

  Json? _category; // famille racine
  Json? _service; // prestation (enfant), facultative
  final _title = TextEditingController();
  final _desc = TextEditingController();
  final List<XFile> _photos = [];

  int? _addressId; // adresse du carnet
  LocationValue _location = const LocationValue();

  String _urgency = 'flexible';
  final _bmin = TextEditingController();
  final _bmax = TextEditingController();

  @override
  void initState() {
    super.initState();
    _category = widget.initialCategory;
    _load();
  }

  @override
  void dispose() {
    _title.dispose();
    _desc.dispose();
    _bmin.dispose();
    _bmax.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _loadError = null;
    });
    try {
      final cats = await _api.getAll('/categories/', auth: false);
      final addrs = await _api.getAll('/addresses/');
      setState(() {
        _categories = cats;
        _addresses = addrs;
        if (_category != null) {
          _category = cats.firstWhere((c) => c['id'] == _category!['id'], orElse: () => _category!);
        }
        if (addrs.isNotEmpty) {
          final def = addrs.firstWhere((a) => a['is_default'] == true, orElse: () => addrs.first);
          _addressId = def['id'] as int;
        }
        if (_category != null) _step = 1;
      });
    } on ApiException catch (e) {
      setState(() => _loadError = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String? _validateStep() {
    final s = S.of(context);
    switch (_step) {
      case 0:
        return _category == null ? s.t('pick_category_first') : null;
      case 1:
        if (_title.text.trim().isEmpty) return '${s.t('title')} : ${s.t('required')}';
        if (_desc.text.trim().isEmpty && _photos.isEmpty) return s.t('need_desc_or_photo');
        return null;
      case 2:
        if (_addressId == null && !_location.complete) return s.t('pick_location');
        return null;
    }
    return null;
  }

  void _next() {
    final err = _validateStep();
    if (err != null) {
      toast(context, err);
      return;
    }
    setState(() => _step++);
  }

  Future<void> _pickPhoto(ImageSource source) async {
    if (_photos.length >= 4) {
      toast(context, S.of(context).t('max_photos'));
      return;
    }
    final file = await ImagePicker().pickImage(source: source, maxWidth: 1600, imageQuality: 80);
    if (file != null) setState(() => _photos.add(file));
  }

  Future<void> _submit() async {
    final s = S.of(context);
    setState(() => _busy = true);
    try {
      final body = <String, dynamic>{
        'category': (_service ?? _category)!['id'],
        'title': _title.text.trim(),
        'description': _desc.text.trim(),
        'urgency': _urgency,
        if (_bmin.text.trim().isNotEmpty) 'budget_min': _bmin.text.trim(),
        if (_bmax.text.trim().isNotEmpty) 'budget_max': _bmax.text.trim(),
        if (_addressId != null) 'address': _addressId,
        if (_addressId == null) 'wilaya': _location.wilayaId,
        if (_addressId == null) 'commune': _location.communeId,
      };
      final created = Json.from(await _api.post('/requests/', data: body));
      final id = created['id'];
      for (final p in _photos) {
        await _api.upload('/requests/$id/photos/', 'image', p.path);
      }
      await _api.post('/requests/$id/publish/');
      if (!mounted) return;
      toast(context, s.t('published_ok'));
      Navigator.of(context).pop(true);
    } on ApiException catch (e) {
      if (mounted) toast(context, e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final steps = [s.t('step_category'), s.t('step_details'), s.t('step_address'), s.t('step_urgency'), s.t('step_recap')];

    Widget body;
    if (_loading) {
      body = const Center(child: CircularProgressIndicator());
    } else if (_loadError != null) {
      body = Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Text(_loadError!, textAlign: TextAlign.center),
          const SizedBox(height: 12),
          OutlinedButton(onPressed: _load, child: Text(s.t('retry'))),
        ]),
      );
    } else {
      body = switch (_step) {
        0 => _categoryStep(s),
        1 => _detailsStep(s),
        2 => _addressStep(s),
        3 => _urgencyStep(s),
        _ => _recapStep(s),
      };
    }

    return PopScope(
      canPop: _step == 0 || _busy,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) setState(() => _step--);
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text('${s.t('publish_request')} · ${_step + 1}/${steps.length}'),
          bottom: PreferredSize(
            preferredSize: const Size.fromHeight(4),
            child: LinearProgressIndicator(value: (_step + 1) / steps.length),
          ),
        ),
        body: body,
        bottomNavigationBar: (_loading || _loadError != null)
            ? null
            : SafeArea(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(children: [
                    if (_step > 0)
                      Expanded(
                        child: OutlinedButton(
                          onPressed: _busy ? null : () => setState(() => _step--),
                          child: Text(s.t('back')),
                        ),
                      ),
                    if (_step > 0) const SizedBox(width: 12),
                    Expanded(
                      child: FilledButton(
                        onPressed: _busy ? null : (_step == steps.length - 1 ? _submit : _next),
                        child: _busy
                            ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                            : Text(_step == steps.length - 1 ? s.t('publish') : s.t('next')),
                      ),
                    ),
                  ]),
                ),
              ),
      ),
    );
  }

  Widget _categoryStep(S s) {
    final children = ((_category?['children'] as List?) ?? []).cast<Json>();
    return ListView(padding: const EdgeInsets.all(16), children: [
      Text(s.t('choose_category'), style: Theme.of(context).textTheme.titleMedium),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final c in _categories)
          ChoiceChip(
            avatar: Icon(categoryIcon(c['icon']), size: 18),
            label: Text(s.name(c)),
            selected: _category?['id'] == c['id'],
            onSelected: (_) => setState(() {
              _category = c;
              _service = null;
            }),
          ),
      ]),
      if (children.isNotEmpty) ...[
        const SizedBox(height: 24),
        Text(s.t('service_optional'), style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final c in children)
            ChoiceChip(
              label: Text(s.name(c)),
              selected: _service?['id'] == c['id'],
              onSelected: (sel) => setState(() => _service = sel ? c : null),
            ),
        ]),
      ],
      if (_category != null && (_category!['price_min'] != null)) ...[
        const SizedBox(height: 16),
        Text('${money(_category!['price_min'])} – ${money(_category!['price_max'])}',
            style: const TextStyle(color: Colors.grey)),
      ],
    ]);
  }

  Widget _detailsStep(S s) {
    return ListView(padding: const EdgeInsets.all(16), children: [
      TextField(
        controller: _title,
        maxLength: 120,
        decoration: InputDecoration(labelText: s.t('title'), hintText: s.t('title_hint')),
      ),
      const SizedBox(height: 8),
      TextField(
        controller: _desc,
        minLines: 4,
        maxLines: 8,
        decoration: InputDecoration(labelText: s.t('description'), hintText: s.t('description_hint')),
      ),
      const SizedBox(height: 16),
      Text('${s.t('photos')} (${_photos.length}/4)', style: Theme.of(context).textTheme.titleSmall),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (var i = 0; i < _photos.length; i++)
          Stack(children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.file(File(_photos[i].path), width: 90, height: 90, fit: BoxFit.cover),
            ),
            PositionedDirectional(
              top: 0,
              end: 0,
              child: IconButton.filledTonal(
                visualDensity: VisualDensity.compact,
                icon: const Icon(Icons.close, size: 16),
                onPressed: () => setState(() => _photos.removeAt(i)),
              ),
            ),
          ]),
        if (_photos.length < 4) ...[
          _PhotoButton(icon: Icons.photo_camera, label: s.t('camera'), onTap: () => _pickPhoto(ImageSource.camera)),
          _PhotoButton(icon: Icons.photo_library, label: s.t('gallery'), onTap: () => _pickPhoto(ImageSource.gallery)),
        ],
      ]),
    ]);
  }

  Widget _addressStep(S s) {
    return ListView(padding: const EdgeInsets.all(16), children: [
      if (_addresses.isNotEmpty) ...[
        Text(s.t('saved_address'), style: Theme.of(context).textTheme.titleSmall),
        RadioGroup<int?>(
          groupValue: _addressId,
          onChanged: (v) => setState(() => _addressId = v),
          child: Column(children: [
            for (final a in _addresses)
              RadioListTile<int?>(
                value: a['id'] as int,
                title: Text((a['label'] ?? '').toString().isEmpty ? (a['commune_name'] ?? '') : a['label']),
                subtitle: Text('${a['commune_name'] ?? ''}, ${a['wilaya_name'] ?? ''}'),
              ),
            RadioListTile<int?>(value: null, title: Text(s.t('other_address'))),
          ]),
        ),
      ],
      if (_addressId == null) ...[
        const SizedBox(height: 8),
        LocationPicker(value: _location, onChanged: (v) => setState(() => _location = v)),
      ],
    ]);
  }

  Widget _urgencyStep(S s) {
    return ListView(padding: const EdgeInsets.all(16), children: [
      Text(s.t('urgency'), style: Theme.of(context).textTheme.titleSmall),
      RadioGroup<String>(
        groupValue: _urgency,
        onChanged: (v) => setState(() => _urgency = v ?? _urgency),
        child: Column(children: [
          for (final u in urgencies) RadioListTile<String>(value: u, title: Text(s.t('u_$u'))),
        ]),
      ),
      const SizedBox(height: 16),
      Text(s.t('budget'), style: Theme.of(context).textTheme.titleSmall),
      const SizedBox(height: 8),
      Row(children: [
        Expanded(
          child: TextField(
            controller: _bmin,
            keyboardType: TextInputType.number,
            decoration: InputDecoration(labelText: s.t('budget_min')),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: TextField(
            controller: _bmax,
            keyboardType: TextInputType.number,
            decoration: InputDecoration(labelText: s.t('budget_max')),
          ),
        ),
      ]),
    ]);
  }

  Widget _recapStep(S s) {
    String place;
    if (_addressId != null) {
      final a = _addresses.firstWhere((a) => a['id'] == _addressId, orElse: () => {});
      place = '${a['commune_name'] ?? ''}, ${a['wilaya_name'] ?? ''}';
    } else {
      place = '${_location.communeName}, ${_location.wilayaName}';
    }
    final budget = (_bmin.text.isEmpty && _bmax.text.isEmpty)
        ? '—'
        : '${_bmin.text.isEmpty ? '…' : money(_bmin.text)} – ${_bmax.text.isEmpty ? '…' : money(_bmax.text)}';
    Widget row(String k, String v) => Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SizedBox(width: 110, child: Text(k, style: const TextStyle(color: Colors.grey))),
            Expanded(child: Text(v)),
          ]),
        );
    return ListView(padding: const EdgeInsets.all(16), children: [
      row(s.t('step_category'), [s.name(_category), if (_service != null) s.name(_service)].join(' › ')),
      row(s.t('title'), _title.text),
      row(s.t('description'), _desc.text.isEmpty ? '—' : _desc.text),
      row(s.t('photos'), '${_photos.length}'),
      row(s.t('step_address'), place),
      row(s.t('urgency'), s.t('u_$_urgency')),
      row(s.t('budget'), budget),
    ]);
  }
}

class _PhotoButton extends StatelessWidget {
  const _PhotoButton({required this.icon, required this.label, required this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        width: 90,
        height: 90,
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey.shade400),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(icon),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(fontSize: 11), textAlign: TextAlign.center),
        ]),
      ),
    );
  }
}
