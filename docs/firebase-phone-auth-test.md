# Test terrain : Firebase Phone Auth avec un numéro +213

---

## ✅ RÉSULTAT DU TEST (2026-09-06) — Firebase Phone Auth ÉCARTÉ

Test web effectué avec le projet `ttb-dev-2bfa8`. Verdict : **inutilisable pour ce projet.**

| Étape | Constat |
|---|---|
| Création projet + activation Phone | OK |
| `localhost` dans Authorized domains | OK |
| Envoi OTP vers `+213…` | ❌ `auth/operation-not-allowed` (SMS region policy) puis, une fois l'Algérie autorisée, ❌ **`auth/billing-not-enabled`** |

**Cause :** depuis fin 2024, Firebase Phone Auth exige le plan **Blaze** (carte bancaire
acceptée par Google + facturation par SMS, sans palier gratuit pour l'Algérie).

**Pourquoi c'est bloquant :**
- Google Cloud Billing n'accepte pas les cartes algériennes (CIB / Edahabia).
- Chaque SMS OTP serait facturé en devises → coût récurrent dès le lancement.

**Décision : on garde le flow OTP maison (déjà codé, `apps/accounts/otp.py`) et on branche
un agrégateur SMS algérien.** Voir `sms-aggregator-brief.md`.

Le reste de ce document (protocole de test Android, etc.) n'est conservé que pour mémoire.

---


**Priorité absolue avant de figer la méthode d'inscription.** Tout l'onboarding TTB
repose sur la réception d'un SMS OTP. Si Firebase ne délivre pas de façon fiable sur
Djezzy / Mobilis / Ooredoo, il faut basculer sur un agrégateur SMS local (coût réel).

> ⚠️ Ce test ne peut **pas** être automatisé ni fait à ma place : il faut un projet
> Firebase réel, une **vraie carte SIM algérienne** dans un téléphone, et une app qui tourne.
> Le backend est déjà codé pour ne pas dépendre du résultat (flow OTP maison, backend SMS `console`).

---

## Pourquoi ce risque est réel

- Firebase Phone Auth passe par des routes SMS internationales (Google → opérateur DZ).
  La délivrabilité des SMS A2P internationaux vers l'Algérie est historiquement irrégulière.
- Les opérateurs algériens filtrent parfois les SMS « application » (expéditeur alphanumérique
  étranger), surtout hors des grandes villes.
- Quota gratuit Firebase : ~10 vérifications SMS/jour en mode test, puis facturation par SMS
  (et disponibilité réelle dépendante du pays).

---

## Étape 1 — Créer le projet Firebase (30 min)

1. https://console.firebase.google.com → **Ajouter un projet** (`ttb-dev`).
2. **Authentication → Sign-in method → Phone** : activer.
3. **Project settings → General** : ajouter une app **Android**
   - package name provisoire : `com.ttb.app`
   - récupérer `google-services.json`
4. **Authentication → Settings → Phone numbers for testing** : ajouter un couple
   `+213...` / code fixe `123456` pour tester le *code* de l'app sans consommer de SMS.
   ⚠️ Ça ne teste PAS la délivrabilité réelle — c'est l'étape 3 qui compte.
5. **Project settings → Service accounts → Generate new private key** :
   fichier `firebase-credentials.json` (pour la vérification côté backend plus tard).
   Le placer dans `backend/` (déjà ignoré par `.gitignore`).

## Étape 2 — App de test minimale (2–3 h)

Le plus rapide : un petit projet Flutter jetable avec `firebase_auth`.

```dart
// pubspec.yaml : firebase_core, firebase_auth
await Firebase.initializeApp();

await FirebaseAuth.instance.verifyPhoneNumber(
  phoneNumber: '+213XXXXXXXXX',
  timeout: const Duration(seconds: 60),
  verificationCompleted: (cred) => print('AUTO-RETRIEVAL OK'),
  verificationFailed: (e) => print('FAILED: ${e.code} ${e.message}'),
  codeSent: (verificationId, resendToken) => print('SMS ENVOYÉ, id=$verificationId'),
  codeAutoRetrievalTimeout: (id) => print('TIMEOUT auto-retrieval'),
);

// Puis, avec le code reçu :
final cred = PhoneAuthProvider.credential(verificationId: id, smsCode: '123456');
final userCred = await FirebaseAuth.instance.signInWithCredential(cred);
final idToken = await userCred.user!.getIdToken();
print('ID TOKEN: $idToken'); // c'est ce que le backend vérifiera
```

- Compiler en APK debug, l'installer sur un téléphone avec **SIM algérienne**.
- Ajouter l'empreinte SHA-1/SHA-256 du keystore debug dans Firebase (sinon erreur
  `app-not-authorized` ou reCAPTCHA web qui s'affiche).

## Étape 3 — Le test qui compte (délivrabilité réelle)

Pour **chaque opérateur** auquel tu as accès (idéalement les 3) :

| # | Test | Résultat attendu |
|---|---|---|
| 1 | Demander un OTP sur un vrai numéro (pas un numéro de test) | SMS reçu |
| 2 | Mesurer le **délai de réception** | < 30 s |
| 3 | Refaire 5 fois d'affilée | 5/5 reçus, pas de blocage |
| 4 | Tester en 3G / zone hors grande ville si possible | SMS reçu |
| 5 | Tester à 2 h du matin et en heure de pointe | pas de différence |
| 6 | Vérifier le nom/format de l'expéditeur du SMS | lisible, pas en spam |
| 7 | Épuiser le quota gratuit → voir le message d'erreur | erreur claire, pas un crash |
| 8 | Numéro déjà vu récemment (anti-abus Firebase) | pas de blocage prématuré |

Note le taux de réussite global : **`reçus / envoyés`**.

## Grille de décision

| Constat | Décision |
|---|---|
| ≥ 95 % de réception, < 30 s, 3 opérateurs | ✅ Firebase Phone Auth pour la v1. On ajoute le backend `firebase` (vérif d'ID token). |
| 70–95 %, ou lent, ou 1 opérateur qui coince | ⚠️ Firebase en principal **+ repli agrégateur** sur échec/renvoi. Plus de travail. |
| < 70 %, ou blocages fréquents | ❌ Agrégateur SMS local dès la v1. On garde le flow OTP maison déjà codé. |

## Agrégateurs SMS locaux (plan B) — à contacter pour devis

- Demander : prix par SMS OTP, délai de mise en place, **sender ID** possible,
  délivrabilité garantie sur les 3 opérateurs, API (HTTP simple), volume minimum.
- Ordre de grandeur à valider : 3–6 DA / SMS.
- Fournisseurs à évaluer : opérateurs directement (offres A2P), ou agrégateurs
  régionaux couvrant l'Algérie. **[À DÉCIDER — point 5 du cahier des charges]**

## Ce qui est déjà prêt côté backend

- `apps/accounts/otp.py` : génération / vérification de code, anti-brute-force (5 essais),
  expiration paramétrable.
- `apps/accounts/sms.py` : `send_sms()` avec backend `console` (dev). Ajouter un backend
  `aggregator` = ~20 lignes (un POST HTTP).
- Si Firebase est retenu : on n'utilise pas `send_sms`. On ajoute un endpoint
  `POST /api/auth/firebase/verify/ {id_token}` qui vérifie le token avec `firebase-admin`
  et applique la même logique `get_or_create_user_after_otp`.

## À reporter ici après le test

```
Date du test :
Opérateurs testés :
Taux de réception (reçus/envoyés) :
Délai médian :
Erreurs rencontrées :
DÉCISION :
```
