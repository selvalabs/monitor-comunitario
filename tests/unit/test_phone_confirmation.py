import pytest

from monitor_comunitario.services.phone_confirmation import (
    PhoneConfirmationDecision,
    classify_reply,
)


@pytest.mark.parametrize("reply", ["OK", "SIM", "quero", "CLARO", "pode ser", "CONFIRMO"])
def test_affirmative_replies_are_confirmed(reply: str) -> None:
    assert classify_reply(reply) is PhoneConfirmationDecision.CONFIRMED


@pytest.mark.parametrize("reply", ["CANCELAR", "não quero", "DESISTO", "PARAR"])
def test_negative_replies_are_cancelled(reply: str) -> None:
    assert classify_reply(reply) is PhoneConfirmationDecision.CANCELLED


def test_ambiguous_reply_does_not_change_registration() -> None:
    assert classify_reply("talvez") is PhoneConfirmationDecision.AMBIGUOUS
