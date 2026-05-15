from .academic_year import AcademicYear
from .enums import AttachmentKind, OpponentKind, StudyForm, ThesisStatus, ThesisType
from .harmonogram import AcademicYearInfo, KeyDate, KeyDateCategory
from .opponent import Opponent
from .student import Student
from .thesis import Attachment, Deadline, Thesis

__all__ = [
    "AcademicYear",
    "AcademicYearInfo",
    "Attachment",
    "AttachmentKind",
    "Deadline",
    "KeyDate",
    "KeyDateCategory",
    "Opponent",
    "OpponentKind",
    "Student",
    "StudyForm",
    "Thesis",
    "ThesisStatus",
    "ThesisType",
]
