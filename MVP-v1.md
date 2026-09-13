# MVP v1 — Tous Types de Bricolages (TTB)

> Périmètre réduit du cahier des charges v1.0, calibré pour : **1 développeur, temps libre, budget ~0 €, Android uniquement, paiement espèces, 1 wilaya**.
> Objectif : une marketplace fonctionnelle testable avec ~50 prestataires + ~200 clients sur une seule wilaya.
> Durée estimée : **3 à 5 mois** de développement en temps libre.

---

## 1. Principe directeur

On garde **le cœur de la boucle marketplace** et rien d'autre :

> Un client publie une demande → des prestataires de la zone envoient un devis → le client en accepte un → ils se parlent → la mission se fait → paiement espèces → évaluation.

Tout ce qui n'est pas nécessaire à cette boucle est reporté (v2+).

---

## 2. Périmètre MVP

### 2.1 DANS le MVP

| Domaine | Ce qu'on garde |
|---|---|
| Plateformes | **App Android (Flutter)** + back-office (Django admin) |
| Auth | Inscription **téléphone + OTP SMS** (via Firebase Phone Auth), choix rôle client/prestataire (cumul possible), vérification obligatoire avant publication/réponse |
| Profil client | Nom, téléphone, 1 à 3 adresses avec point GPS, historique des demandes, langue (FR/AR) |
| Profil prestataire | Identité + photo, statut juridique (déclaré / non déclaré), pièce justificative (photo), wilaya + communes d'intervention, rayon km, jusqu'à **5 catégories**, années d'expérience, description, note moyenne, badge « Identité vérifiée » |
| Catalogue | Arbre **Catégorie → Prestation** (2 niveaux au lieu de 3), ~30 catégories seedées, libellé FR/AR, icône, fourchette de prix indicative. Géré via Django admin. |
| Demande | Catégorie, titre, description libre, **jusqu'à 4 photos**, adresse (carnet ou GPS), urgence (immédiat / aujourd'hui / cette semaine / flexible), budget optionnel. **Formulaire générique** (pas de formulaire dynamique par catégorie en v1). |
| Cycle de vie demande | `PUBLIEE → DEVIS_RECUS → ATTRIBUEE → EN_COURS → TERMINEE → EVALUEE → CLOTUREE` + `ANNULEE` / `EXPIREE` |
| Règles | Expiration après 7 j sans attribution ; max 5 demandes actives par client ; coordonnées cachées jusqu'à acceptation ; filtrage regex des numéros de téléphone dans la messagerie avant attribution |
| Devis | Montant, délai d'intervention, message. Le client compare (montant, note, distance). Acceptation → les autres devis refusés automatiquement + coordonnées échangées. Validité 72 h. |
| Messagerie | Par demande, client ↔ prestataire. Texte + photos. **Par polling REST** (pas de WebSocket en v1) + notification push. Conservation 12 mois. Bouton « Signaler ». |
| Mission | Confirmation du RDV par les 2 parties, bouton « Démarrer » / « Terminer », photos avant/après **optionnelles**. |
| Paiement | **Espèces uniquement.** Le client marque « payé », le prestataire confirme. Aucune commission prélevée (gratuité totale, aligné avec la reco du CDC). |
| Évaluation | Note 1–5 + commentaire sous 7 j, **évaluation croisée** (le prestataire note aussi le client), affichage de la note moyenne. Pas de suppression d'avis négatif. |
| Notifications | **Push (FCM) uniquement** : nouveau devis, devis accepté/refusé, nouveau message, nouvelle demande dans ma zone, rappel RDV J-1. |
| Back-office | **Django admin** : valider/refuser prestataires (avec pièce), gérer le catalogue, consulter demandes/missions, suspendre un utilisateur, voir les signalements. |
| Conformité | CGU + politique de confidentialité FR/AR acceptées à l'inscription, statut « intermédiaire non employeur », suppression de compte + export des données. |

### 2.2 HORS MVP (reporté v2+)

