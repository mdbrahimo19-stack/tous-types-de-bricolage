"""Accès centralisé à l'API Claude (Anthropic).

Toutes les fonctions IA passent par `ask()` : un seul endroit pour le modèle,
les délais, la gestion des refus et des erreurs réseau.
"""
import json
import logging
from functools import lru_cache

import anthropic
from django.conf import settings

log = logging.getLogger(__name__)

# Si Claude décline une requête (classifieurs de sécurité), l'API la rejoue
# automatiquement sur le modèle de repli recommandé par Anthropic.
_FALLBACK_HEADERS = {"anthropic-beta": "server-side-fallback-2026-07-01"}
_FALLBACK_BODY = {"fallbacks": "default"}


class AIUnavailable(Exception):
    """IA désactivée, injoignable ou réponse inutilisable : l'appelant doit se replier."""


@lru_cache(maxsize=1)
def _client():
    return anthropic.Anthropic(
        api_key=settings.ANTHROPIC_API_KEY or None,
        timeout=settings.AI_TIMEOUT_SECONDS,
        max_retries=2,
    )


def ask(system, messages, *, schema=None, effort="low", max_tokens=8000):
    """Appelle Claude et renvoie le texte de la réponse, ou un dict si `schema` est fourni.

    `schema` : JSON Schema (additionalProperties=false) imposé à la réponse.
    Lève AIUnavailable en cas d'IA désactivée, d'erreur API ou de refus.
    """
    if not settings.AI_ENABLED:
        raise AIUnavailable("IA désactivée (ANTHROPIC_API_KEY absente).")

    output_config = {"effort": effort}
    if schema is not None:
        output_config["format"] = {"type": "json_schema", "schema": schema}

    try:
        response = _client().messages.create(
            model=settings.AI_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            output_config=output_config,
            cache_control={"type": "ephemeral"},
            extra_headers=_FALLBACK_HEADERS,
            extra_body=_FALLBACK_BODY,
        )
    except anthropic.RateLimitError as e:
        log.warning("Claude: limite de débit atteinte (%s)", e)
        raise AIUnavailable("Service IA saturé, réessayez dans un instant.") from e
    except anthropic.APIStatusError as e:
        log.error("Claude: erreur API %s (%s)", e.status_code, e.message)
        raise AIUnavailable("Service IA indisponible.") from e
    except anthropic.APIConnectionError as e:
        log.error("Claude: erreur réseau (%s)", e)
        raise AIUnavailable("Service IA injoignable.") from e

    if response.stop_reason == "refusal":
        log.info("Claude: refus (%s)", getattr(response.stop_details, "category", None))
        raise AIUnavailable("Requête refusée par le service IA.")
    if response.stop_reason == "max_tokens":
        raise AIUnavailable("Réponse IA tronquée.")

    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if schema is None:
        return text
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        log.error("Claude: JSON invalide malgré le schéma : %r", text[:200])
        raise AIUnavailable("Réponse IA illisible.") from e
