import 'package:flutter/material.dart';

import '../theme.dart';

/// Photo ronde d'une personne (artisan), avec ses initiales si pas de photo,
/// et la petite pastille verte ✓ quand le compte est vérifié par BRICOOL.
class PersonAvatar extends StatelessWidget {
  const PersonAvatar({super.key, required this.name, this.photoUrl, this.size = 56, this.verified = false});

  final String name;
  final String? photoUrl;
  final double size;
  final bool verified;

  static const _tints = [Color(0xFF8A5A3C), Color(0xFF3C5A8A), Color(0xFF5A3C8A), Color(0xFF3C7A5A), Color(0xFF8A3C4E)];

  String get _initials {
    final parts = name.trim().split(RegExp(r'\s+')).where((s) => s.isNotEmpty).toList();
    if (parts.isEmpty) return '?';
    final first = parts.first.characters.first;
    final second = parts.length > 1 ? parts[1].characters.first : '';
    return (first + second).toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    final tint = _tints[name.hashCode.abs() % _tints.length];
    final initials = Container(
      color: tint,
      alignment: Alignment.center,
      child: Text(_initials,
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: size * 0.34)),
    );
    final url = photoUrl;
    final badge = size * 0.38;
    return SizedBox(
      width: size,
      height: size,
      child: Stack(clipBehavior: Clip.none, children: [
        ClipOval(
          child: SizedBox(
            width: size,
            height: size,
            child: url == null || url.isEmpty
                ? initials
                : Image.network(url, fit: BoxFit.cover, errorBuilder: (_, _, _) => initials),
          ),
        ),
        if (verified)
          Positioned(
            right: -2,
            bottom: -2,
            child: Container(
              width: badge,
              height: badge,
              decoration: BoxDecoration(
                color: AppPalette.success,
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white, width: 2),
              ),
              child: Icon(Icons.check, color: Colors.white, size: badge * 0.62),
            ),
          ),
      ]),
    );
  }
}

/// Étiquette verte « Vérifié ».
class VerifiedTag extends StatelessWidget {
  const VerifiedTag(this.label, {super.key});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
      decoration: BoxDecoration(color: AppPalette.successSoft, borderRadius: BorderRadius.circular(6)),
      child: Text(label, style: const TextStyle(color: AppPalette.success, fontSize: 11, fontWeight: FontWeight.w700)),
    );
  }
}
