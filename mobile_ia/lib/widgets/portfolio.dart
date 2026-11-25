import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../api/api_client.dart';
import '../l10n.dart';
import '../theme.dart';
import 'common.dart';

/// Nombre maximal de réalisations par artisan (même limite que le serveur).
const kMaxPortfolio = 12;

/// Grille des réalisations (fiche publique de l'artisan). Un appui ouvre la photo en grand.
class PortfolioGrid extends StatelessWidget {
  const PortfolioGrid({super.key, required this.photos});

  final List<Json> photos;

  @override
  Widget build(BuildContext context) {
    return GridView.count(
      crossAxisCount: 3,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 8,
      crossAxisSpacing: 8,
      children: [
        for (var i = 0; i < photos.length; i++)
          _Thumb(
            photo: photos[i],
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => PortfolioViewer(photos: photos, initialIndex: i)),
            ),
          ),
      ],
    );
  }
}

class _Thumb extends StatelessWidget {
  const _Thumb({required this.photo, required this.onTap});

  final Json photo;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.current;
    final caption = '${photo['caption'] ?? ''}'.trim();
    return Semantics(
      button: true,
      label: caption.isEmpty ? context.tr('portfolio_photo') : caption,
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(14),
          child: Stack(fit: StackFit.expand, children: [
            Image.network(
              '${photo['image']}',
              fit: BoxFit.cover,
              errorBuilder: (_, _, _) => Container(color: p.border, child: Icon(Icons.image_outlined, color: p.muted)),
            ),
            if (caption.isNotEmpty)
              Positioned(
                left: 6,
                bottom: 6,
                right: 6,
                child: Align(
                  alignment: AlignmentDirectional.bottomStart,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.9),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(caption,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: p.ink)),
                  ),
                ),
              ),
          ]),
        ),
      ),
    );
  }
}

/// Photo en plein écran : on glisse pour passer à la suivante, on pince pour zoomer.
class PortfolioViewer extends StatefulWidget {
  const PortfolioViewer({super.key, required this.photos, this.initialIndex = 0});

  final List<Json> photos;
  final int initialIndex;

  @override
  State<PortfolioViewer> createState() => _PortfolioViewerState();
}

class _PortfolioViewerState extends State<PortfolioViewer> {
  late final _controller = PageController(initialPage: widget.initialIndex);
  late int _index = widget.initialIndex;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final caption = '${widget.photos[_index]['caption'] ?? ''}'.trim();
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text('${_index + 1} / ${widget.photos.length}',
            style: const TextStyle(color: Colors.white, fontSize: 16)),
      ),
      body: Column(children: [
        Expanded(
          child: PageView.builder(
            controller: _controller,
            itemCount: widget.photos.length,
            onPageChanged: (i) => setState(() => _index = i),
            itemBuilder: (_, i) => InteractiveViewer(
              maxScale: 4,
              child: Center(
                child: Image.network(
                  '${widget.photos[i]['image']}',
                  fit: BoxFit.contain,
                  errorBuilder: (_, _, _) => const Icon(Icons.broken_image_outlined, color: Colors.white54, size: 48),
                ),
              ),
            ),
          ),
        ),
        if (caption.isNotEmpty)
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Text(caption, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white, fontSize: 15)),
            ),
          ),
      ]),
    );
  }
}

/// BRICOOL Pro : l'artisan gère ses réalisations (ajouter avec une légende, supprimer).
class MyPortfolioEditor extends StatefulWidget {
  const MyPortfolioEditor({super.key});

  @override
  State<MyPortfolioEditor> createState() => _MyPortfolioEditorState();
}

