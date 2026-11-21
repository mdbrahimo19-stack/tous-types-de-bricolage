import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../l10n.dart';
import '../state/session.dart';
import '../widgets/common.dart';

/// Étape 1 : numéro de téléphone. Connexion si le compte existe, sinon inscription.
class PhoneScreen extends StatefulWidget {
  const PhoneScreen({super.key});

  @override
  State<PhoneScreen> createState() => _PhoneScreenState();
}

class _PhoneScreenState extends State<PhoneScreen> {
  final _phone = TextEditingController();
  bool _busy = false;

  Future<void> _continue() async {
    final phone = _phone.text.replaceAll(' ', '').trim();
    if (phone.length < 9) return;
    final session = context.read<Session>();
    setState(() => _busy = true);
    try {
      String purpose = 'login';
      String? debugCode;
      try {
        debugCode = await session.requestOtp(phone, 'login');
      } on ApiException catch (e) {
        if (!e.isNotFound) rethrow;
        purpose = 'registration'; // aucun compte : on inscrit
        debugCode = await session.requestOtp(phone, 'registration');
      }
      if (!mounted) return;
      Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => OtpScreen(phone: phone, purpose: purpose, debugCode: debugCode)),
      );
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(actions: [
        IconButton(
          tooltip: context.tr('server'),
          icon: const Icon(Icons.dns_outlined),
          onPressed: () => showServerDialog(context),
        ),
        TextButton(
          onPressed: () => session.setLocale(session.locale == 'ar' ? 'fr' : 'ar'),
          child: Text(session.locale == 'ar' ? 'Français' : 'العربية'),
        ),
      ]),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Icon(Icons.handyman, size: 72, color: theme.colorScheme.primary),
            const SizedBox(height: 16),
            Text(context.tr('app_name'),
                textAlign: TextAlign.center,
                style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            Text(context.tr('welcome_title'), textAlign: TextAlign.center, style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(context.tr('welcome_sub'), textAlign: TextAlign.center, style: theme.textTheme.bodyMedium),
            const SizedBox(height: 40),
            TextField(
              controller: _phone,
              keyboardType: TextInputType.phone,
              textDirection: TextDirection.ltr,
              decoration: InputDecoration(
                labelText: context.tr('phone_label'),
                hintText: context.tr('phone_hint'),
                prefixIcon: const Icon(Icons.phone),
              ),
              onSubmitted: (_) => _continue(),
            ),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: _busy ? null : _continue,
              child: _busy
                  ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2))
                  : Text(context.tr('continue')),
            ),
          ],
        ),
      ),
    );
  }
}

/// Étape 2 : code OTP (+ nom et rôle pour une inscription).
class OtpScreen extends StatefulWidget {
  const OtpScreen({super.key, required this.phone, required this.purpose, this.debugCode});

  final String phone;
  final String purpose;
  final String? debugCode;

  @override
  State<OtpScreen> createState() => _OtpScreenState();
}

class _OtpScreenState extends State<OtpScreen> {
  final _form = GlobalKey<FormState>();
  late final _code = TextEditingController(text: widget.debugCode ?? '');
  final _name = TextEditingController();
  bool _asProvider = false;
  bool _busy = false;

  bool get _isRegistration => widget.purpose == 'registration';

  Future<void> _verify() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    final ok = await runAction(context, () async {
      await context.read<Session>().verifyOtp(
            phone: widget.phone,
            code: _code.text.trim(),
            purpose: widget.purpose,
            fullName: _name.text.trim(),
            asProvider: _asProvider,
          );
    });
    if (!mounted) return;
    setState(() => _busy = false);
    if (ok) Navigator.of(context).popUntil((r) => r.isFirst);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_isRegistration ? context.tr('new_account') : context.tr('otp_title'))),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text(context.tr('otp_sent_to', {'phone': widget.phone})),
            if (widget.debugCode != null) ...[
              const SizedBox(height: 8),
              Text(context.tr('dev_code', {'code': widget.debugCode}),
                  style: const TextStyle(color: Colors.deepOrange)),
            ],
            const SizedBox(height: 20),
            TextFormField(
              controller: _code,
              keyboardType: TextInputType.number,
              textDirection: TextDirection.ltr,
              maxLength: 6,
              decoration: InputDecoration(labelText: context.tr('otp_code'), prefixIcon: const Icon(Icons.sms)),
              validator: (v) => (v ?? '').trim().length < 4 ? context.tr('required') : null,
            ),
            if (_isRegistration) ...[
              TextFormField(
                controller: _name,
                textCapitalization: TextCapitalization.words,
                decoration: InputDecoration(labelText: context.tr('full_name'), prefixIcon: const Icon(Icons.person)),
                validator: (v) => (v ?? '').trim().isEmpty ? context.tr('required') : null,
              ),
              const SizedBox(height: 8),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                value: _asProvider,
                onChanged: (v) => setState(() => _asProvider = v),
                title: Text(context.tr('i_am_provider')),
                secondary: const Icon(Icons.handyman),
              ),
            ],
            const SizedBox(height: 20),
            FilledButton(
              onPressed: _busy ? null : _verify,
              child: _busy
                  ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2))
                  : Text(context.tr('verify')),
            ),
          ],
        ),
      ),
    );
  }
}
