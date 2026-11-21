import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/config.dart';
import '../core/format.dart';
import '../core/i18n.dart';
import '../core/session.dart';
import '../screens/auth_screens.dart';

void toast(BuildContext context, String msg) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(msg)));
}

Future<bool> confirmDialog(BuildContext context, String message) async {
  final s = S.of(context);
  final ok = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      content: Text(message),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(s.t('cancel'))),
        FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(s.t('confirm'))),
      ],
    ),
  );
  return ok ?? false;
}

/// Ouvre l'écran de connexion si besoin. Renvoie true si l'utilisateur est connecté.
Future<bool> ensureLoggedIn(BuildContext context) async {
  final session = context.read<Session>();
  if (session.loggedIn) return true;
  await Navigator.of(context).push(MaterialPageRoute(builder: (_) => const PhoneScreen()));
  return session.loggedIn;
}

/// Charge des données asynchrones avec indicateur, erreur et bouton Réessayer.
class AsyncBody<T> extends StatefulWidget {
  const AsyncBody({super.key, required this.load, required this.builder});
  final Future<T> Function() load;
  final Widget Function(BuildContext context, T data, Future<void> Function() reload) builder;

  @override
  State<AsyncBody<T>> createState() => _AsyncBodyState<T>();
}

class _AsyncBodyState<T> extends State<AsyncBody<T>> {
  late Future<T> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.load();
  }

  Future<void> _reload() async {
    final f = widget.load();
    setState(() => _future = f);
    try {
      await f;
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<T>(
      future: _future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snap.hasError) {
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                const Icon(Icons.cloud_off, size: 48, color: Colors.grey),
                const SizedBox(height: 12),
                Text(snap.error.toString(), textAlign: TextAlign.center),
                const SizedBox(height: 12),
                OutlinedButton(onPressed: _reload, child: Text(S.of(context).t('retry'))),
              ]),
            ),
          );
        }
        return widget.builder(context, snap.data as T, _reload);
      },
    );
  }
}

class StatusChip extends StatelessWidget {
  const StatusChip(this.label, this.color, {super.key});
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(label, style: TextStyle(color: color, fontWeight: FontWeight.w600, fontSize: 12)),
    );
  }
}

class RequestStatusChip extends StatelessWidget {
  const RequestStatusChip(this.status, {super.key});
  final String status;

  @override
  Widget build(BuildContext context) =>
      StatusChip(S.of(context).t('s_$status'), statusColor(status));
}

class NetImage extends StatelessWidget {
  const NetImage(this.path, {super.key, this.size = 80});
  final String? path;
  final double size;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(8),
      child: Image.network(
        AppConfig.mediaUrl(path),
        width: size,
        height: size,
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) => Container(
          width: size,
          height: size,
          color: Colors.grey.shade200,
          child: const Icon(Icons.broken_image, color: Colors.grey),
        ),
      ),
    );
  }
}

class EmptyState extends StatelessWidget {
  const EmptyState(this.text, {super.key, this.icon = Icons.inbox_outlined});
  final String text;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, size: 56, color: Colors.grey),
          const SizedBox(height: 12),
          Text(text, textAlign: TextAlign.center, style: const TextStyle(color: Colors.grey)),
        ]),
      ),
    );
  }
}

class Stars extends StatelessWidget {
  const Stars(this.rating, {super.key, this.count});
  final double rating;
  final int? count;

  @override
  Widget build(BuildContext context) {
    return Row(mainAxisSize: MainAxisSize.min, children: [
      const Icon(Icons.star, color: Colors.amber, size: 18),
      const SizedBox(width: 2),
      Text(rating.toStringAsFixed(1), style: const TextStyle(fontWeight: FontWeight.w600)),
      if (count != null) Text(' ($count)', style: const TextStyle(color: Colors.grey)),
    ]);
  }
}

/// Réglage de l'adresse du serveur, avec test de connexion (`/api/health/`).
Future<void> editServerDialog(BuildContext context) async {
  final s = S.of(context);
  final ctrl = TextEditingController(text: AppConfig.baseUrl);
  String? result;
  var testing = false;
  final ok = await showDialog<bool>(
    context: context,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setLocal) => AlertDialog(
        title: Text(s.t('server')),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          TextField(
            controller: ctrl,
            keyboardType: TextInputType.url,
            textDirection: TextDirection.ltr,
            decoration: InputDecoration(hintText: s.t('server_hint')),
          ),
          const SizedBox(height: 8),
          Text(s.t('server_help'), style: const TextStyle(fontSize: 12, color: Colors.grey)),
          if (result != null) ...[
            const SizedBox(height: 8),
            Text(result!, style: TextStyle(color: result == s.t('server_ok') ? Colors.green : Colors.red)),
          ],
        ]),
        actions: [
          TextButton(
            onPressed: testing
                ? null
                : () async {
                    setLocal(() {
                      testing = true;
                      result = null;
                    });
                    var url = ctrl.text.trim();
                    while (url.endsWith('/')) {
                      url = url.substring(0, url.length - 1);
                    }
                    try {
                      await Dio(BaseOptions(connectTimeout: const Duration(seconds: 6)))
                          .get('$url/api/health/');
                      result = s.t('server_ok');
                    } on DioException catch (e) {
                      result = e.response != null
                          ? '${s.t('server_ko')} (HTTP ${e.response!.statusCode})'
                          : s.t('server_ko');
                    } catch (_) {
                      result = s.t('server_ko');
                    }
                    setLocal(() => testing = false);
                  },
            child: Text(testing ? '…' : s.t('server_test')),
          ),
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(s.t('cancel'))),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(s.t('save'))),
        ],
      ),
    ),
  );
  final url = ctrl.text;
  ctrl.dispose();
  if (ok == true) {
    await AppConfig.setBaseUrl(url);
    if (context.mounted) toast(context, s.t('saved'));
  }
}
