from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field

from .enums import OpponentKind


class Opponent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    kind: OpponentKind = OpponentKind.INTERNAL
    name: str
    email: str | None = None
    affiliation: str | None = None
    phone: str | None = None  # zejména pro externí
    address: str | None = None  # pouze pro externí
    note: str | None = None

    @property
    def is_external(self) -> bool:
        return self.kind == OpponentKind.EXTERNAL

    @property
    def display_label(self) -> str:
        suffix = f" ({self.affiliation})" if self.affiliation else ""
        return f"{self.name}{suffix}"
