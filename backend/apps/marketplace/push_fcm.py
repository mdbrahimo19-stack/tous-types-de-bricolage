"""Envoi des notifications push par Firebase Cloud Messaging (API HTTP v1).

Le fichier du compte de service Firebase (JSON) reste hors du code : son chemin est dans
FIREBASE_CREDENTIALS_FILE (fichier .env). Il n'est jamais copié dans le dépôt.
"""
import logging
import threading

from django.conf import settings

logger = logging.getLogger("ttb.push")

SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
# même identifiant que le canal créé par l'app (lib/push.dart) : sonnerie + priorité haute
ANDROID_CHANNEL = "bricool_alerts"

_lock = threading.Lock()
_session = None
_project_id = None


def _client():
    """Session HTTP authentifiée auprès de Google (le jeton d'accès se renouvelle tout seul)."""
    global _session, _project_id
    with _lock:
        if _session is None:
            from google.auth.transport.requests import AuthorizedSession
            from google.oauth2 import service_account

            path = settings.FIREBASE_CREDENTIALS_FILE
            if not path:
                raise RuntimeError("FIREBASE_CREDENTIALS_FILE n'est pas défini dans le fichier .env.")
            creds = service_account.Credentials.from_service_account_file(path, scopes=[SCOPE])
            _project_id = creds.project_id
            _session = AuthorizedSession(creds)
        return _session, _project_id


def build_message(token, title, body, data):
    return {
        "message": {
            "token": token,
            "notification": {"title": title, "body": body},
            # FCM n'accepte que des textes dans « data »
            "data": {str(k): str(v) for k, v in (data or {}).items()},
            "android": {
                "priority": "high",
                "notification": {"channel_id": ANDROID_CHANNEL, "sound": "default"},
            },
            "apns": {"payload": {"aps": {"sound": "default"}}},
        }
    }


def send(tokens, title, body, data=None, *, timeout=10):
    """Envoie la notification à chaque appareil. Renvoie la liste des jetons à supprimer
    (application désinstallée ou jeton expiré)."""
    session, project_id = _client()
    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    dead = []
    for token in tokens:
        resp = session.post(url, json=build_message(token, title, body, data), timeout=timeout)
        if resp.status_code == 200:
            continue
        try:
            err = resp.json().get("error", {})
        except ValueError:
            err = {}
        codes = {d.get("errorCode") for d in err.get("details", []) if isinstance(d, dict)}
        if resp.status_code == 404 or "UNREGISTERED" in codes or "INVALID_ARGUMENT" in codes:
            dead.append(token)
        else:
            # le jeton n'est jamais écrit en entier dans le journal
            logger.warning("FCM HTTP %s pour le jeton %s… : %s", resp.status_code, token[:8], err.get("status"))
    return dead
