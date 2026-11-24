import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../flavor.dart';
import '../l10n.dart';
import '../state/session.dart';
import '../widgets/common.dart';
import '../widgets/floating_services.dart';

/// Étape 1 : numéro de téléphone. Connexion si le compte existe, sinon inscription.
class PhoneScreen extends StatefulWidget {
  const PhoneScreen({super.key});

  @override
  State<PhoneScreen> createState() => _PhoneScreenState();
}

class _PhoneScreenState extends State<PhoneScreen> {
  final _phone = TextEditingController();
  bool _busy = false;

  /// Clé stable de la carte de connexion : quand le clavier s'ouvre, l'écran passe en
  /// mode compact (autre parent). Sans cette clé, la carte serait recréée, le champ
  /// perdrait le focus, le clavier se refermerait… et on ne pourrait jamais écrire.
  final _cardKey = GlobalKey();

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
        MaterialPageRoute(
          builder: (_) =>
              OtpScreen(phone: phone, purpose: purpose, debugCode: debugCode),
        ),
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
    final scheme = theme.colorScheme;
    final media = MediaQuery.of(context);
    final keyboardOpen = media.viewInsets.bottom > 0;
    // hauteur réellement disponible (sans barre d'état ni clavier)
    final availH =
        media.size.height - media.padding.top - media.viewInsets.bottom;
    // peu de place (clavier ouvert, petit écran) : titre + carte seulement, défilable
    final compact = keyboardOpen || availH < 520;
    final showMarquee = !compact && availH > 640;
    const onHero = Colors.white;

