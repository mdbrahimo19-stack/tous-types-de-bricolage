"""Création + envoi des notifications.

Backend push pluggable (comme les SMS) :
- `console` : journalise seulement (dev)
- `fcm` : Firebase Cloud Messaging (gratuit), voir push_fcm.py ; le téléphone sonne même app fermée.
"""
import logging

from django.conf import settings

from .models import Notification

logger = logging.getLogger("ttb.push")


def _send_push(user, title, body, data):
    backend = getattr(settings, "PUSH_BACKEND", "console")
    tokens = list(user.devices.values_list("token", flat=True))
    if not tokens:
        return
    if backend == "console":
        logger.info("PUSH → %s (%d appareil·s) : %s", user, len(tokens), title)
        return
    if backend == "fcm":
        from . import push_fcm

        dead = push_fcm.send(tokens, title, body, data)
        if dead:  # application désinstallée : on oublie ces appareils
            user.devices.filter(token__in=dead).delete()
        return
    raise NotImplementedError(f"PUSH_BACKEND inconnu : {backend!r}")


def notify(user, type_, title, body="", *, data=None, push=True):
    """Crée une Notification en base et, si `push`, tente un envoi push."""
    notif = Notification.objects.create(
        recipient=user, type=type_, title=title, body=body, data=data or {}
    )
    if push:
        try:
            _send_push(user, title, body, notif.data)
        except Exception:  # ne jamais casser le flux métier pour une notif
            logger.exception("Échec envoi push à %s", user)
    return notif


def notify_many(users, type_, title, body="", *, data=None, push=True):
    for user in users:
        notify(user, type_, title, body, data=data, push=push)
