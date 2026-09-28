"""Reglas puras para el recurso de almas de la Segadora."""

SOUL_BASE_LIMIT = 100
SOUL_RESERVOIR_LIMIT = 125


def soul_limit(expanded=False):
    return SOUL_RESERVOIR_LIMIT if expanded else SOUL_BASE_LIMIT


def gain_souls(current, amount, expanded=False):
    before = max(0, int(current))
    after = min(soul_limit(expanded), before + max(0, int(amount)))
    return after, after - before
