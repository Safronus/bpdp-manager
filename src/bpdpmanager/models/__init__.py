from .academic_year import AcademicYear
from .enums import StudyForm, ThesisStatus, ThesisType
from .opponent import Opponent
from .student import Student
from .thesis import Attachment, Deadline, Thesis

__all__ = [
    "AcademicYear",
    "Attachment",
    "Deadline",
    "Opponent",
    "Student",
    "StudyForm",
    "Thesis",
    "ThesisStatus",
    "ThesisType",
]
