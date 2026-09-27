"""Pravidla pro stav práce při importu ze STAG (bez Qt).

Import páruje i práci založenou ručně (zájemce / vypsané téma) — podle STAG ID,
jinak podle studenta, roku a typu. Dřív stav existující práce nikdy neměnil, takže
schválené téma („v řešení" ve STAG) zůstalo v Budoucích. Teď:

- existující práce v budoucím stavu + STAG dokládá „v řešení" nebo pozdější stav
  → náhled předvybere stav ze STAG,
- jinak (V řešení, ukončené, nebo STAG nic nedokládá) → předvybere stávající
  stav, tedy beze změny.

Stav, který uživatel v náhledu ručně zvolí, se uplatní vždy.
"""

from __future__ import annotations

from ..models.enums import STATUSES_FUTURE, ThesisStatus


def preselected_status_for_existing(
    current: ThesisStatus, stag_status: ThesisStatus | None
) -> ThesisStatus:
    """Výchozí stav v náhledu importu pro už evidovanou vedenou práci.

    ``stag_status`` = stav doložený daty STAG (kód ``stavPrace`` nebo data
    zadání/odevzdání/obhajoby); ``None`` = STAG nic nedokládá.
    """
    if (
        current in STATUSES_FUTURE
        and stag_status is not None
        and stag_status not in STATUSES_FUTURE
    ):
        return stag_status
    return current
