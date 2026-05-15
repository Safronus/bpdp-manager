from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field


class Opponent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    email: str | None = None
    affiliation: str | None = None
    note: str | None = None
