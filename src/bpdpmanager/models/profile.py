"""Profily — pojmenované datové sady. Každý profil má vlastní data_dir."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class SmtpConfig(BaseModel):
    """Nastavení odchozího SMTP serveru pro odesílání posudků.

    Heslo se zde **nikdy neukládá** — uživatel je zadává při každém odeslání.
    Výchozí hodnoty odpovídají UTB Office365 (viz nápověda / CVT UTB).
    """

    model_config = ConfigDict(extra="ignore")

    host: str = "outlook.office365.com"
    port: int = 587
    security: str = "starttls"  # "starttls" | "ssl" | "none"
    username: str = ""           # prázdné = použij e-mail uživatele profilu


class Profile(BaseModel):
    """Jeden datový profil (data_dir + jméno + meta)."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    data_dir: str  # absolutní cesta ke složce s db.json, documents/, harmonograms/
    user_name: str = ""  # jméno uživatele profilu (pro STAG import auto-detect role)
    user_email: str = ""  # e-mail uživatele (odesílatel posudků sekretářkám)
    # Tituly před/za jménem (volný string) — skládají se do jména autora posudku.
    user_title_before: str = ""  # např. "doc. Ing."
    user_title_after: str = ""   # např. "Ph.D." nebo ", Ph.D."
    review_place: str = "Zlín"  # místo pro podpisový blok posudku (Místo, datum)
    smtp: SmtpConfig = Field(default_factory=SmtpConfig)  # odchozí pošta (bez hesla)
    created_at: datetime = Field(default_factory=datetime.now)
    last_opened_at: datetime | None = None


class ProfileRegistry(BaseModel):
    """Rejstřík profilů — uložen v user config dir mimo data."""

    model_config = ConfigDict(extra="ignore")

    version: int = 1
    last_opened: str | None = None
    profiles: list[Profile] = Field(default_factory=list)
    # UI předvolby napříč profily (poslední cesty pro file dialogy atp.)
    last_stag_import_dir: str = ""
    last_template_import_dir: str = ""
    # Tutorial „Začínáme" se ukazuje jen jednou (po prvním nastavení).
    tutorial_shown: bool = False
