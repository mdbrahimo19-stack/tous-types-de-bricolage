import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api.dart';
import '../core/i18n.dart';
import '../core/session.dart';
import '../widgets/common.dart';

/// Saisie du numéro de téléphone.
class PhoneScreen extends StatefulWidget {
  const PhoneScreen({super.key});

  @override
  State<PhoneScreen> createState() => _PhoneScreenState();
}

class _PhoneScreenState extends State<PhoneScreen> {
  final _phone = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _phone.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final phone = _phone.text.replaceAll(' ', '').trim();
    if (phone.length < 9) {
      toast(context, S.of(context).t('required'));
      return;
    }
    setState(() => _busy = true);
    try {
      final debugCode = await context.read<Session>().requestOtp(phone);
      if (!mounted) return;
      await Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => OtpScreen(phone: phone, debugCode: debugCode),
      ));
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
      appBar: AppBar(
        title: Text(s.t('login')),
        actions: [
          IconButton(
            tooltip: s.t('server'),
            icon: const Icon(Icons.settings_ethernet),
            onPressed: () => editServerDialog(context),
          ),
        ],
      ),
      body: ListView(padding: const EdgeInsets.all(24), children: [
        const Icon(Icons.phone_android, size: 72),
        const SizedBox(height: 24),
        TextField(
          controller: _phone,
          keyboardType: TextInputType.phone,
          textDirection: TextDirection.ltr,
          decoration: InputDecoration(
            labelText: s.t('phone'),
            hintText: s.t('phone_hint'),
            prefixIcon: const Icon(Icons.phone),
          ),
          onSubmitted: (_) => _send(),
        ),
        const SizedBox(height: 24),
        FilledButton(
          onPressed: _busy ? null : _send,
          child: _busy
              ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
              : Text(s.t('send_code')),
        ),
      ]),
    );
  }
}

/// Saisie du code OTP (+ nom et rôle pour un nouveau compte).
class OtpScreen extends StatefulWidget {
  const OtpScreen({super.key, required this.phone, this.debugCode});
  final String phone;
  final String? debugCode;

  @override
  State<OtpScreen> createState() => _OtpScreenState();
}

class _OtpScreenState extends State<OtpScreen> {
  late final TextEditingController _code = TextEditingController(text: widget.debugCode ?? '');
  final _name = TextEditingController();
  bool _provider = false;
  bool _busy = false;

  @override
  void dispose() {
    _code.dispose();
    _name.dispose();
    super.dispose();
  }

  Future<void> _verify() async {
    if (_code.text.trim().length < 4) {
      toast(context, S.of(context).t('required'));
      return;
    }
    setState(() => _busy = true);
    try {
      await context.read<Session>().verifyOtp(
            phone: widget.phone,
            code: _code.text.trim(),
            fullName: _name.text.trim(),
            asProvider: _provider,
          );
      if (!mounted) return;
      Navigator.of(context).popUntil((r) => r.isFirst);
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
      appBar: AppBar(title: Text(widget.phone)),
      body: ListView(padding: const EdgeInsets.all(24), children: [
        Text(s.t('code_sent')),
        if (widget.debugCode != null) ...[
          const SizedBox(height: 8),
          Text('${s.t('dev_code')} ${widget.debugCode}', style: const TextStyle(color: Colors.orange)),
        ],
        const SizedBox(height: 16),
        TextField(
          controller: _code,
          keyboardType: TextInputType.number,
          textDirection: TextDirection.ltr,
          maxLength: 8,
          style: const TextStyle(fontSize: 24, letterSpacing: 6),
          decoration: InputDecoration(labelText: s.t('code')),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: _name,
          textCapitalization: TextCapitalization.words,
          decoration: InputDecoration(labelText: s.t('your_name'), prefixIcon: const Icon(Icons.person)),
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          value: _provider,
          onChanged: (v) => setState(() => _provider = v),
          title: Text(s.t('also_provider')),
        ),
        const SizedBox(height: 16),
        FilledButton(
          onPressed: _busy ? null : _verify,
          child: _busy
              ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
              : Text(s.t('verify')),
        ),
      ]),
    );
  }
}
