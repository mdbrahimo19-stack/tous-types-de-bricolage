# Cahier des charges — Application « Tous Types de Bricolages »

**Plateforme de mise en relation entre particuliers et prestataires de services / artisans**

| | |
|---|---|
| **Nom du projet** | Tous Types de Bricolages (TTB) |
| **Type** | Marketplace de services (modèle C2C / B2C) |
| **Marché cible** | Algérie (déploiement progressif par wilayas) |
| **Version du document** | 1.0 — Brouillon à valider |
| **Date** | Septembre 2026 |

> Les points marqués **[À DÉCIDER]** sont des hypothèses de travail à confirmer par le porteur du projet avant le lancement du développement.

---

## 1. Contexte et présentation du projet

### 1.1 Contexte

Le secteur des services à domicile en Algérie (plomberie, électricité, maçonnerie, peinture, réparation d'électroménager, déménagement, garde d'enfants, aide à domicile…) reste très largement informel. La recherche d'un artisan passe par le bouche-à-oreille, sans visibilité sur les prix, sans garantie de qualité et sans recours en cas de problème.

Côté artisans, la difficulté est symétrique : trouver des clients réguliers dépend du réseau personnel et de la zone géographique.

### 1.2 Objectif général

Créer une plateforme mobile et web qui met en relation, de manière rapide et transparente, un **demandeur** (particulier ou entreprise) et un **prestataire** qualifié, pour tout type de travaux de bricolage et de services à domicile.

### 1.3 Objectifs mesurables (à 12 mois)

| Objectif | Indicateur cible |
|---|---|
| Adoption prestataires | 1 500 prestataires inscrits et vérifiés |
| Adoption clients | 15 000 comptes clients |
| Activité | 2 000 demandes publiées / mois |
| Qualité de service | Délai moyen de 1re réponse < 30 min |
| Taux de concrétisation | > 45 % des demandes aboutissant à une mission |
| Satisfaction | Note moyenne prestataires ≥ 4,2 / 5 |
| Rétention | 30 % de clients ayant commandé au moins 2 fois |

### 1.4 Facteurs différenciants visés

1. **Devis gratuit et contact non payant à l'unité** : le prestataire paie un abonnement ou une commission sur mission conclue, pas un droit d'accès au numéro du client (principal reproche fait aux plateformes existantes).
2. **Garantie satisfaction** : dispositif de médiation et de remboursement en cas de travail non conforme.
3. **Grille tarifaire indicative** par prestation, affichée publiquement.
4. **Vérification d'identité réelle** des prestataires (pièce d'identité + attestation d'activité si professionnel).
5. **Fonctionnement en zone à faible connexion** : application légère, mode dégradé, notifications SMS de secours.

---

## 2. Périmètre du projet

### 2.1 Dans le périmètre (v1)

- Application mobile Android
- Application mobile iOS
- Site web responsive (vitrine + application web complète)
- Back-office d'administration
- API backend commune
- Système de paiement en ligne et hors ligne
- Système de notation et d'avis
- Messagerie instantanée intégrée

### 2.2 Hors périmètre (v1, prévu en v2+)

- Vente de matériel et de pièces détachées
- Abonnements d'entretien récurrents (contrats annuels)
- Version tablette optimisée pour les entreprises
- Programme de parrainage avancé
- Application dédiée aux syndics et gestionnaires d'immeubles
- Support multilingue au-delà de FR / AR

### 2.3 Langues

