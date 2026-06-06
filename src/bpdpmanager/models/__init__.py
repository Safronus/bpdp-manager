from .academic_year import AcademicYear
from .enums import (
    AttachmentKind,
    OpponentKind,
    PlagiarismVerdict,
    StudyForm,
    ThesisStatus,
    ThesisType,
)
from .harmonogram import AcademicYearInfo, KeyDate, KeyDateCategory
from .obor import Obor
from .opponent import Opponent
from .opposing_thesis import OpposingThesis
from .profile import Profile, ProfileRegistry, SmtpConfig
from .review import CriterionScore, Review
from .review_template import ReviewTemplate, TemplateCriterion
from .rejected_student import RejectedStudent
from .student import Student
from .supervisor import Supervisor
from .thesis import Attachment, Deadline, Thesis
from .thesis_proposal import ThesisProposal

__all__ = [
    "AcademicYear",
    "AcademicYearInfo",
    "Attachment",
    "AttachmentKind",
    "Deadline",
    "KeyDate",
    "KeyDateCategory",
    "Obor",
    "Opponent",
    "OpponentKind",
    "OpposingThesis",
    "PlagiarismVerdict",
    "Profile",
    "ProfileRegistry",
    "SmtpConfig",
    "CriterionScore",
    "Review",
    "ReviewTemplate",
    "TemplateCriterion",
    "RejectedStudent",
    "Student",
    "StudyForm",
    "Supervisor",
    "Thesis",
    "ThesisProposal",
    "ThesisStatus",
    "ThesisType",
]
