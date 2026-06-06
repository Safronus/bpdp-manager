from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field, model_validator

from ..config import SCHEMA_VERSION
from ..models import (
    AcademicYearInfo,
    Obor,
    Opponent,
    OpposingThesis,
    RejectedStudent,
    ReviewTemplate,
    Student,
    Supervisor,
    Thesis,
    ThesisProposal,
)


class Database(BaseModel):
    """Kontejner pro celé úložiště — serializovatelný do JSON."""

    version: int = SCHEMA_VERSION
    obory: list[Obor] = Field(default_factory=list)
    students: list[Student] = Field(default_factory=list)
    opponents: list[Opponent] = Field(default_factory=list)
    supervisors: list[Supervisor] = Field(default_factory=list)
    theses: list[Thesis] = Field(default_factory=list)
    opposing_theses: list[OpposingThesis] = Field(default_factory=list)
    academic_years: list[AcademicYearInfo] = Field(default_factory=list)
    # v3+ (0.17.0): knihovna XLSX šablon posudků v rámci profilu.
    review_templates: list[ReviewTemplate] = Field(default_factory=list)
    # v10: evidence odmítnutých zájemců o vedení (kapacita vedení).
    rejected_students: list[RejectedStudent] = Field(default_factory=list)
    # v12 (0.58.0): návrhy témat prací (nekompletní nápady bez studenta/stavu).
    proposals: list[ThesisProposal] = Field(default_factory=list)

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

    @model_validator(mode="before")
    @classmethod
    def _migrate_assigned_status(cls, data: Any) -> Any:
        """v0.15.0: ThesisStatus.ASSIGNED bylo sloučeno do IN_PROGRESS.

        Stará data se statusem ``"assigned"`` musí být před validací přepsána
        na ``"in_progress"``, jinak by pydantic neuměl deserializovat enum.
        """
        if not isinstance(data, dict):
            return data
        for thesis in data.get("theses", []) or []:
            if isinstance(thesis, dict) and thesis.get("status") == "assigned":
                thesis["status"] = "in_progress"
        return data

    @model_validator(mode="before")
    @classmethod
    def _migrate_attachment_versioning(cls, data: Any) -> Any:
        """v0.15.0: Attachment má nová pole version + is_current.

        Stará data nemají tyto klíče → pydantic je doplní z defaultů
        (version=1, is_current=True). Ale: pokud existuje víc příloh
        téhož ``kind`` u jedné práce, je správnější označit jako
        is_current=True jen tu *poslední* (nahranou jako poslední).
        Heuristika: poslední pozice v listu.
        """
        if not isinstance(data, dict):
            return data

        def _backfill_versioning(attachments: list[Any]) -> None:
            if not isinstance(attachments, list):
                return
            # Group by kind, keep only last as current, version by order.
            kind_indices: dict[str, list[int]] = {}
            for i, att in enumerate(attachments):
                if not isinstance(att, dict):
                    continue
                # už má v0.15.0 fieldy → respektuj
                if "version" in att and "is_current" in att:
                    continue
                kind = att.get("kind") or "other"
                kind_indices.setdefault(kind, []).append(i)
            for _kind, idxs in kind_indices.items():
                for n, idx in enumerate(idxs, start=1):
                    attachments[idx].setdefault("version", n)
                    attachments[idx].setdefault("is_current", idx == idxs[-1])

        for thesis in data.get("theses", []) or []:
            if isinstance(thesis, dict):
                _backfill_versioning(thesis.get("attachments", []))
        for op in data.get("opposing_theses", []) or []:
            if isinstance(op, dict):
                _backfill_versioning(op.get("attachments", []))
        return data


class Repository(ABC):
    """Abstraktní rozhraní pro perzistenci."""

    @abstractmethod
    def load(self) -> Database: ...

    @abstractmethod
    def save(self, db: Database) -> None: ...
