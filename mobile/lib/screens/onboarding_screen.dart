import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/i18n.dart';
import '../core/session.dart';
import 'auth_screens.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _ctrl = PageController();
  int _page = 0;

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final session = context.read<Session>();
    final pages = [
      (Icons.handyman, s.t('onb1_t'), s.t('onb1_b')),
      (Icons.request_quote, s.t('onb2_t'), s.t('onb2_b')),
      (Icons.payments, s.t('onb3_t'), s.t('onb3_b')),
    ];
    final last = _page == pages.length - 1;

    return Scaffold(
      body: SafeArea(
        child: Column(children: [
          Align(
            alignment: AlignmentDirectional.topEnd,
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: SegmentedButton<String>(
                segments: const [
                  ButtonSegment(value: 'fr', label: Text('FR')),
                  ButtonSegment(value: 'ar', label: Text('عربي')),
                ],
                selected: {session.locale.languageCode},
                onSelectionChanged: (v) => session.setLanguage(v.first),
              ),
            ),
          ),
          Expanded(
            child: PageView.builder(
              controller: _ctrl,
              itemCount: pages.length,
              onPageChanged: (i) => setState(() => _page = i),
              itemBuilder: (_, i) {
                final (icon, title, body) = pages[i];
                return Padding(
                  padding: const EdgeInsets.all(32),
                  child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                    CircleAvatar(
                      radius: 64,
                      backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                      child: Icon(icon, size: 64, color: Theme.of(context).colorScheme.primary),
                    ),
                    const SizedBox(height: 32),
                    Text(title,
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 16),
                    Text(body, textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodyLarge),
                  ]),
                );
              },
            ),
          ),
          Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            for (var i = 0; i < pages.length; i++)
              Container(
                margin: const EdgeInsets.all(4),
                width: i == _page ? 20 : 8,
                height: 8,
                decoration: BoxDecoration(
                  color: i == _page ? Theme.of(context).colorScheme.primary : Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
          ]),
          Padding(
            padding: const EdgeInsets.all(24),
            child: Column(children: [
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: () async {
                    if (!last) {
                      _ctrl.nextPage(duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
                      return;
                    }
                    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => const PhoneScreen()));
                    if (session.loggedIn) await session.finishOnboarding();
                  },
                  child: Text(last ? s.t('login') : s.t('next')),
                ),
              ),
              TextButton(onPressed: session.finishOnboarding, child: Text(s.t('browse_guest'))),
            ]),
          ),
        ]),
      ),
    );
  }
}
