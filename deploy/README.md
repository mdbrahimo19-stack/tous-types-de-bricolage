# Mettre le serveur en ligne (VPS)

Ce dossier contient tout ce qu'il faut pour faire tourner le backend en production sur un
serveur loué (VPS) : base **PostgreSQL**, **backend Django** (gunicorn), **Caddy** (HTTPS
automatique et gratuit) et une **tâche horaire** qui fait expirer les vieilles demandes.

Durée : environ 1 h la première fois.

---

## 1. Louer un VPS

| Caractéristique | Minimum conseillé |
|---|---|
| Système | **Ubuntu 24.04** |
| Mémoire | **2 Go** de RAM |
| Processeur | 1 à 2 vCPU |
| Disque | 40 Go |

N'importe quel hébergeur qui propose un VPS Linux convient (ordre de grandeur : 5 à 10 €/mois).
Notez **l'adresse IP** du serveur et le **mot de passe root** (ou ajoutez votre clé SSH).

## 2. Se connecter au serveur

Depuis PowerShell sur votre PC :

```bash
ssh root@51.15.20.30          # remplacez par l'IP de votre VPS
```

## 3. Installer Docker et le pare-feu

```bash
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable
```

## 4. Récupérer le code

```bash
cd /root
git clone https://github.com/mdbrahimo19-stack/tous-types-de-bricolage.git
cd tous-types-de-bricolage/deploy
```

Si le dépôt est privé, GitHub demande un identifiant et un **jeton** (pas le mot de passe) :
GitHub → Settings → Developer settings → Personal access tokens → *Fine-grained*, accès
**lecture seule** au dépôt.

## 5. Remplir les réglages

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(50))"   # -> DJANGO_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # -> POSTGRES_PASSWORD
nano .env
```

**Sans nom de domaine**, utilisez l'adresse gratuite `IP-avec-des-tirets.sslip.io`.
Exemple pour l'IP `51.15.20.30` :

```ini
DOMAIN=51-15-20-30.sslip.io
DJANGO_ALLOWED_HOSTS=51-15-20-30.sslip.io
CSRF_TRUSTED_ORIGINS=https://51-15-20-30.sslip.io
```

(`Ctrl+O` puis `Entrée` pour enregistrer, `Ctrl+X` pour quitter nano.)

## 6. Démarrer

```bash
docker compose up -d --build
docker compose ps            # db, web, scheduler, caddy doivent être « Up » / « healthy »
```

Premier remplissage de la base (catégories, wilayas, communes) et compte administrateur :

```bash
docker compose exec web python manage.py seed_base
docker compose exec web python manage.py createsuperuser   # numéro +213… et mot de passe
```

## 7. Vérifier

Dans un navigateur :

- `https://51-15-20-30.sslip.io/api/health/` → `{"status": "ok"}`
- `https://51-15-20-30.sslip.io/admin/` → tableau de bord administrateur

Le certificat HTTPS est obtenu automatiquement par Caddy en quelques secondes.

## 8. Brancher l'application

- **Tout de suite** : dans l'app, bouton **Serveur** → `https://51-15-20-30.sslip.io` → **Tester**.
- **Pour tous les utilisateurs** : sur GitHub → *Settings* → *Secrets and variables* →
  *Actions* → onglet **Variables** → *New repository variable* :
  `API_URL` = `https://51-15-20-30.sslip.io`.
  Les APK compilés ensuite utiliseront directement ce serveur.

## 9. Sauvegardes automatiques (chaque nuit à 3 h 30)

```bash
chmod +x /root/tous-types-de-bricolage/deploy/sauvegarde.sh
mkdir -p /root/sauvegardes-ttb
crontab -e
# ajouter la ligne :
30 3 * * * /root/tous-types-de-bricolage/deploy/sauvegarde.sh >> /root/sauvegardes-ttb/log.txt 2>&1
```

Les 14 dernières sauvegardes (base + photos) sont gardées dans `/root/sauvegardes-ttb`.
Pensez à en copier une de temps en temps sur votre PC :
`scp root@51.15.20.30:/root/sauvegardes-ttb/base_*.dump .`

---

## Au quotidien

| Besoin | Commande (dans `deploy/`) |
|---|---|
| Voir les journaux (et les codes SMS en mode `console`) | `docker compose logs -f web` |
| Mettre à jour après un changement sur GitHub | `git pull && docker compose up -d --build` |
| Redémarrer | `docker compose restart` |
| État des services | `docker compose ps` |

## Quand vous aurez un nom de domaine

1. Chez le vendeur du domaine, créez un enregistrement **A** : `api.mondomaine.com` → IP du VPS.
2. Dans `.env` : remplacez l'adresse sslip.io par `api.mondomaine.com` (dans `DOMAIN`,
   `DJANGO_ALLOWED_HOSTS` et `CSRF_TRUSTED_ORIGINS`).
3. `docker compose up -d` — Caddy obtient le nouveau certificat tout seul.
4. Mettez à jour la variable GitHub `API_URL`.

## Envoi réel des SMS

Tant que `SMS_BACKEND=console`, aucun SMS n'est envoyé : les codes n'apparaissent que dans
`docker compose logs web`. Pour brancher un fournisseur, voir `docs/sms-aggregator-brief.md`,
remplir les lignes `SMS_*` du `.env`, puis `docker compose up -d`.

## Sécurité (conseillé)

- Connexion SSH par **clé** plutôt que par mot de passe, puis désactiver la connexion root
  par mot de passe (`PasswordAuthentication no` dans `/etc/ssh/sshd_config`).
- Ne jamais mettre le fichier `.env` sur GitHub (il est ignoré par `.gitignore`).
