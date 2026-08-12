import re
import unicodedata
from enum import StrEnum


class PhoneConfirmationDecision(StrEnum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    AMBIGUOUS = "ambiguous"


def normalize_reply(value: str) -> str:
    """Normalize a short WhatsApp reply without changing its meaning."""
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    )
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", without_accents.upper())).strip()


def classify_reply(value: str) -> PhoneConfirmationDecision:
    """Classify explicit affirmative or cancellation replies conservatively."""
    reply = normalize_reply(value)
    if not reply:
        return PhoneConfirmationDecision.AMBIGUOUS

    cancellation_phrases = (
        "CANCELAR",
        "CANCELE",
        "NAO QUERO",
        "NAO ACEITO",
        "DESISTO",
        "PARAR",
        "RECUSO",
    )
    if reply in cancellation_phrases or any(
        reply.startswith(f"{phrase} ") for phrase in cancellation_phrases
    ):
        return PhoneConfirmationDecision.CANCELLED

    confirmation_phrases = (
        "OK",
        "SIM",
        "QUERO",
        "CLARO",
        "PODE SER",
        "CONFIRMO",
        "CONFIRMAR",
        "ACEITO",
        "TUDO BEM",
    )
    if reply in confirmation_phrases or any(
        reply.startswith(f"{phrase} ") for phrase in confirmation_phrases
    ):
        return PhoneConfirmationDecision.CONFIRMED

    return PhoneConfirmationDecision.AMBIGUOUS
