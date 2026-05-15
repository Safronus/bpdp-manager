from __future__ import annotations

import re

from pydantic import BaseModel, field_validator

_PATTERN = re.compile(r"^\d{4}/\d{4}$")


class AcademicYear(BaseModel):
    """Akademický rok ve tvaru ``YYYY/YYYY`` (např. ``2024/2025``)."""

    label: str

    @field_validator("label")
    @classmethod
    def _validate(cls, v: str) -> str:
        v = v.strip()
        if not _PATTERN.match(v):
            raise ValueError(f"Akademický rok musí být ve tvaru YYYY/YYYY, dostal: {v!r}")
        start, end = (int(x) for x in v.split("/"))
        if end != start + 1:
            raise ValueError(f"Druhý rok musí následovat hned po prvním: {v!r}")
        return v

    @property
    def start_year(self) -> int:
        return int(self.label.split("/")[0])

    @property
    def end_year(self) -> int:
        return int(self.label.split("/")[1])

    @classmethod
    def from_start(cls, start: int) -> AcademicYear:
        return cls(label=f"{start}/{start + 1}")

    def __lt__(self, other: AcademicYear) -> bool:
        return self.start_year < other.start_year

    def __hash__(self) -> int:
        return hash(self.label)