- Application **iOS**
- **Site web** complet + SEO des profils prestataires (une simple landing page statique suffit)
- **Paiement en ligne** SATIM / CIB / Edahabia / BaridiMob, portefeuille interne, séquestre
- **Commission** technique / abonnements / packs de devis / mise en avant payante
- **Formulaires dynamiques** par catégorie (JSON)
- Messagerie **temps réel** (WebSocket), accusés de lecture, « en train d'écrire »
- **Message vocal** dans la demande et la messagerie
- Repli **SMS** pour les notifications (on garde le SMS seulement pour l'OTP)
- Connexion **sociale** (Google/Facebook), 2FA back-office
- **Contre-proposition** sur devis, avenants / travaux supplémentaires
- **Bon d'intervention** signé à l'écran
- Suivi de **position en temps réel** (« je suis en route »)
- **Litiges** outillés (en v1 : traités à la main par email / téléphone)
- Badges avancés (« Top prestataire », « Réponse rapide », « Ponctuel »)
- Recherche **vocale**, tolérance aux fautes avancée
- Codes promo, bannières, notifications de masse
- Statistiques avancées prestataire, carte de chaleur admin
- Familles (3ᵉ niveau de catalogue), réordonnancement no-code, catégories « sensibles » avec casier judiciaire
- 3ᵉ langue (EN / Tamazight)

### 2.3 Arbitrages retenus pour le MVP (à confirmer)

| Point | Décision MVP proposée | Raison |
|---|---|---|
| Prestataires non déclarés | **Acceptés**, avec statut affiché (« Non déclaré » vs « Professionnel déclaré ») | Sinon l'offre est trop mince pour amorcer |
| Modèle économique | **Gratuit total** pendant toute la durée du MVP | Amorçage ; pas de paiement en ligne donc pas de commission fiable |
| Formulaire de demande | **Un seul formulaire générique** | Les formulaires dynamiques = gros chantier, faible valeur au début |
| Messagerie | **Polling REST toutes les 5–10 s** quand la conversation est ouverte | WebSocket = coût d'hébergement (RAM, process) et complexité |
| Hébergement | **Oracle Cloud Always Free** (VM ARM, gratuite à vie) ou Fly.io free | 0 € |
| Cartographie | **OpenStreetMap** (flutter_map + tuiles OSM, géocodage Nominatim) | 0 €, pas de carte bancaire à fournir |
| OTP SMS | **Firebase Phone Auth** (quota gratuit) | Pas de contrat avec un agrégateur SMS local au début |
| Distribution de l'APK | **Téléchargement direct + Firebase App Distribution** | Play Store = 25 $ une fois, à faire juste avant la bêta publique |

---

## 3. Écrans de l'application (Flutter)

### Commun
1. Onboarding (3 écrans) + « parcourir sans compte »
2. Saisie téléphone → saisie OTP → choix du rôle
3. Sélecteur de langue (FR / AR + RTL)

### Client
4. Accueil : gros bouton « Publier une demande » + catégories en icônes + mes demandes en cours
5. Création de demande (assistant en 4 étapes : catégorie → détails+photos → adresse → urgence+budget → récap)
6. Détail d'une demande : liste des devis reçus, comparaison
7. Fiche prestataire publique (photo, note, avis, catégories, zone)
8. Conversation
9. Suivi de mission (RDV, démarrer/terminer, marquer payé)
10. Écran d'évaluation
11. Profil : adresses, historique, favoris, paramètres de notification, langue

### Prestataire
12. Fil des demandes disponibles (filtrées par zone + catégories)
13. Détail d'une demande + formulaire d'envoi de devis
14. Mes devis (en attente / acceptés / refusés)
15. Mes missions (planifiées / en cours / terminées)
16. Conversation
17. Suivi de mission côté prestataire + évaluation du client
18. Édition du profil prestataire : catégories, zone, rayon, pièces justificatives, disponibilités, portfolio (jusqu'à 10 photos)
19. Tableau de bord simple : nombre de devis envoyés, taux d'acceptation, note moyenne

---

## 4. Modèle de données MVP

| Entité | Champs clés |
|---|---|
| **Utilisateur** | id, téléphone (unique, vérifié), email (optionnel), rôles [client, prestataire], statut (actif / suspendu), langue, date d'inscription, dernier login, fcm_token |
| **ProfilClient** | utilisateur, nom, prénom, photo, score_fiabilité (calculé) |
| **ProfilPrestataire** | utilisateur, raison_sociale, statut_juridique, rc_nif (optionnel), bio, années_expérience, rayon_km, wilaya, statut_vérification (en_attente / validé / refusé), note_moyenne, nb_missions |
| **DocumentPrestataire** | prestataire, type (pièce_identité / registre_commerce / diplôme), fichier, statut, uploadé_le, supprimé_après_validation (bool) |
| **Adresse** | utilisateur, libellé, wilaya, commune, quartier, rue, point GPS (PostGIS), indications |
| **Categorie** | parent (nullable), libellé_fr, libellé_ar, icône, description, unité (forfait / heure / m² / jour), prix_min, prix_max, actif, ordre |
| **PrestataireCategorie** | prestataire, catégorie, années_expérience, tarif_horaire (optionnel), forfait (optionnel) |
| **Demande** | client, catégorie, titre, description, photos (jusqu'à 4), adresse, point GPS, urgence, budget_min, budget_max, statut, publiée_le, expire_le |
| **Devis** | demande, prestataire, montant, délai_jours, durée_estimée, message, statut (envoyé / accepté / refusé / expiré), valide_jusqu'au |
| **Mission** | demande, devis_retenu, date_planifiée, confirmée_client (bool), confirmée_prestataire (bool), date_début, date_fin, statut, photos_avant, photos_après, payée_le, paiement_confirmé_prestataire (bool) |
| **Message** | demande, expéditeur, type (texte / photo), contenu, pièce_jointe, lu_le, signalé (bool) |
| **Avis** | mission, auteur, cible, note_globale, commentaire, statut_modération, réponse (optionnelle) |
| **Notification** | destinataire, type, titre, corps, canal (push), lue, date |
| **JournalAudit** | acteur, action, objet, date, IP (actions admin uniquement) |

Retiré par rapport au CDC : `Famille` (fusionnée dans `Categorie` via `parent`), `Transaction` (remplacée par les champs `payée_le` de `Mission`), `Abonnement`, `Litige` (géré hors app en v1), `Conversation` (une demande = une conversation).

---

## 5. Stack technique MVP (0 €)

| Couche | Choix | Coût |
|---|---|---|
| Backend | Django 5 + Django REST Framework | 0 |
| Base de données | PostgreSQL 16 + PostGIS | 0 |
| Cache / tâches | Redis + **django management commands via cron** au début (Celery quand nécessaire) | 0 |
| Auth OTP | Firebase Authentication (Phone) | 0 (quota gratuit) |
| Push | Firebase Cloud Messaging | 0 |
| Stockage fichiers | Disque de la VM au début → Cloudflare R2 (10 Go gratuits) ensuite | 0 |
| Cartes | flutter_map + tuiles OpenStreetMap + Nominatim (géocodage) | 0 |
| Mobile | Flutter (Android), APK signé distribué en direct + Firebase App Distribution | 0 (Play Store 25 $ plus tard) |
| Hébergement | Oracle Cloud Always Free (VM ARM Ampere 4 vCPU / 24 Go) ou Fly.io / Render free | 0 |
| CI | GitHub Actions | 0 (quota gratuit) |
| Suivi d'erreurs | Sentry (offre gratuite) | 0 |

---

## 6. Ordre de construction proposé (jalons)

| Jalon | Contenu | Livrable vérifiable |
|---|---|---|
| **J1 — Fondations** | Projet Django, modèles, migrations, PostGIS, Django admin de base, auth téléphone + OTP (Firebase → vérif token côté backend), JWT | Je peux créer un compte via l'API et me connecter |
| **J2 — Catalogue + demandes** | Seed des ~30 catégories, CRUD demande, upload photos, adresses + GPS | Un client crée une demande depuis Postman/curl |
| **J3 — Matching + devis** | Requête géo (prestataires dont la zone couvre la commune + catégorie), fil de demandes prestataire, envoi/acceptation de devis, échange des coordonnées | La boucle demande→devis→acceptation fonctionne via l'API |
| **J4 — Messagerie + push** | Messages REST + polling, filtrage regex des numéros, intégration FCM, notifications clés | Deux comptes discutent, reçoivent les push |
| **J5 — App Flutter client** | Écrans 1–11, i18n FR/AR + RTL, cache hors ligne des brouillons | APK : un client publie une demande et accepte un devis |
| **J6 — App Flutter prestataire** | Écrans 12–19, upload pièces justificatives, portfolio | APK complet : un prestataire répond et gère ses missions |
| **J7 — Missions + évaluations** | Confirmation RDV, démarrer/terminer, paiement espèces, évaluation croisée, calcul note moyenne + score fiabilité | Un cycle complet de bout en bout |
| **J8 — Back-office + durcissement** | Personnalisation Django admin (validation prestataires, signalements), rate limiting, HTTPS, sauvegardes, CGU FR/AR, tests (cible 60–70 % backend) | Prêt pour bêta fermée sur 1 wilaya |

---

## 7. Ce qu'il faut préparer en parallèle (non technique)

- Choisir **la wilaya de lancement**
- Rédiger **CGU + politique de confidentialité** FR/AR (statut d'intermédiaire, responsabilité limitée)
- Se renseigner sur la **déclaration ANPDP** (loi 18-07) — obligatoire avant mise en service publique
- **Nom commercial** définitif + nom de domaine + (plus tard) dépôt INAPI
- Lister **30 catégories** prioritaires avec libellés FR/AR et fourchettes de prix
- Trouver une **icône par catégorie** (jeu d'icônes libre : Tabler, Lucide, Noun Project)
- Préparer le **compte Firebase** et le **compte Oracle Cloud / Fly.io**

---

## 8. Questions encore ouvertes

1. Firebase Phone Auth fonctionne-t-il correctement avec les numéros algériens (+213) et les opérateurs locaux ? → à tester tôt, sinon repli sur un agrégateur SMS (coût).
2. Oracle Cloud Always Free est-il accessible / stable depuis l'Algérie ? Sinon : Fly.io, Render, ou petit VPS Contabo (~5 €/mois).
3. Accepte-t-on la géoloc approximative (commune) si l'utilisateur refuse le GPS précis ?
4. Langue par défaut à l'installation : FR ou AR ?
