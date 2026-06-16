"""Profil: rozdělené jméno (křestní + příjmení) pro přesné hledání ve STAG."""

from __future__ import annotations

from bpdpmanager.models.naming import split_first_surname


def test_split_first_surname() -> None:
    """Fallback/předvyplnění: příjmení = poslední token, zbytek = křestní."""
    assert split_first_surname("Petr Novák") == ("Petr", "Novák")
    assert split_first_surname("Jan Petr Novák") == ("Jan Petr", "Novák")
    # dvojí příjmení se odhadem rozdělí špatně (proto si to uživatel upraví)
    assert split_first_surname("Zuzana Komínková Oplatková") == (
        "Zuzana Komínková", "Oplatková")
    assert split_first_surname("Novák") == ("", "Novák")
    assert split_first_surname("") == ("", "")


def test_set_user_name_parts_composes_full_name(tmp_path, monkeypatch) -> None:
    """set_user_name_parts uloží křestní+příjmení a složí z nich celé jméno."""
    import bpdpmanager.services.profile_manager as pmmod

    monkeypatch.setattr(
        pmmod, "profiles_registry_path", lambda: tmp_path / "profiles.json")
    pm = pmmod.ProfileManager()
    prof = pm.create(name="Test", data_dir=tmp_path / "data")

    # Dvojí příjmení — uživatel ho zadá explicitně (odhad by ho rozdělil špatně).
    pm.set_user_name_parts(prof.id, "Zuzana", "Komínková Oplatková")
    p = pm.get(prof.id)
    assert p.user_first_name == "Zuzana"
    assert p.user_surname == "Komínková Oplatková"
    assert p.user_name == "Zuzana Komínková Oplatková"   # celé jméno složené

    # Dvojí křestní jméno.
    pm.set_user_name_parts(prof.id, "Jan Petr", "Novák")
    p = pm.get(prof.id)
    assert p.user_first_name == "Jan Petr"
    assert p.user_surname == "Novák"
    assert p.user_name == "Jan Petr Novák"
