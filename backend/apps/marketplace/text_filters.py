"""Filtrage anti-contournement de la messagerie (RG-05).

Masque les numéros de téléphone et les liens tant que la demande n'est pas attribuée,
pour empêcher les échanges hors plateforme.
"""
import re

# Chiffres arabes-indiens -> ASCII (les utilisateurs tapent souvent en arabe)
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

_PHONE_RE = re.compile(r"(?<!\w)(\+?\d[\d\s.\-/]{6,}\d)(?!\w)")
_URL_RE = re.compile(
    r"\b((?:https?://|www\.)\S+|\S+\.(?:com|net|org|dz|fr|io|me|app)\b\S*)", re.IGNORECASE
)
# "zero six ..." / "zéro six" / séquences de mots-chiffres rapprochés
_SPELLED_RE = re.compile(
    r"\b(?:(?:z[ée]ro|un|deux|trois|quatre|cinq|six|sept|huit|neuf|dix)[\s\-]*){5,}",
    re.IGNORECASE,
)

PHONE_MASK = "[numéro masqué]"
URL_MASK = "[lien masqué]"


def mask_contacts(text: str) -> tuple[str, bool]:
    """Renvoie (texte_filtré, a_ete_modifie)."""
    if not text:
        return text, False
    normalized = text.translate(_ARABIC_DIGITS)
    out = _URL_RE.sub(URL_MASK, normalized)
    out = _PHONE_RE.sub(PHONE_MASK, out)
    out = _SPELLED_RE.sub(PHONE_MASK, out)
    return out, (out != normalized)
