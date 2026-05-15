from __future__ import annotations

from pydantic import BaseModel


class Obor(BaseModel):
    """Studijní obor s volitelným kontaktem na sekretářku oboru."""

    name: str
    secretary_name: str | None = None
    secretary_email: str | None = None
    secretary_phone: str | None = None
    note: str | None = None

    @property
    def has_secretary(self) -> bool:
        return bool(
            (self.secretary_name or "").strip()
            or (self.secretary_email or "").strip()
            or (self.secretary_phone or "").strip()
        )
