# TTB — Backend (MVP)

API Django + DRF pour la marketplace « Tous Types de Bricolages ».
Cible : MVP 6 semaines, 1 wilaya, paiement espèces, app Android.

## Prérequis

- Python 3.13
- (prod) PostgreSQL 16

## Démarrage (dev)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
copy .env.example .env            # cp .env.example .env  (Linux/mac)

python manage.py migrate
python manage.py seed_base        # 10 catégories + wilaya d'Alger + communes
python manage.py createsuperuser --phone +213770000000
python manage.py runserver
```

- API : http://127.0.0.1:8000/api/
- Admin / back-office : http://127.0.0.1:8000/admin/

## Configuration (.env)

| Variable | Rôle |
|---|---|
| `DJANGO_SECRET_KEY` | clé secrète (obligatoire en prod) |
| `DJANGO_DEBUG` | `True` en dev, `False` en prod |
| `DJANGO_ALLOWED_HOSTS` | domaines autorisés, séparés par virgule |
| `DATABASE_URL` | vide → SQLite ; `postgres://user:pass@host:5432/db` en prod |
| `SMS_BACKEND` | `console` (dev, code affiché dans les logs) / `http` (fournisseur SMS, réglages `SMS_*` : voir `.env.example` et `docs/sms-aggregator-brief.md`) |
| `OTP_TTL_SECONDS` | durée de validité d'un code OTP (défaut 300) |
| `ANTHROPIC_API_KEY` | clé API Claude ; vide → fonctions IA désactivées |
| `AI_MODEL` | modèle Claude (défaut `claude-opus-5-5`) |

En `DEBUG=True`, `POST /api/auth/otp/request/` renvoie `debug_code` dans la réponse
(pas de vrai SMS à envoyer pendant le développement).

## Authentification (Jalon 1 — fait)

| Endpoint | Méthode | Description |
|---|---|---|
| `/api/health/` | GET | ping |
| `/api/auth/otp/request/` | POST | `{phone, purpose}` → envoie un OTP. `purpose` ∈ `registration\|login\|password_reset` |
| `/api/auth/otp/verify/` | POST | `{phone, code, purpose, full_name?, as_provider?, language?}` → crée/identifie l'utilisateur, renvoie `{tokens:{access,refresh}, user}` |
| `/api/auth/token/refresh/` | POST | `{refresh}` → nouveau `access` |
| `/api/auth/logout/` | POST | `{refresh}` → blackliste le refresh token |
| `/api/auth/me/` | GET / PATCH | profil de l'utilisateur connecté |

- Numéros acceptés au format local (`0661…`) ou E.164 (`+213661…`), normalisés en `+213…`.
- Le téléphone doit être vérifié (OTP) avant toute publication ou réponse (règle AUT-06).
- JWT : access 30 min, refresh 30 j rotatif + blacklist.

## Catalogue, localisation, demandes (Jalon 2 — fait)

| Endpoint | Méthode | Accès | Description |
|---|---|---|---|
| `/api/categories/` | GET | public | 10 catégories racines + prestations imbriquées |
| `/api/categories/{slug}/` | GET | public | détail d'une catégorie |
| `/api/wilayas/` | GET | public | wilayas (`?is_active=true`) |
| `/api/communes/?wilaya={id}` | GET | public | communes d'une wilaya |
| `/api/addresses/` | GET/POST | connecté | carnet d'adresses (isolé par utilisateur) |
| `/api/addresses/{id}/` | GET/PATCH/DELETE | propriétaire | — |
| `/api/requests/` | GET | client | mes demandes (`?status=`, `?category=`) |
| `/api/requests/` | POST | client | créer (brouillon ; `publish_now:true` pour publier direct) |
| `/api/requests/{id}/` | PATCH/DELETE | propriétaire | modifiable **uniquement en brouillon** |
| `/api/requests/{id}/publish/` | POST | propriétaire | publier (RG-03 : max 5 actives ; expire à J+7) |
| `/api/requests/{id}/cancel/` | POST | propriétaire | annuler |
| `/api/requests/{id}/photos/` | POST (multipart) | propriétaire | ajouter une photo (max 4) |
| `/api/requests/{id}/photos/{photo_id}` | DELETE | propriétaire | supprimer une photo |