class _MyPortfolioEditorState extends State<MyPortfolioEditor> {
  List<Json>? _photos;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await context.api.get('/api/provider/portfolio/');
      if (!mounted) return;
      setState(() => _photos = (data as List).cast<Map>().map((e) => e.cast<String, dynamic>()).toList());
    } on ApiException catch (e) {
      if (mounted) {
        setState(() => _photos = const []);
        showError(context, e);
      }
    }
  }

  Future<void> _add() async {
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(
            leading: const Icon(Icons.photo_camera_outlined),
            title: Text(ctx.tr('photo_camera')),
            onTap: () => Navigator.pop(ctx, ImageSource.camera),
          ),
          ListTile(
            leading: const Icon(Icons.photo_library_outlined),
            title: Text(ctx.tr('photo_gallery')),
            onTap: () => Navigator.pop(ctx, ImageSource.gallery),
          ),
        ]),
      ),
    );
    if (source == null || !mounted) return;
    final picked = await ImagePicker().pickImage(source: source, maxWidth: 1600, imageQuality: 80);
    if (picked == null || !mounted) return;
    final caption = await _askCaption();
    if (caption == null || !mounted) return; // annulé
    setState(() => _busy = true);
    final ok = await runAction(context, () async {
      await context.api.upload(
        '/api/provider/portfolio/',
        fileField: 'image',
        file: File(picked.path),
        fields: {'caption': caption},
      );
    });
    if (!mounted) return;
    setState(() => _busy = false);
    if (ok) await _load();
  }

  /// Légende facultative (ex. « Salle de bain refaite »). Renvoie null si l'artisan annule.
  Future<String?> _askCaption() {
    final ctrl = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(ctx.tr('portfolio_caption_title')),
        content: TextField(
          controller: ctrl,
          autofocus: true,
          maxLength: 80,
          textCapitalization: TextCapitalization.sentences,
          decoration: InputDecoration(hintText: ctx.tr('portfolio_caption_hint')),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: Text(ctx.tr('cancel'))),
          FilledButton(onPressed: () => Navigator.pop(ctx, ctrl.text.trim()), child: Text(ctx.tr('portfolio_publish'))),
        ],
      ),
    );
  }

  Future<void> _delete(Json photo) async {
    if (!await confirmDialog(context, context.tr('portfolio_delete_confirm'))) return;
    if (!mounted) return;
    final ok = await runAction(context, () => context.api.delete('/api/provider/portfolio/${photo['id']}/'));
    if (ok && mounted) await _load();
  }

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.current;
    final photos = _photos;
    if (photos == null) {
      return const Padding(padding: EdgeInsets.all(16), child: Center(child: CircularProgressIndicator()));
    }
    final canAdd = photos.length < kMaxPortfolio && !_busy;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(context.tr('portfolio_hint'), style: TextStyle(fontSize: 12.5, color: p.muted)),
      const SizedBox(height: 10),
      GridView.count(
        crossAxisCount: 3,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: 8,
        crossAxisSpacing: 8,
        children: [
          if (photos.length < kMaxPortfolio)
            Material(
              color: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
                side: BorderSide(color: p.border, width: 1.5),
              ),
              child: InkWell(
                borderRadius: BorderRadius.circular(14),
                onTap: canAdd ? _add : null,
                child: Center(
                  child: _busy
                      ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2))
                      : Column(mainAxisSize: MainAxisSize.min, children: [
                          Icon(Icons.add_photo_alternate_outlined, color: p.primary, size: 28),
                          const SizedBox(height: 4),
                          Text(context.tr('portfolio_add'),
                              textAlign: TextAlign.center,
                              style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w600, color: p.primary)),
                        ]),
                ),
              ),
            ),
          for (var i = 0; i < photos.length; i++)
            Stack(fit: StackFit.expand, children: [
              _Thumb(
                photo: photos[i],
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => PortfolioViewer(photos: photos, initialIndex: i)),
                ),
              ),
              PositionedDirectional(
                top: 2,
                end: 2,
                child: IconButton.filled(
                  tooltip: context.tr('portfolio_delete'),
                  style: IconButton.styleFrom(
                    backgroundColor: Colors.black54,
                    foregroundColor: Colors.white,
                    minimumSize: const Size(32, 32),
                    fixedSize: const Size(32, 32),
                    padding: EdgeInsets.zero,
                  ),
                  iconSize: 18,
                  icon: const Icon(Icons.close),
                  onPressed: () => _delete(photos[i]),
                ),
              ),
            ]),
        ],
      ),
      const SizedBox(height: 6),
      Text(context.tr('portfolio_count', {'n': photos.length, 'max': kMaxPortfolio}),
          style: TextStyle(fontSize: 12, color: p.muted)),
    ]);
  }
}
