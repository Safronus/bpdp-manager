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
from .komise import Committee, CommitteeMember, DefenseSlot
from .obor import Obor
from .opponent import Opponent
from .opposing_thesis import OpposingThesis
from .profile import Profile, ProfileRegistry, SmtpConfig
from .rejected_student import RejectedStudent
from .review import CriterionScore, Review
from .review_template import ReviewTemplate, TemplateCriterion
from .student import Student
from .supervisor import Supervisor
from .thesis import Attachment, Deadline, Thesis
from .thesis_proposal import ThesisProposal

__all__ = [
    "AcademicYear",
    "AcademicYearInfo",
    "Attachment",
    "AttachmentKind",
    "Committee",
    "CommitteeMember",
    "CriterionScore",
    "Deadline",
    "DefenseSlot",
    "KeyDate",
    "KeyDateCategory",
    "Obor",
    "Opponent",
    "OpponentKind",
    "OpposingThesis",
    "PlagiarismVerdict",
    "Profile",
    "ProfileRegistry",
    "RejectedStudent",
    "Review",
    "ReviewTemplate",
    "SmtpConfig",
    "Student",
    "StudyForm",
    "Supervisor",
    "TemplateCriterion",
    "Thesis",
    "ThesisProposal",
    "ThesisStatus",
    "ThesisType",
]
