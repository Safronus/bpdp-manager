from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from ..config import SCHEMA_VERSION
from ..models import Opponent, Student, Thesis


class Database(BaseModel):
    """Kontejner pro celé úložiště — serializovatelný do JSON."""

    version: int = SCHEMA_VERSION
    obory: list[str] = Field(default_factory=list)
    students: list[Student] = Field(default_factory=list)
    opponents: list[Opponent] = Field(default_factory=list)
    theses: list[Thesis] = Field(default_factory=list)


class Repository(ABC):
    """Abstraktní rozhraní pro perzistenci."""

    @abstractmethod
    def load(self) -> Database: ...

    @abstractmethod
    def save(self, db: Database) -> None: ...