Localisation d'une demande : soit `address` (id du carnet), soit `wilaya` + `commune` (+ `latitude`/`longitude` optionnels).

Tâche planifiée (cron, en attendant Celery) :
```bash
python manage.py expire_requests          # RG-02 : expire les demandes à échéance
python manage.py expire_requests --dry-run
```

## Prestataire, devis, missions (Jalon 3 — fait)

| Endpoint | Méthode | Accès | Description |
|---|---|---|---|
| `/api/provider/me/` | GET/PATCH | prestataire | profil (bio, zone, `service_communes`, `radius_km`, `latitude`/`longitude`, `is_available`) |
| `/api/provider/categories/` | GET/POST | prestataire | catégories servies (max 5), tarifs |
| `/api/provider/categories/{id}/` | PATCH/DELETE | prestataire | — |
| `/api/feed/` | GET | prestataire **vérifié** | demandes publiées dans ses catégories **et** ses communes ; tri urgence → date ; `distance_km` (haversine), `already_quoted` |
| `/api/quotes/` | POST | prestataire vérifié | envoyer un devis `{request, amount, lead_time_days, estimated_duration?, message?}` (valide 72 h) |
| `/api/quotes/` | GET | prestataire / client | mes devis (`?status=`, `?request=`) |
| `/api/quotes/{id}/withdraw/` | POST | prestataire | retirer son devis |
| `/api/quotes/{id}/accept/` | POST | client propriétaire | accepter → crée la **mission**, refuse les autres devis, passe la demande en `assigned` |
| `/api/requests/{id}/quotes/` | GET | client propriétaire | comparer les devis reçus (triés par montant) |
| `/api/missions/` | GET | client / prestataire | mes missions (`?status=`) |
| `/api/missions/{id}/` | GET | parties concernées | détail **avec coordonnées** des deux parties (révélées après acceptation — RG-04) |

