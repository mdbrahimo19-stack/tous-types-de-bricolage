# Dossier : choisir un fournisseur SMS (OTP) pour l'Algérie

**Contexte :** Firebase Phone Auth écarté (voir `firebase-phone-auth-test.md`). Le backend
a un flow OTP maison ; il manque juste un service qui **envoie le SMS**. Ce SMS transporte
un code à 6 chiffres, il doit arriver en < 30 s sur Djezzy, Mobilis et Ooredoo.

C'est le **point 5 « [À DÉCIDER] »** du cahier des charges.

---

## 1. Ce qu'il faut (cahier des charges du fournisseur)

| Exigence | Détail |
|---|---|
| SMS A2P transactionnel | catégorie « OTP / verification », priorité haute |
| Couverture | **les 3 opérateurs** algériens, tout le territoire |
| Délai de livraison | < 30 s en heure de pointe |
| Sender ID | idéalement alphanumérique `TTB` (sinon numéro court/long dédié) |
| API | HTTP REST simple (POST avec `to`, `text`, `sender`) + accusé de livraison (DLR) |
| Paiement | en **DA**, facture locale (NIF/RC), prépayé accepté |
| Volume de départ | ~2 000–5 000 SMS/mois en bêta, montée à ~50 000/mois |
| Pas d'engagement long | contrat mensuel ou prépayé, pas 12 mois fermes |

## 2. Pistes à contacter (Algérie)

> Liste de départ à valider — les offres A2P changent souvent. Chercher aussi
> « SMS Pro Algérie », « SMS OTP Algérie », « plateforme SMS entreprise Algérie ».

- **Opérateurs directement** — Mobilis / Djezzy / Ooredoo ont des offres « SMS Pro » /
  « SMS Business » pour entreprises. Avantage : livraison native sur leur réseau.
  Inconvénient : il faut souvent un contrat par opérateur.
- **Agrégateurs / intégrateurs locaux** — sociétés de services télécoms algériennes qui
  revendent l'A2P multi-opérateurs avec une seule API. Demander autour de soi / chambres
  de commerce / groupes d'e-commerçants algériens (beaucoup utilisent déjà du SMS OTP).
- **Agrégateurs régionaux couvrant l'Algérie** (à comparer sur prix + délivrabilité réelle) :
  certains acteurs Maghreb/Moyen-Orient. Vérifier impérativement la délivrabilité sur les
  3 opérateurs avant de signer.
- **International (dépannage uniquement)** — Twilio, Vonage, MessageBird : API excellente
  mais SMS vers Algérie chers (~0,05–0,08 $) et délivrabilité irrégulière ; paiement carte
  étrangère. À garder comme secours, pas comme solution principale.

## 3. Questions à poser (à chaque fournisseur)

1. Prix par SMS OTP vers l'Algérie, par opérateur (Djezzy / Mobilis / Ooredoo) ?
2. Palier de volume ? Prix à 5 000 / 20 000 / 50 000 SMS par mois ?
3. Délai de livraison moyen et P95 mesurés sur l'Algérie ?
4. Taux de livraison garanti (SLA) ? Pénalités si non respecté ?
5. Sender ID alphanumérique `TTB` possible ? Délai et démarches d'enregistrement ?
6. Accusés de livraison (DLR) via webhook ? Format ?
7. API : doc publique ? Exemple de requête ? Authentification (clé API) ?
8. Paiement : prépayé en DA ? Facture avec NIF/RC ? Moyens acceptés (virement, CCP, Baridimob) ?
9. Compte de test gratuit avec quelques SMS offerts pour valider la délivrabilité ?
10. Que se passe-t-il si un numéro est injoignable / éteint ? File de retry ?
11. Contrat : durée minimale ? Résiliation ?
12. Références clients en Algérie (e-commerce, banques, apps) ?

## 4. Test à faire avant de signer (avec le compte d'essai)

Pour chaque fournisseur qui offre un essai, refaire le protocole de délivrabilité :
- 5 SMS d'affilée sur **chaque opérateur** → mesurer délai + taux de réception
- test en zone hors grande ville si possible
- test heure de pointe (18 h–21 h)
- vérifier l'apparence du SMS reçu (expéditeur lisible, pas en spam)