    return Scaffold(
      body: DecoratedBox(
        // dégradé : orange « chantier » (BRICOOL) ou bleu nuit (BRICOOL Pro)
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: AppFlavor.heroGradient,
          ),
        ),
        child: SafeArea(
          bottom: false,
          // Structure FIXE (même colonne, même ordre) quel que soit le mode : si la carte
          // changeait de parent ou de place, le champ serait recréé et perdrait le focus.
          child: Column(
            children: [
              // --- barre du haut : serveur + langue
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                child: Row(
                  children: [
                    IconButton(
                      tooltip: context.tr('server'),
                      color: onHero,
                      icon: const Icon(Icons.dns_outlined),
                      onPressed: () => showServerDialog(context),
                    ),
                    const Spacer(),
                    TextButton.icon(
                      style: TextButton.styleFrom(
                        foregroundColor: onHero,
                        backgroundColor: Colors.white.withValues(alpha: 0.16),
                        shape: const StadiumBorder(),
                      ),
                      icon: const Icon(Icons.translate, size: 18),
                      onPressed: () => session.setLocale(
                        session.locale == 'ar' ? 'fr' : 'ar',
                      ),
                      label: Text(
                        session.locale == 'ar' ? 'Français' : 'العربية',
                      ),
                    ),
                  ],
                ),
              ),

              // --- zone héros : services qui flottent autour du titre
              // (mode compact : seulement le nom de l'app, réduit si besoin)
              Expanded(
                child: compact
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 24),
                          child: FittedBox(
                            fit: BoxFit.scaleDown,
                            child: Text(
                              AppFlavor.name,
                              textAlign: TextAlign.center,
                              style: theme.textTheme.titleLarge?.copyWith(
                                color: onHero,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                        ),
                      )
                    // titre en haut (toujours lisible), bulles dans l'espace en dessous
                    : Column(
                        children: [
                          Padding(
                            padding: const EdgeInsets.fromLTRB(24, 4, 24, 0),
                            child: Column(
                              children: [
                                Text(
                                  AppFlavor.name,
                                  textAlign: TextAlign.center,
                                  style: theme.textTheme.headlineMedium
                                      ?.copyWith(
                                        color: onHero,
                                        fontWeight: FontWeight.w800,
                                        height: 1.1,
                                        shadows: const [
                                          Shadow(
                                            color: Colors.black26,
                                            blurRadius: 12,
                                            offset: Offset(0, 3),
                                          ),
                                        ],
                                      ),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  context.tr('welcome_title'),
                                  textAlign: TextAlign.center,
                                  style: theme.textTheme.titleMedium?.copyWith(
                                    color: onHero.withValues(alpha: 0.95),
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const Expanded(
                            child: Padding(
                              padding: EdgeInsets.fromLTRB(16, 12, 16, 8),
                              child: FloatingServices(),
                            ),
                          ),
                        ],
                      ),
              ),

              // --- tous les services, en deux bandeaux qui défilent en sens inverse
              if (showMarquee) ...[
                const ServicesMarquee(),
                const SizedBox(height: 8),
                ServicesMarquee(
                  reverse: true,
                  offset: kServices.length ~/ 2,
                  speed: 22,
                ),
                const SizedBox(height: 18),
              ],

              // --- carte de connexion
              Container(
                key: _cardKey,
                width: double.infinity,
                decoration: BoxDecoration(
                  color: scheme.surface,
                  borderRadius: const BorderRadius.vertical(
                    top: Radius.circular(28),
                  ),
                  boxShadow: const [
                    BoxShadow(
                      color: Colors.black26,
                      blurRadius: 24,
                      offset: Offset(0, -4),
                    ),
                  ],
                ),
                padding: EdgeInsets.fromLTRB(
                  24,
                  24,
                  24,
                  16 + MediaQuery.paddingOf(context).bottom,
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (!compact) ...[
                      Text(
                        context.tr('welcome_sub'),
                        textAlign: TextAlign.center,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: scheme.onSurfaceVariant,
                        ),
                      ),
                      const SizedBox(height: 18),
                    ],
                    // clé fixe : le champ reste le même widget même si le texte
                    // au-dessus disparaît (mode compact) -> il garde le focus
                    TextField(
                      key: const ValueKey('phone-field'),
                      controller: _phone,
                      keyboardType: TextInputType.phone,
                      textDirection: TextDirection.ltr,
                      decoration: InputDecoration(
                        labelText: context.tr('phone_label'),
                        hintText: context.tr('phone_hint'),
                        prefixIcon: const Icon(Icons.phone_iphone),
                        filled: true,
                        fillColor: scheme.surfaceContainerHighest.withValues(
                          alpha: 0.5,
                        ),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                      onSubmitted: (_) => _continue(),
                    ),
                    const SizedBox(height: 14),
                    FilledButton(
                      key: const ValueKey('continue-button'),
                      style: FilledButton.styleFrom(
                        minimumSize: const Size.fromHeight(54),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                        textStyle: const TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      onPressed: _busy ? null : _continue,
                      child: _busy
                          ? const SizedBox(
                              width: 22,
                              height: 22,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : Text(context.tr('continue')),
                    ),
                    if (!compact) ...[
                      const SizedBox(height: 16),
                      Wrap(
                        alignment: WrapAlignment.spaceEvenly,
                        spacing: 12,
                        runSpacing: 6,
                        children: [
                          _Trust(
                            Icons.verified_user,
                            context.tr('trust_verified'),
                          ),
                          _Trust(
                            Icons.request_quote,
                            context.tr('trust_quotes'),
                          ),
                          _Trust(Icons.reviews, context.tr('trust_reviews')),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Petit argument de confiance sous le bouton (icône + texte).
class _Trust extends StatelessWidget {
  const _Trust(this.icon, this.text);

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    final color = Theme.of(context).colorScheme.primary;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16, color: color),
        const SizedBox(width: 4),
        Text(text, style: Theme.of(context).textTheme.labelMedium),
      ],
    );
  }
}

/// Étape 2 : code OTP (+ nom et rôle pour une inscription).
class OtpScreen extends StatefulWidget {
  const OtpScreen({
    super.key,
    required this.phone,
    required this.purpose,
    this.debugCode,
  });

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
      );
    });
    if (!mounted) return;
    setState(() => _busy = false);
    if (ok) Navigator.of(context).popUntil((r) => r.isFirst);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          _isRegistration ? context.tr('new_account') : context.tr('otp_title'),
        ),
      ),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text(context.tr('otp_sent_to', {'phone': widget.phone})),
            if (widget.debugCode != null) ...[
              const SizedBox(height: 8),
              Text(
                context.tr('dev_code', {'code': widget.debugCode}),
                style: const TextStyle(color: Colors.deepOrange),
              ),
            ],
            const SizedBox(height: 20),
            TextFormField(
              controller: _code,
              keyboardType: TextInputType.number,
              textDirection: TextDirection.ltr,
              maxLength: 6,
              decoration: InputDecoration(
                labelText: context.tr('otp_code'),
                prefixIcon: const Icon(Icons.sms),
              ),
              validator: (v) =>
                  (v ?? '').trim().length < 4 ? context.tr('required') : null,
            ),
            if (_isRegistration) ...[
              TextFormField(
                controller: _name,
                textCapitalization: TextCapitalization.words,
                decoration: InputDecoration(
                  labelText: context.tr('full_name'),
                  prefixIcon: const Icon(Icons.person),
                ),
                validator: (v) =>
                    (v ?? '').trim().isEmpty ? context.tr('required') : null,
              ),
            ],
            const SizedBox(height: 20),
            FilledButton(
              onPressed: _busy ? null : _verify,
              child: _busy
                  ? const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Text(context.tr('verify')),
            ),
          ],
        ),
      ),
    );
  }
}
