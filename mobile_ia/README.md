# TTB — Application mobile (Flutter, Android)

Application client + prestataire de « Tous Types de Bricolages », branchée sur le backend
Django de `../backend`. Interface en français et en arabe (RTL automatique).

## Lancer en développement

1. Démarrer le backend (voir `../backend/README.md`) :
   ```bash
   cd ../backend
   .venv\Scripts\activate
   python manage.py runserver 0.0.0.0:8000
   ```
2. Lancer l'app :
   ```bash
   cd mobile_ia
   flutter run                                                   # émulateur Android (API = 10.0.2.2:8000)
   flutter run --dart-define=API_URL=http://192.168.1.20:8000    # téléphone réel : IP du PC sur le Wi-Fi
   ```
   Pour un téléphone réel, ajouter l'IP du PC dans `DJANGO_ALLOWED_HOSTS` du `.env` backend.

En mode `DEBUG` côté Django, le code SMS est renvoyé par l'API et pré-rempli dans l'écran OTP
(aucun vrai SMS n'est envoyé).

## Générer un APK

```bash
flutter build apk --debug       # build/app/outputs/flutter-apk/app-debug.apk
flutter build apk --release --dart-define=API_URL=https://api.mon-domaine.dz
```
Avant une vraie release : configurer une clé de signature, passer l'API en HTTPS et retirer
`android:usesCleartextTraffic="true"` de `android/app/src/main/AndroidManifest.xml`.

## Ce que fait l'application

| Mode | Écrans |
|---|---|
| Tous | Connexion par téléphone + code SMS (inscription automatique si le numéro est nouveau), langue FR/AR, assistance IA (chat) |
| Client | Accueil · **« Décrivez votre problème » (IA)** → demande pré-remplie · formulaire de demande (catégorie, wilaya/commune, urgence, budget, 4 photos, **estimation de prix IA**) · mes demandes · comparaison et acceptation des devis · messagerie · missions (rendez-vous, paiement espèces, avis) |
| Prestataire | Fil des travaux de sa zone · envoi de devis (avec **aide au prix IA**) · mes devis (retrait) · messagerie · missions (démarrer, terminer, confirmer le paiement) · profil (catégories, communes, statut) |

Un compte inscrit comme prestataire peut basculer entre les modes client et prestataire
depuis l'onglet Profil. Le fil des travaux n'apparaît qu'une fois le compte **validé** par un
modérateur dans l'admin Django (`verification_status = approved`).

## Structure

```
lib/
  main.dart            # point d'entrée, thème, langues
  config.dart          # URL de l'API (--dart-define=API_URL), délais
  l10n.dart            # textes FR / AR
  api/api_client.dart  # HTTP + JWT (refresh automatique), erreurs DRF, pagination
  state/session.dart   # compte connecté, langue, mode client/prestataire
  widgets/common.dart  # chargement, erreurs, sélecteurs catégorie / wilaya / commune
  screens/
    auth.dart          # téléphone + OTP
    shell.dart         # onglets + profil
    client.dart        # accueil, IA, formulaire, demandes, devis
    provider.dart      # fil, devis, profil prestataire
    shared.dart        # messagerie, missions, assistance IA
```

## Pas encore fait (v2)

- Notifications push (FCM) — la messagerie se rafraîchit toutes les 7 s quand elle est ouverte
- Carnet d'adresses et position GPS dans le formulaire de demande
- Portfolio photo et pièce d'identité du prestataire, photos avant/après de mission
- Mode hors ligne (brouillons enregistrés localement)
