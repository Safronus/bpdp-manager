from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field, model_validator

from ..config import SCHEMA_VERSION
from ..models import AcademicYearInfo, Obor, Opponent, Student, Thesis


class Database(BaseModel):
    """Kontejner pro celé úložiště — serializovatelný do JSON."""

    version: int = SCHEMA_VERSION
    obory: list[Obor] = Field(default_factory=list)
    students: list[Student] = Field(default_factory=list)
    opponents: list[Opponent] = Field(default_factory=list)
    theses: list[Thesis] = Field(default_factory=list)
    academic_years: list[AcademicYearInfo] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _migrate_obory_strings(cls, data: Any) -> Any:
        """Stará verze ukládala obory jako list[str]; konvertujeme na list[Obor]."""
        if isinstance(data, dict):
            obory = data.get("obory")
            if isinstance(obory, list):
                converted: list[Any] = []
                for item in obory:
                    if isinstance(item, str):
                        converted.append({"name": item})
                    else:
                        converted.append(item)
                data["obory"] = converted
        return data


class Repository(ABC):
    """Abstraktní rozhraní pro perzistenci."""

    @abstractmethod
    def load(self) -> Database: ...

    @abstractmethod
    def save(self, db: Database) -> None: ...