Un prestataire doit être **`verification_status = approved`** (posé par un modérateur dans
l'admin Django) pour voir le fil et envoyer des devis.

## Messagerie & notifications (Jalon 4 — fait)

| Endpoint | Méthode | Description |
|---|---|---|
| `/api/conversations/` | GET | mes conversations (client ou prestataire) : autre partie, dernier message, non-lus, `contacts_unlocked` |
| `/api/conversations/{id}/messages/` | GET | messages (paginé) ; marque les entrants comme lus |
| `/api/conversations/{id}/messages/` | POST | envoyer `{type:text, body}` ou multipart `{type:photo, attachment}` |
| `/api/conversations/{id}/read/` | POST | tout marquer lu |
| `/api/messages/{id}/flag/` | POST | signaler un message |
| `/api/notifications/` | GET | mes notifications (`?is_read=`, `?type=`) |
| `/api/notifications/unread_count/` | GET | `{unread: n}` |
| `/api/notifications/read_all/` · `/api/notifications/{id}/read/` | POST | marquer lu |
| `/api/devices/` | POST/DELETE | enregistrer / retirer un jeton push (FCM) |

- **Conversation** = 1 fil par (demande, prestataire), créée automatiquement quand le prestataire envoie un devis.
- **RG-05** : `apps/marketplace/text_filters.py` masque numéros de téléphone (y compris chiffres arabes et écrits en lettres) et liens **tant que la demande n'est pas attribuée à ce prestataire**. Le texte original est conservé (`body_raw`) pour la modération.
- À l'acceptation d'un devis : les conversations des prestataires **non retenus** passent en lecture seule (`is_locked`).
- **Notifications** créées pour : devis reçu, devis accepté/refusé, nouveau message. Push via backend pluggable `PUSH_BACKEND` (`console` en dev, `fcm` à implémenter — le projet Firebase existe, FCM est gratuit).

## Suivi de mission & évaluations (Jalon 5 — fait)

| Endpoint | Méthode | Qui | Effet |
|---|---|---|---|
| `/api/missions/{id}/schedule/` | POST `{scheduled_at}` | client ou prestataire | propose un créneau (réinitialise les confirmations) |
| `/api/missions/{id}/confirm/` | POST | client / prestataire | confirme le créneau ; les 2 → `confirmed` |
| `/api/missions/{id}/start/` | POST | prestataire | `in_progress`, demande → `in_progress` |
| `/api/missions/{id}/complete/` | POST | prestataire | `completed`, demande → `completed` |
| `/api/missions/{id}/photos/` | POST multipart `{kind, image}` | prestataire | photo avant/après |
| `/api/missions/{id}/pay/` | POST | client | déclare le paiement espèces |
| `/api/missions/{id}/confirm-payment/` | POST | prestataire | confirme réception ; les 2 → `paid` |
| `/api/missions/{id}/cancel/` | POST | client / prestataire | annule (avant démarrage) ; RG-06 marque l'annulation tardive < 2 h |
| `/api/missions/{id}/review/` | POST `{rating 1-5, comment}` | client | évalue le prestataire (1 fois), recalcule la note, demande → `evaluated` |
| `/api/reviews/{id}/reply/` | POST `{reply}` | prestataire cible | une réponse publique par avis |
| `/api/providers/{id}/` | GET | public | fiche prestataire (note, catégories, badges) |
| `/api/providers/{id}/reviews/` | GET | public | avis publiés du prestataire |

Réputation recalculée dans `apps/marketplace/reputation.py` (note moyenne + `reviews_count` +
`missions_count`) à la fin de mission et à chaque avis.

## Intelligence artificielle (Claude)

Activée dès que `ANTHROPIC_API_KEY` est renseignée dans `.env` (modèle : `AI_MODEL`,
`claude-opus-5-5` par défaut). Sans clé : `/api/ai/*` répond 503 et la modération est ignorée.
Comprend le français, l'arabe et la darija (lettres arabes ou latines).

| Endpoint | Méthode | Description |
|---|---|---|
| `/api/ai/draft-request/` | POST `{text}` | texte libre du client → `{category_id, title, description, urgency, budget_min, budget_max, missing_info[], language}` à pré-remplir dans le formulaire de demande (rien n'est enregistré) |
| `/api/ai/price-estimate/` | POST `{category, description, urgency?, wilaya?, language?}` | fourchette `{min_da, max_da, confidence, explanation, based_on_quotes}`, basée sur le catalogue et les devis réellement acceptés |
| `/api/ai/support/` | POST `{messages:[{role, content}]}` | chatbot d'aide ; l'app renvoie tout l'historique à chaque tour → `{reply}` |

Connectés uniquement, limités à 30 appels/heure/utilisateur (`ai` dans `DEFAULT_THROTTLE_RATES`).

**Modération automatique** (toujours *fail-open* : si l'IA est indisponible, rien n'est bloqué) :
- **Avis** : un avis injurieux, frauduleux ou hors sujet est créé en `moderation_status=pending`
  (invisible publiquement, exclu de la note) en attendant un modérateur.
- **Messages** : analysés en arrière-plan après l'envoi (aucune latence) ; insultes, arnaques et
  contournements que la regex ne voit pas (« ajoute-moi sur Insta ») → `flagged=True`.
- Chaque décision IA est tracée dans le journal d'audit (`action = ai_moderation`, motif inclus).

Code : `apps/ai/` (`client.py` appel API, `prompts.py` prompts système, `services.py` logique).

## Structure

```
backend/
  config/            # settings, urls, wsgi/asgi
  apps/
    accounts/        # User (téléphone), profils client/prestataire, OTP, JWT, device tokens
    catalog/         # Category (arbre 2 niveaux), ProviderCategory
    locations/       # Wilaya, Commune, Address
    marketplace/     # ServiceRequest, Quote, Mission, Message, Review, Notification, AuditLog
    ai/              # Claude : assistant de demande, estimation de prix, support, modération
```

## Tests

```bash
python manage.py test
```

## Écarts assumés vs cahier des charges (MVP)

- **Pas de PostGIS** : lat/lng en `DecimalField`, distance calculée en haversine (Jalon 3).
- **OTP maison** (modèle `PhoneOTP` + SMS pluggable) au lieu de Firebase — voir
  `../docs/firebase-phone-auth-test.md` pour le test terrain à faire avant de trancher.
- Pas de stockage de pièces d'identité : `ProviderProfile.verification_status` est un
  flag posé manuellement par un modérateur (vérification par téléphone en bêta).
- Évaluation à sens unique (client → prestataire).
- Messagerie par polling REST (Jalon 4), pas de WebSocket.