Retenir le fournisseur avec le **meilleur taux de réception réel**, pas le moins cher.

## 5. Modèle d'email de demande de devis

> Objet : Demande de devis — SMS OTP transactionnel (application mobile, Algérie)
>
> Bonjour,
>
> Nous lançons une application mobile de mise en relation de services à domicile en
> Algérie. Nous avons besoin d'un service d'envoi de **SMS OTP** (codes de vérification
> à l'inscription et à la connexion).
>
> Nos besoins :
> - Volume estimé : ~3 000 SMS/mois au démarrage, ~50 000/mois à 12 mois
> - Couverture : Djezzy, Mobilis, Ooredoo — tout le territoire
> - Livraison < 30 s, priorité transactionnelle
> - Sender ID souhaité : « TTB »
> - Intégration via API HTTP, avec accusés de livraison
> - Paiement en DA, facture avec nos identifiants fiscaux
>
> Pourriez-vous nous communiquer :
> 1. votre grille tarifaire par SMS et par palier de volume,
> 2. vos délais et taux de livraison sur l'Algérie,
> 3. la procédure et le délai d'enregistrement d'un Sender ID,
> 4. la possibilité d'un compte de test,
> 5. votre documentation d'API.
>
> Merci d'avance.
> [Nom] — [téléphone] — [email]

## 6. Côté code : ✅ prêt — il suffit de remplir le `.env`

Le backend `http` est codé (`backend/apps/accounts/sms.py`) : un POST JSON vers l'API
du fournisseur, avec une nouvelle tentative si le fournisseur est injoignable ou en
erreur 5xx. Si le SMS ne part pas, le code est annulé et l'app affiche
« Envoi du SMS impossible pour le moment » (HTTP 503) au lieu de « code envoyé ».

Une fois le fournisseur choisi, recopier **ses** valeurs dans `backend/.env` :

```ini
SMS_BACKEND=http
SMS_API_URL=https://…            # adresse d'envoi donnée par le fournisseur
SMS_API_KEY=…                     # clé API (ne jamais la mettre sur GitHub)
SMS_AUTH_HEADER=Authorization     # ou X-API-Key, selon sa doc
SMS_AUTH_SCHEME=Bearer            # vide si la clé est envoyée seule
SMS_SENDER_ID=TTB                 # expéditeur enregistré chez lui (ou vide)
SMS_PHONE_FORMAT=e164             # +213… | intl = 213… | local = 0…
SMS_FIELD_TO=to                   # noms des champs de SA doc (ex. phone, msisdn, recipient)
SMS_FIELD_TEXT=text               # (ex. message, content, body)
SMS_FIELD_SENDER=sender           # (ex. from, sender_id)
SMS_EXTRA_JSON={}                 # champs fixes en plus, ex. {"type": "otp"}
```

Puis relancer le serveur et tester avec son propre numéro. En production
(`DJANGO_DEBUG=False`), le code n'est plus renvoyé dans la réponse de l'API :
il n'arrive **que** par SMS.

**Si l'API du fournisseur n'est pas du JSON** (formulaire, paramètres dans l'URL, XML),
il faudra adapter `_send_http` : ~15 lignes.

### Option bêta : passerelle SMS sur un téléphone Android

Pour une bêta à faible volume, en attendant le contrat avec un fournisseur :
un téléphone Android dédié, avec une puce Mobilis / Djezzy / Ooredoo et une
application de « passerelle SMS » qui expose une API HTTP. Le backend `http`
lui envoie les codes, et c'est le téléphone qui envoie les SMS depuis sa puce.

- ✅ Coût = forfait SMS de la puce, mise en place en une heure.
- ⚠️ Limites : volume limité par l'opérateur (risque de blocage si trop de SMS),
  téléphone à garder allumé et connecté, expéditeur = un numéro ordinaire.
  Vérifier les conditions de l'opérateur avant usage commercial.
- À remplacer par un vrai fournisseur A2P avant le lancement public.

Reste à faire plus tard : passer l'envoi en tâche de fond quand Celery sera en place,
et brancher les accusés de livraison (DLR) si le fournisseur en propose.
