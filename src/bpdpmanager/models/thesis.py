from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from .enums import AttachmentKind, PlagiarismVerdict, ThesisStatus, ThesisType
from .review import Review


class Deadline(BaseModel):
    label: str
    date: date
    done: bool = False


class Attachment(BaseModel):
    label: str
    url_or_path: str  # absolute path, URL, nebo relativní cesta v documents/{thesis_id}/
    kind: AttachmentKind = AttachmentKind.OTHER
    is_file: bool = False  # True = lokální soubor v documents/, False = URL/externí cesta
    # Verzování: každá příloha má version (1, 2, 3, …) a is_current flag.
    # Při nahrání nové přílohy stejného ``kind`` se předchozí current
    # přepne na is_current=False a nově přidaná dostane version = max+1.
    # UI ukáže current prominently a starší verze v rozbalené sekci
    # „Předchozí verze". Stará data dostávají version=1, is_current=True.
    version: int = 1
    is_current: bool = True


class Thesis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: ThesisType
    status: ThesisStatus = ThesisStatus.INTERESTED
    academic_year: str

    student_id: str | None = None
    opponent_id: str | None = None

    title_cs: str = ""
    title_en: str = ""
    annotation: str = ""
    annotation_en: str = ""
    stag_url: str = ""  # odkaz na práci v IS/STAG
    adipidno: str = ""  # STAG ID práce (adipIdno) — pro přesné párování při importu
    # Body zadání a literární zdroje jsou volný text s vlastním číslováním
    # (viz oficiální zadání UTB: "1. ...\n2. ...\n..."). Dřívější verze
    # používaly list[str]; přechod ze starého formátu řeší validator.
    objectives: str = ""
    references: str = ""

    deadlines: list[Deadline] = Field(default_factory=list)
    notes: str = ""
    attachments: list[Attachment] = Field(default_factory=list)
    # v4+ (0.19.0): strukturované posudky (zdroj pravdy pro XLSX/PDF výstupy).
    reviews: list[Review] = Field(default_factory=list)

    # Výsledek kontroly plagiátorství
    plagiarism_similarity_pct: float | None = None  # 0–100
    plagiarism_comment: str = ""
    plagiarism_pdf_filename: str | None = None  # název v thesis_documents_dir(id)
    plagiarism_verdict: PlagiarismVerdict = PlagiarismVerdict.NOT_ASSESSED

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @model_validator(mode="before")
    @classmethod
    def _migrate_list_fields_to_text(cls, data: Any) -> Any:
        """Konvertuje stará pole objectives/references z list[str] na číslovaný text."""
        if isinstance(data, dict):
            for field in ("objectives", "references"):
                v = data.get(field)
                if isinstance(v, list):
                    items = [str(x).strip() for x in v if str(x).strip()]
                    data[field] = "\n".join(
                        f"{i + 1}. {item}" for i, item in enumerate(items)
                    )
        return data

    def touch(self) -> None:
        self.updated_at = datetime.now()

    @property
    def display_title(self) -> str:
        return self.title_cs or "(bez názvu)"

    @property
    def supervisor_review_state(self) -> str:
        """Stav posudku vedoucího: ``"done"`` (vyrobený soubor) /
        ``"draft"`` (jen uložená data) / ``"none"`` (nic)."""
        if any(
            a.is_file and a.kind == AttachmentKind.SUPERVISOR_REVIEW
            for a in self.attachments
        ):
            return "done"
        if any(r.role == "supervisor" for r in self.reviews):
            return "draft"
        return "none"

    def is_ready_for_listing(self) -> tuple[bool, list[str]]:
        """Vypsání tématu vyžaduje název CZ a anotaci."""
        missing = []
        if not self.title_cs.strip():
            missing.append("název CZ")
        if not self.annotation.strip():
            missing.append("anotace")
        return (not missing, missing)

    def is_ready_for_assignment(self) -> tuple[bool, list[str]]:
        """Oficiální zadání vyžaduje navíc EN název, body zadání a literaturu."""
        ok, missing = self.is_ready_for_listing()
        if not self.title_en.strip():
            missing.append("název EN")
        if not self.objectives.strip():
            missing.append("body zadání")
        if not self.references.strip():
            missing.append("literární zdroje")
        return (not missing, missing)