- **v1** : Français et Arabe (interface complète, avec support RTL pour l'arabe)
- **v2** : Anglais, éventuellement Tamazight **[À DÉCIDER]**

---

## 3. Acteurs du système

| Acteur | Description | Accès |
|---|---|---|
| **Visiteur** | Non inscrit, consulte le catalogue de services, les tarifs indicatifs et les profils publics | Mobile + Web |
| **Client** | Particulier ou entreprise qui publie une demande et sélectionne un prestataire | Mobile + Web |
| **Prestataire** | Artisan indépendant ou petite entreprise qui répond aux demandes | Mobile (+ Web) |
| **Modérateur** | Valide les inscriptions prestataires, modère les avis et les contenus signalés | Back-office |
| **Support / Médiateur** | Traite les litiges, les réclamations et les demandes de remboursement | Back-office |
| **Administrateur** | Gère les catégories, tarifs, commissions, utilisateurs, statistiques | Back-office |
| **Super-administrateur** | Gestion des rôles, paramètres système, journaux d'audit | Back-office |

---

## 4. Arborescence des catégories de services

Structure à 3 niveaux : **Famille → Catégorie → Prestation**.

### 4.1 Familles proposées (10 familles, ~90 catégories)

**1. Bâtiment et gros œuvre**
Maçonnerie, carrelage/faïence, plâtre et placo, étanchéité, charpente, démolition, ferraillage, coffrage.

**2. Second œuvre et finitions**
Peinture intérieure/extérieure, papier peint, pose de parquet, faux plafond, décoration, staff et corniches, vitrerie.

**3. Plomberie et sanitaire**
Fuite d'eau, débouchage canalisation, installation sanitaire, chauffe-eau/chaudière, robinetterie, pompe à eau, bâche à eau.

**4. Électricité et climatisation**
Installation électrique, dépannage, tableau électrique, éclairage, climatiseur (pose/nettoyage/recharge gaz), chauffage central, groupe électrogène.

**5. Menuiserie et métallerie**
Menuiserie bois, aluminium, PVC, portes et fenêtres, cuisine équipée, placard, serrurerie, ferronnerie, portail automatique, rideau métallique.

**6. Réparation d'électroménager et électronique**
Réfrigérateur, machine à laver, four/cuisinière, micro-ondes, téléviseur, ordinateur, téléphone, antenne parabolique.

**7. Nettoyage et entretien**
Nettoyage de fin de chantier, nettoyage de maison, tapis et salons, vitres, désinsectisation/dératisation, vidange de fosse, nettoyage de citerne.

**8. Transport et déménagement**
Déménagement, transport de marchandises, manutention, location de camion avec chauffeur, débarras.

**9. Services à la personne**
Garde d'enfants, aide aux personnes âgées, soins infirmiers à domicile, cours particuliers, coiffure/esthétique à domicile, cuisine événementielle.

**10. Extérieur et divers**
Jardinage, élagage, entretien de piscine, panneaux solaires, caméras de surveillance, informatique/réseaux, événementiel (chapiteaux, sonorisation).

### 4.2 Règles sur les catégories

- Chaque catégorie possède : un libellé FR/AR, une icône, une description, une fourchette de prix indicative, une unité de facturation (forfait / heure / m² / jour), et un formulaire de qualification spécifique.
- Les catégories sont gérées entièrement depuis le back-office (ajout, désactivation, réordonnancement) sans intervention technique.
- Certaines catégories sont marquées « sensibles » (services à la personne, soins) et imposent des vérifications supplémentaires : casier judiciaire, diplôme, attestation.

---

## 5. Fonctionnalités détaillées

### 5.1 Module Authentification et comptes

| Réf. | Fonctionnalité | Priorité |
|---|---|---|
| AUT-01 | Inscription par numéro de téléphone + OTP SMS (méthode principale en Algérie) | Must |
| AUT-02 | Inscription par email + mot de passe | Must |
| AUT-03 | Connexion sociale (Google, Facebook) | Should |
| AUT-04 | Mot de passe oublié (réinitialisation par OTP ou lien email) | Must |
| AUT-05 | Choix du rôle à l'inscription : Client / Prestataire (un compte peut cumuler les deux) | Must |
| AUT-06 | Vérification du numéro obligatoire avant toute publication ou réponse | Must |
| AUT-07 | Gestion de session multi-appareils, déconnexion à distance | Should |
| AUT-08 | Suppression de compte et export des données personnelles (conformité loi 18-07) | Must |
| AUT-09 | Authentification à deux facteurs pour les comptes back-office | Must |

### 5.2 Module Profil client

- Informations : nom, prénom, téléphone, email, photo (facultative)
- Carnet d'adresses : plusieurs adresses enregistrées (domicile, travail, autre) avec géolocalisation sur carte
- Historique des demandes (en cours, terminées, annulées)
- Historique des paiements et factures téléchargeables (PDF)
- Prestataires favoris
- Paramètres de notification (push, SMS, email — par type d'événement)
- Choix de la langue

### 5.3 Module Profil prestataire

**Informations obligatoires**
- Identité complète, photo de profil, téléphone vérifié
- Statut : auto-entrepreneur / artisan inscrit / entreprise / non déclaré **[À DÉCIDER : accepte-t-on les non déclarés ?]**
- Numéro de registre de commerce ou carte d'artisan (si professionnel), NIF
- Wilaya(s) et communes d'intervention, rayon de déplacement en km
- Catégories de services (max. 8) avec niveau d'expérience par catégorie
- Années d'expérience, description libre
- Disponibilités : jours et plages horaires, mode « indisponible » temporaire

**Éléments valorisants**
- Portfolio photo (jusqu'à 20 réalisations, avec légende et catégorie)
- Diplômes, certificats, attestations de formation
- Tarifs personnels par prestation (déplacement, taux horaire, forfaits)
- Badges obtenus : « Identité vérifiée », « Professionnel déclaré », « Top prestataire », « Réponse rapide », « Ponctuel »

**Tableau de bord prestataire**
- Demandes disponibles dans sa zone et ses catégories (fil d'actualité)
- Mes devis envoyés (en attente / acceptés / refusés)
- Mes missions (planifiées / en cours / terminées)
- Revenus : période, missions payées, commissions retenues, solde à percevoir
- Statistiques : taux de réponse, taux d'acceptation, note moyenne, vues du profil

### 5.4 Module Demande de service (cœur du système)

**Parcours de création (client) — objectif : moins de 90 secondes**

1. Choix de la catégorie (recherche, icônes, ou saisie libre avec suggestion automatique)
2. Formulaire dynamique adapté à la catégorie
   *Exemple pour « Fuite d'eau » : localisation de la fuite, type de canalisation, depuis quand, eau coupée ou non.*
   *Exemple pour « Peinture » : surface en m², nombre de pièces, avec ou sans fourniture, type de peinture.*
3. Ajout de photos (jusqu'à 8) et d'un message vocal facultatif (très utile pour les utilisateurs peu à l'aise avec l'écrit)
4. Adresse d'intervention (carnet d'adresses ou position GPS)
5. Urgence : immédiat (< 2 h) / aujourd'hui / cette semaine / date précise / flexible
6. Budget estimé (fourchette facultative)
7. Récapitulatif et publication

**Cycle de vie d'une demande**

```
BROUILLON → PUBLIÉE → DEVIS_REÇUS → ATTRIBUÉE → PLANIFIÉE
   → EN_COURS → TERMINÉE → PAYÉE → ÉVALUÉE → CLÔTURÉE
                    ↘ ANNULÉE / EXPIRÉE / EN_LITIGE
```

**Règles de gestion**
- RG-01 : une demande publiée est diffusée aux prestataires correspondant à la catégorie **et** couvrant la commune, classés par pertinence (note, proximité, taux de réponse).
- RG-02 : une demande expire automatiquement après 7 jours sans attribution (paramétrable).
- RG-03 : un client peut avoir au maximum 5 demandes actives simultanément (anti-spam).
- RG-04 : les coordonnées directes (téléphone, adresse exacte) ne sont dévoilées qu'après acceptation d'un devis.
- RG-05 : la messagerie filtre automatiquement les numéros de téléphone et liens tant que la mission n'est pas attribuée.
- RG-06 : une demande annulée moins de 2 h avant l'heure convenue est notifiée au prestataire et impacte le score de fiabilité du client.

### 5.5 Module Devis et négociation

- Le prestataire consulte une demande et envoie un **devis** : montant (ou fourchette), délai d'intervention, durée estimée, détail des postes (main-d'œuvre / fourniture / déplacement), message personnalisé.
- Le client reçoit une notification et compare les devis côte à côte (montant, note, distance, délai).
- Possibilité de poser des questions au prestataire avant acceptation (messagerie).
- Contre-proposition possible par le client (1 aller-retour minimum).
- À l'acceptation : les autres devis sont automatiquement refusés avec notification, la mission est créée et les coordonnées échangées.
- Devis valable 72 h par défaut.

### 5.6 Module Messagerie instantanée

- Conversation par demande, entre client et prestataire uniquement
- Messages texte, photos, messages vocaux, partage de position
- Accusés de lecture, indicateur « en train d'écrire »
- Notifications push, repli SMS si le destinataire est hors ligne depuis > 15 min sur une demande urgente
- Conservation des conversations pendant 12 mois (preuve en cas de litige)
- Bouton « Signaler » sur chaque conversation
- Filtrage anti-contournement avant attribution (voir RG-05)

### 5.7 Module Planification et suivi de mission

- Confirmation de rendez-vous par les deux parties
- Rappel automatique J-1 et H-2
- Bouton « Je suis en route » avec partage de position en temps réel (facultatif, limité à 2 h)
- Pointage début / fin d'intervention
- Photos avant / après (obligatoires pour déclencher le paiement sur certaines catégories)
- Bon d'intervention numérique signé par le client sur l'écran
- Gestion des travaux supplémentaires : avenant à valider par le client dans l'app

### 5.8 Module Paiement

**Modes de paiement (v1)**

| Mode | Description | Priorité |
|---|---|---|
| Espèces à la fin de la mission | Le client confirme le paiement dans l'app | Must |
| Carte CIB / Edahabia via SATIM | Paiement en ligne | Must |
| BaridiMob / virement CCP | Justificatif à téléverser ou API si disponible | Should |
| Portefeuille interne | Solde rechargeable, cagnotte de parrainage | Could |

**Modèle économique [À DÉCIDER — 3 options à arbitrer]**

- **Option A — Commission** : X % du montant de la mission prélevé au prestataire (recommandé : 8 à 12 %). Nécessite un paiement en ligne pour être fiable.
- **Option B — Abonnement prestataire** : forfait mensuel (ex. 1 500 / 3 000 / 5 000 DA) donnant droit à un nombre de devis, illimité pour le palier supérieur. Plus simple à encaisser dans un marché à dominante espèces.
- **Option C — Modèle mixte** : abonnement de base gratuit avec quota de devis mensuels + achat de packs de devis + mise en avant payante du profil.

> **Recommandation** : démarrer avec l'option C (gratuité totale les 6 premiers mois pour amorcer l'offre), puis introduire la commission une fois le paiement en ligne adopté.

**Séquestre (à partir de la v2)**
Le client paie à l'acceptation, les fonds sont bloqués et libérés au prestataire 48 h après validation de la mission, sauf litige ouvert.

### 5.9 Module Évaluation et réputation

- Note de 1 à 5 étoiles + commentaire, dans les 7 jours suivant la fin de mission
- Critères détaillés : qualité du travail, respect des délais, propreté, tarif conforme, relationnel
- Évaluation croisée : le prestataire note aussi le client (ponctualité, clarté de la demande, paiement)
- Publication après modération automatique (langage) + manuelle si signalement
- Droit de réponse du prestataire (une réponse publique par avis)
- Le score de réputation combine : note moyenne pondérée, nombre de missions, taux de réponse, taux d'annulation, ancienneté
- Interdiction de supprimer un avis négatif ; seul un avis frauduleux ou injurieux est retiré, avec traçabilité

### 5.10 Module Recherche et découverte

- Recherche par mot-clé avec suggestion automatique et tolérance aux fautes
- Recherche vocale (utile pour l'arabe dialectal) **[Should]**
- Filtres : catégorie, wilaya/commune, note minimale, prix, disponibilité, badges, distance
- Tri : pertinence, proximité, note, prix, réactivité
- Vue carte des prestataires disponibles à proximité
- Page publique de chaque prestataire, référencée sur le web (SEO)

### 5.11 Module Notifications

| Événement | Push | SMS | Email |
|---|---|---|---|
| Nouveau devis reçu | ✔ | si urgent | ✔ |
| Devis accepté / refusé | ✔ | ✔ | ✔ |
| Nouveau message | ✔ | — | — |
| Rappel de rendez-vous | ✔ | ✔ | — |
| Mission terminée / demande d'évaluation | ✔ | — | ✔ |
| Paiement reçu | ✔ | ✔ | ✔ |
| Nouvelle demande dans ma zone (prestataire) | ✔ | — | — |
| Compte validé / rejeté | ✔ | ✔ | ✔ |

Chaque utilisateur peut désactiver individuellement les notifications non critiques.

### 5.12 Back-office d'administration

**Tableau de bord**
Demandes du jour, missions en cours, chiffre d'affaires, inscriptions, taux de concrétisation, carte de chaleur des demandes par wilaya.

**Gestion des utilisateurs**
Recherche, consultation de fiche, suspension, bannissement, historique complet des actions, fusion de doublons.

**Validation des prestataires**
File d'attente des inscriptions, consultation des pièces justificatives, validation/refus motivé, attribution des badges.

**Gestion du catalogue**
Familles, catégories, prestations, formulaires dynamiques, tarifs indicatifs, icônes, ordre d'affichage.

**Modération**
Avis signalés, conversations signalées, photos, profils suspects, mots interdits.

**Litiges**
Ouverture, pièces jointes des deux parties, historique de la conversation, décision, remboursement, clôture.

**Finance**
Transactions, commissions, abonnements, factures, versements aux prestataires, exports comptables (CSV / Excel).

**Marketing**
Codes promo, bannières d'accueil, notifications de masse ciblées (par wilaya, catégorie, segment).

**Système**
Rôles et permissions, paramètres (délais, quotas, rayons), journal d'audit de toutes les actions administratives.

---

## 6. Exigences techniques

### 6.1 Architecture cible

```
   Mobile Android / iOS          Web (Next.js ou Django templates)
              │                            │
              └────────── API REST ────────┘
                          │
              ┌───────────┴───────────┐
              │  Backend Django + DRF │
              └───────────┬───────────┘
       ┌──────────┬───────┼────────┬──────────────┐
   PostgreSQL   Redis   Celery   Stockage      Services tiers
   (+PostGIS)  (cache)  (tâches)  objets    (SMS, SATIM, FCM, Maps)
```

### 6.2 Stack recommandée

| Couche | Technologie | Justification |
|---|---|---|
| Backend | **Django 5 + Django REST Framework** | Maîtrisé en interne, écosystème mature, back-office rapide à produire |
| Base de données | **PostgreSQL 16 + PostGIS** | Requêtes géographiques (rayon, distance) indispensables |
| Cache / file | **Redis** | Sessions, cache, files de tâches |
| Tâches asynchrones | **Celery + Redis** | Notifications, SMS, emails, expiration des demandes, rapports |
| Temps réel | **Django Channels (WebSocket)** | Messagerie et suivi de position |
| Mobile | **Flutter** (recommandé) ou React Native | Une base de code pour Android + iOS, bon rendu RTL, taille d'APK maîtrisée |
| Web | **Next.js** ou templates Django + HTMX | SEO nécessaire pour les pages prestataires |
| Stockage fichiers | S3 compatible (MinIO auto-hébergé ou fournisseur cloud) | Photos, documents |
| Notifications push | Firebase Cloud Messaging | Standard Android/iOS |
| Cartographie | OpenStreetMap + Leaflet, ou Google Maps | Coût vs précision **[À DÉCIDER]** |
| SMS | Agrégateur local (à sélectionner) | OTP et notifications critiques |
| Supervision | Sentry + Grafana/Prometheus | Erreurs et métriques |
| CI/CD | GitHub Actions ou GitLab CI | Déploiements automatisés |

### 6.3 Hébergement

- **[À DÉCIDER]** : hébergement en Algérie (Algérie Télécom, ICOSNET) — obligatoire pour les données personnelles selon l'interprétation de la loi 18-07 — ou hébergement mixte avec CDN.
- Environnements séparés : développement, recette, production.
- Serveur de production : minimum 4 vCPU / 8 Go RAM / 200 Go SSD au lancement, évolutif.
- Sauvegardes : base de données quotidienne (rétention 30 jours) + hebdomadaire (rétention 6 mois), sauvegarde hors site, restauration testée trimestriellement.

### 6.4 Performances attendues

| Critère | Cible |
|---|---|
| Temps de réponse API (p95) | < 500 ms |
| Ouverture de l'application (démarrage à froid) | < 3 s |
| Taille de l'APK | < 30 Mo |
| Disponibilité | 99,5 % |
| Utilisateurs simultanés supportés (v1) | 2 000 |
| Fonctionnement en 3G / réseau instable | Obligatoire (mise en cache, reprise d'envoi) |

### 6.5 Sécurité

- HTTPS obligatoire (TLS 1.2+), HSTS
- Authentification par jeton JWT à courte durée + refresh token révocable
- Mots de passe hachés (Argon2)
- Limitation de débit sur l'authentification, l'OTP et la publication de demandes
- Protection OWASP Top 10, validation stricte de toutes les entrées
- Chiffrement au repos des documents d'identité, suppression automatique après validation
- Journalisation des accès aux données personnelles
- Rôles et permissions granulaires côté back-office
- Test d'intrusion avant mise en production
- Politique de rétention : documents d'identité supprimés après validation, conversations 12 mois, données de compte supprimé anonymisées sous 30 jours

### 6.6 Conformité réglementaire (Algérie)

- **Loi n° 18-07** relative à la protection des personnes physiques dans le traitement des données à caractère personnel : déclaration/autorisation auprès de l'ANPDP avant mise en service.
- Mentions légales, CGU et politique de confidentialité rédigées en français et en arabe, acceptées explicitement à l'inscription.
- Conditions générales de vente et statut de la plateforme (intermédiaire, non employeur des prestataires) clairement établis pour limiter la responsabilité.
- Facturation conforme (NIF, RC, timbre fiscal le cas échéant).
- Loi n° 18-05 sur le commerce électronique : mentions obligatoires du e-commerçant, déclaration au registre du commerce électronique.

---

## 7. Exigences ergonomiques et de conception

- Interface épurée, priorité au parcours « publier une demande » accessible en 1 tap depuis l'accueil
- Support complet **RTL** pour l'arabe (miroir des écrans, alignements, icônes directionnelles)
- Vocabulaire simple, adapté à un public non technophile ; icônes explicites pour chaque catégorie
- Contraste et taille de police conformes WCAG AA ; option grande police
- Mode hors ligne partiel : consultation de l'historique, brouillon de demande enregistré localement
- Onboarding en 3 écrans maximum, avec possibilité de parcourir l'app avant inscription
- Identité visuelle : logo, charte couleurs, jeu d'icônes complet à livrer **[à produire]**

---

## 8. Modèle de données (entités principales)

| Entité | Champs clés |
|---|---|
| **Utilisateur** | id, téléphone, email, mot de passe, rôle(s), statut, langue, date d'inscription, dernière connexion |
| **ProfilClient** | utilisateur, nom, prénom, photo, score de fiabilité |
| **ProfilPrestataire** | utilisateur, raison sociale, statut juridique, RC/NIF, bio, expérience, rayon, statut de vérification, note moyenne, badges |
| **Adresse** | utilisateur, libellé, wilaya, commune, quartier, rue, point GPS, indications |
| **Famille / Catégorie / Prestation** | libellé FR, libellé AR, icône, description, unité, prix min, prix max, formulaire (JSON), actif |
| **PrestataireCategorie** | prestataire, catégorie, années d'expérience, tarif horaire, forfait |
| **Demande** | client, catégorie, titre, description, réponses au formulaire (JSON), photos, audio, adresse, urgence, budget min/max, statut, date de publication, date d'expiration |
| **Devis** | demande, prestataire, montant, détail (JSON), délai, message, statut, date de validité |
| **Mission** | demande, devis retenu, date planifiée, date de début, date de fin, statut, photos avant/après, bon d'intervention |
| **Conversation / Message** | demande, expéditeur, type, contenu, pièce jointe, lu le |
| **Transaction** | mission, mode, montant, commission, statut, référence externe, date |
| **Abonnement** | prestataire, formule, date de début, date de fin, quota restant |
| **Avis** | mission, auteur, cible, note globale, notes détaillées, commentaire, statut de modération, réponse |
| **Litige** | mission, ouvert par, motif, pièces, statut, décision, montant remboursé |
| **Notification** | destinataire, type, titre, corps, canal, lue, date |
| **JournalAudit** | acteur, action, objet, valeurs avant/après, IP, date |

---

## 9. Livrables attendus

1. Maquettes UX/UI complètes (Figma) : mobile client, mobile prestataire, web, back-office
2. Charte graphique et jeu d'icônes des catégories
3. Code source complet, versionné, documenté (dépôt Git privé)
4. Documentation de l'API (OpenAPI / Swagger)
5. Documentation technique : architecture, installation, déploiement, sauvegarde/restauration
6. Applications publiées sur Google Play et App Store (comptes développeur au nom du client)
7. Manuels utilisateurs : client, prestataire, administrateur (FR + AR)
8. Jeu de tests automatisés (couverture ≥ 70 % du backend)
9. Formation : 2 sessions administrateurs, 1 session support
10. Rapport de test d'intrusion et de recette

---

## 10. Planning prévisionnel

| Phase | Contenu | Durée |
|---|---|---|
| **0. Cadrage** | Validation du cahier des charges, arbitrages [À DÉCIDER], choix des prestataires tiers | 2 semaines |
| **1. Conception** | Maquettes, charte graphique, modèle de données, spécifications API | 4 semaines |
| **2. Développement backend** | API, back-office, modèle de données, authentification | 8 semaines |
| **3. Développement mobile** | Application client puis prestataire | 10 semaines (partiellement en parallèle) |
| **4. Web** | Site vitrine + application web + SEO | 4 semaines (en parallèle) |
| **5. Intégrations** | Paiement, SMS, push, cartes | 3 semaines |
| **6. Recette et tests** | Tests fonctionnels, sécurité, correction | 4 semaines |
| **7. Bêta fermée** | 50 prestataires + 200 clients sur 1 wilaya | 4 semaines |
| **8. Lancement** | Publication sur les stores, communication | 2 semaines |
| **Total** | | **≈ 7 à 8 mois** |

---

## 11. Stratégie de lancement

1. **Amorçage de l'offre avant la demande** : recruter 150 à 300 prestataires vérifiés sur une seule wilaya (Alger ou la wilaya d'origine) avant toute communication grand public. Une marketplace vide fait fuir les clients.
2. **Gratuité totale les 6 premiers mois** pour les prestataires.
3. **Prospection terrain** : visite des quincailleries, marchés de matériaux, coopératives d'artisans ; inscription assistée sur place.
4. **Communication** : Facebook et TikTok (canaux dominants en Algérie), vidéos courtes de démonstration, témoignages d'artisans.
5. **Expansion** : une nouvelle wilaya ouverte seulement lorsque 100 prestataires actifs y sont inscrits.

---

## 12. Risques et mesures d'atténuation

| Risque | Impact | Mesure |
|---|---|---|
| Contournement de la plateforme (échange direct hors app) | Élevé | Modèle par abonnement plutôt que commission ; valeur ajoutée (garantie, historique, visibilité) ; filtrage avant attribution |
| Marketplace vide au lancement | Élevé | Amorçage manuel de l'offre, lancement sur une seule wilaya |
| Faible adoption du paiement en ligne | Moyen | Paiement en espèces pleinement supporté dès la v1 |
| Prestataires non déclarés / travail informel | Moyen | Statut clairement affiché, accompagnement à la déclaration, responsabilité limitée dans les CGU |
| Litiges et travaux mal exécutés | Élevé | Procédure de médiation, photos avant/après, notation, exclusion des prestataires récidivistes |
| Non-conformité loi 18-07 | Élevé | Déclaration ANPDP avant lancement, minimisation des données, hébergement local |
| Faux comptes et avis frauduleux | Moyen | Vérification par OTP, avis uniquement après mission réelle, détection d'anomalies |
| Connectivité limitée | Moyen | App légère, mode dégradé, repli SMS |

---

## 13. Points à arbitrer avant lancement du développement

1. Modèle économique retenu (commission / abonnement / mixte) et grille tarifaire
2. Acceptation ou non des prestataires non déclarés
3. Wilaya de lancement et calendrier d'expansion
4. Hébergement local ou externe
5. Fournisseur SMS et fournisseur de cartographie
6. Nom commercial définitif, dépôt de marque INAPI et achat du nom de domaine
7. Statut juridique de la société porteuse et inscription au registre du commerce électronique
8. Budget global et mode de réalisation : développement interne, prestataire externe, ou mixte

---

*Fin du document — version 1.0*
