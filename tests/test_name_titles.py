"""Test parseru jména s tituly (STAG formát „Příjmení Jméno, tituly")."""

from __future__ import annotations

import pytest

from bpdpmanager.models.naming import compose_titled_name, parse_titled_name


@pytest.mark.parametrize(
    "raw,before,name,after",
    [
        ("Novák Jan, prof. Ing. Ph.D.", "prof. Ing.", "Jan Novák", "Ph.D."),
        ("Svoboda Petr, prof. Mgr. Ph.D., DBA", "prof. Mgr.", "Petr Svoboda", "Ph.D., DBA"),
        ("Dvořák Karel, Ing.", "Ing.", "Karel Dvořák", ""),
        ("Černý Pavel, Ing. PhD.", "Ing.", "Pavel Černý", "PhD."),
        ("Veselý Tomáš, doc. Ing. Ph.D.", "doc. Ing.", "Tomáš Veselý", "Ph.D."),
        # Bez čárky = čisté jméno, neparsuje se.
        ("Michal Bílý", "", "Michal Bílý", ""),
        ("", "", "", ""),
        # Neznámý token „arch." se připojí ke skupině před jménem.
        ("Procházka Jan, Ing. arch.", "Ing. arch.", "Jan Procházka", ""),
    ],
)
def test_parse_titled_name(raw, before, name, after) -> None:
    assert parse_titled_name(raw) == (before, name, after)


def test_parse_then_compose_roundtrip() -> None:
    """Po rozparsování dá compose správný český formát s čárkou."""
    b, n, a = parse_titled_name("Novák Jan, prof. Ing. Ph.D.")
    assert compose_titled_name(b, n, a) == "prof. Ing. Jan Novák, Ph.D."


def _service(tmp_path):
    from bpdpmanager.services import ThesisService
    from bpdpmanager.storage import JsonRepository

    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def test_cleanup_opponent_titles(tmp_path) -> None:
    from bpdpmanager.models import Opponent

    svc = _service(tmp_path)
    messy = Opponent(name="Novák Jan, prof. Ing. Ph.D.")
    clean = Opponent(name="Petr Svoboda")  # bez čárky → nechá být
    svc.upsert_opponent(messy)
    svc.upsert_opponent(clean)

    preview = svc.cleanup_opponent_titles(dry_run=True)
    assert len(preview) == 1                      # jen ten messy
    assert svc.get_opponent(messy.id).name == "Novák Jan, prof. Ing. Ph.D."  # beze změny

    svc.cleanup_opponent_titles()
    fixed = svc.get_opponent(messy.id)
    assert fixed.name == "Jan Novák"
    assert fixed.title_before == "prof. Ing." and fixed.title_after == "Ph.D."
    assert svc.get_opponent(clean.id).name == "Petr Svoboda"  # nedotčeno


def test_cleanup_supervisor_titles_also_fixes_opposing_copy(tmp_path) -> None:
    from bpdpmanager.models import OpposingThesis, Supervisor
    from bpdpmanager.models.enums import ThesisType

    svc = _service(tmp_path)
    sup = Supervisor(name="Svoboda Petr, prof. Mgr. Ph.D., DBA")
    svc.upsert_supervisor(sup)
    op = OpposingThesis(type=ThesisType.BP, academic_year="2024/2025",
                        student_last_name="X",
                        supervisor_name="Dvořák Karel, Ing.")
    svc.upsert_opposing_thesis(op)

    changes = svc.cleanup_supervisor_titles()
    assert len(changes) == 2  # vedoucí v registru + denormalizovaná kopie u oponentury
    fixed = svc.get_supervisor(sup.id)
    assert fixed.name == "Petr Svoboda" and fixed.title_before == "prof. Mgr."
    assert fixed.title_after == "Ph.D., DBA"
    # Denormalizovaný string u oponentury je přeskládaný do čitelného formátu.
    assert svc.get_opposing_thesis(op.id).supervisor_name == "Ing. Karel Dvořák"
