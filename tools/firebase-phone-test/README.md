# Testeur Firebase Phone Auth (+213)

Deux tests, dans l'ordre :

1. **Test web** (ici, ~15 min) — premier signal : est-ce que Firebase envoie un SMS vers +213 ?
2. **Test Android** (voir `../../docs/firebase-phone-auth-test.md`) — le vrai verdict, par opérateur.

---

## A. Créer le projet Firebase (une fois)

1. https://console.firebase.google.com → **Créer un projet** → nom `ttb-dev`
   (Google Analytics : pas nécessaire, tu peux décocher).
2. Dans le projet : **Build → Authentication → Get started**.
3. Onglet **Sign-in method** → **Phone** → **Enable** → Save.
4. Onglet **Settings → Authorized domains** → **Add domain** → `localhost`.
5. **⚙️ (Paramètres du projet) → Général → Vos applications → icône Web `</>`**
   - Surnom : `ttb-web-test`. **Ne pas** cocher Firebase Hosting.
   - Firebase affiche `const firebaseConfig = { apiKey: "...", ... }` → garde cet objet.

### Numéros de test fictifs (optionnel, pour tester le *flux* sans SMS)

**Authentication → Settings → Phone numbers for testing** → ajoute
`+213661000000` / code `654321`. Ces numéros n'envoient jamais de SMS et acceptent
toujours le code fixe. Utile pour valider le code de l'app, **inutile pour la délivrabilité**.

---

## B. Lancer le testeur web

Le SDK se charge mieux via un petit serveur local (plutôt qu'un double-clic `file://`).
Dans ce dossier :

```bash
# Python (déjà installé)
python -m http.server 5500
# ou Node
npx --yes serve -l 5500
```

Puis ouvre http://localhost:5500

1. Colle le `firebaseConfig` (en JSON — mets des guillemets sur les clés) → **Initialiser**.
2. Résous le reCAPTCHA affiché.
3. Saisis **ton vrai numéro** au format `+213XXXXXXXXX` → **Envoyer le SMS**.
4. **Chronomètre** : note l'heure d'envoi (dans le journal) et l'heure d'arrivée du SMS sur le téléphone.
5. Saisis le code → **Vérifier**. Si ça marche, tu obtiens un `ID TOKEN`.

### Erreurs fréquentes

| Code | Cause / solution |
|---|---|
| `auth/operation-not-allowed` | Phone non activé (étape A.3) |
| `auth/unauthorized-domain` | `localhost` pas dans Authorized domains (étape A.4) |
| `auth/quota-exceeded` / `auth/too-many-requests` | quota SMS gratuit épuisé pour aujourd'hui → réessaie demain, ou attends |
| `auth/captcha-check-failed` | reCAPTCHA expiré, recharge la page |
| `auth/invalid-app-credential` | config incomplète, recopie tout l'objet |

---

## C. Ce que ce test web NE dit PAS

- La délivrabilité **par opérateur** (Djezzy / Mobilis / Ooredoo) depuis une app native.
- Le comportement hors grande ville / en 3G.
- Web et Android natif n'utilisent pas exactement les mêmes routes SMS.

→ Si le test web **échoue** à recevoir le SMS : mauvais signe, passe direct à l'évaluation
d'un agrégateur SMS local.
→ Si le test web **réussit** : continue avec le test Android (`docs/firebase-phone-auth-test.md`)
pour confirmer avant de trancher.

---

## D. Empreintes du keystore de debug (pour l'app Android)

Quand tu ajouteras l'app **Android** dans Firebase (package `com.ttb.app`), colle :

```
SHA-1   : 70:09:CA:EC:35:EE:03:F3:44:54:41:11:DC:06:4A:B6:8F:C2:46:09
SHA-256 : 71:EE:D0:1A:8A:4E:72:60:8C:AB:74:66:35:83:BA:12:18:C9:86:70:EE:A0:EF:B6:4B:6F:0E:DC:DA:71:27:07
```

(généré depuis `~/.android/debug.keystore`, alias `androiddebugkey`, mot de passe `android` —
partagé par tous tes projets Android sur cette machine)

Pour les régénérer :
```bash
& "C:\Program Files\Android\Android Studio\jbr\bin\keytool.exe" -list -v \
  -alias androiddebugkey -keystore "$env:USERPROFILE\.android\debug.keystore" \
  -storepass android -keypass android
```
