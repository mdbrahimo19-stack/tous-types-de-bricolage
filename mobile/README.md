# TTB — Application Android (client)

Application Flutter de la marketplace « Tous Types de Bricolages », côté **client** (écrans 1 à 11 du MVP).

## Récupérer l'APK sans installer Flutter

Chaque envoi sur GitHub qui touche `mobile/` lance la compilation (onglet **Actions** → « App mobile (Flutter) »).
En bas de la page du run, téléchargez l'artefact **ttb-debug-apk**, décompressez-le et installez `app-debug.apk` sur le téléphone.

## Lancer en local

```bash
cd mobile
flutter create --platforms=android --org dz.ttb --project-name ttb .   # 1re fois seulement
python3 ../tools/ci/patch_android.py android                           # 1re fois seulement
flutter pub get
flutter run
```

## Relier l'app au serveur Django

- **Émulateur Android** : rien à faire, l'app vise `http://10.0.2.2:8000` (le PC).
- **Vrai téléphone (même Wi-Fi)** : lancez Django avec `python manage.py runserver 0.0.0.0:8000`,
  ajoutez l'IP du PC dans `DJANGO_ALLOWED_HOSTS`, puis dans l'app : **Profil → Serveur** → `http://IP_DU_PC:8000`.
- **Production** : `flutter build apk --dart-define=API_BASE_URL=https://api.votre-domaine.dz`.

En mode `DJANGO_DEBUG=True`, le code OTP s'affiche directement dans l'app (pas de vrai SMS).

## Écrans

| Écran | Fichier |
|---|---|
| Présentation (3 pages) + choix FR/AR, « parcourir sans compte » | `screens/onboarding_screen.dart` |
| Téléphone → code OTP (+ nom, « je suis aussi prestataire ») | `screens/auth_screens.dart` |
| Accueil : bouton « Publier une demande », catégories, demandes en cours | `screens/home_screen.dart` |
| Création de demande (catégorie → détails + 4 photos → adresse → urgence/budget → récap) | `screens/create_request_screen.dart` |
| Mes demandes, détail, comparaison et acceptation des devis | `screens/requests_screen.dart` |
| Fiche prestataire publique + avis | `screens/provider_screen.dart` |
| Conversations et messagerie (rafraîchie toutes les 7 s, photos, signalement) | `screens/conversations_screen.dart`, `screens/chat_screen.dart` |
| Suivi de mission : RDV, coordonnées, « j'ai payé », annulation, avis | `screens/mission_screen.dart` |
| Profil : nom, adresses, langue, serveur, déconnexion | `screens/profile_screen.dart` |
| Notifications | `screens/notifications_screen.dart` |

## Pas encore fait

- Notifications push (FCM) : l'app lit les notifications via l'API, sans push.
- Position GPS de l'adresse (choix wilaya + commune pour l'instant).
- Écrans prestataire (J6).
