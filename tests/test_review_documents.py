"""Testy archivace posudků a úklidu chybějících dokumentů."""

from __future__ import annotations

from pathlib import Path

import pytest

from bpdpmanager.config import thesis_documents_dir
from bpdpmanager.models import Attachment, Thesis
from bpdpmanager.models.enums import AttachmentKind, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _write(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_archive_moves_old_xlsx_and_deletes_old_pdf(service: ThesisService) -> None:
    thesis = Thesis(type=ThesisType.BP, academic_year="2025/2026", title_cs="Vzorová práce")
    service.upsert_thesis(thesis)

    posudky = thesis_documents_dir(thesis.id) / "posudky"
    xlsx_name = "Vzor_posudek-vedouciho_2026-06-01.xlsx"
    pdf_name = "Vzor_posudek-vedouciho_2026-06-01.pdf"
    _write(posudky / xlsx_name)
    _write(posudky / pdf_name)

    thesis.attachments = [
        Attachment(
            label=xlsx_name, url_or_path=f"posudky/{xlsx_name}",
            kind=AttachmentKind.SUPERVISOR_REVIEW, is_file=True,
            version=1, is_current=True,
        ),
        Attachment(
            label=pdf_name, url_or_path=f"posudky/{pdf_name}",
            kind=AttachmentKind.SUPERVISOR_REVIEW, is_file=True,
            version=1, is_current=False,
        ),
    ]

    service._archive_previous_review_files(
        thesis.id, thesis.attachments, AttachmentKind.SUPERVISOR_REVIEW, "posudky"
    )

    # Staré PDF + jeho příloha jsou pryč.
    assert not (posudky / pdf_name).exists()
    assert all(not a.url_or_path.endswith(".pdf") for a in thesis.attachments)

    # XLSX se přesunul do archiv/ a v hlavní složce už není.
    assert not (posudky / xlsx_name).exists()
    archived = list((posudky / "archiv").glob("*.xlsx"))
    assert len(archived) == 1
    assert "_archiv_" in archived[0].name

    # Zůstala jediná příloha (archivovaný XLSX), označená jako neaktuální.
    assert len(thesis.attachments) == 1
    att = thesis.attachments[0]
    assert att.is_current is False
    assert att.url_or_path.startswith("posudky/archiv/")
    assert (thesis_documents_dir(thesis.id) / att.url_or_path).exists()


def test_archive_ignores_other_review_role(service: ThesisService) -> None:
    thesis = Thesis(type=ThesisType.BP, academic_year="2025/2026", title_cs="Vzorová práce")
    service.upsert_thesis(thesis)

    posudky = thesis_documents_dir(thesis.id) / "posudky"
    opp_name = "Vzor_posudek-oponenta_2026-06-01.xlsx"
    _write(posudky / opp_name)
    thesis.attachments = [
        Attachment(
            label=opp_name, url_or_path=f"posudky/{opp_name}",
            kind=AttachmentKind.OPPONENT_REVIEW, is_file=True,
            version=1, is_current=True,
        ),
    ]

    # Archivujeme posudek VEDOUCÍHO — oponentský se nesmí dotknout.
    service._archive_previous_review_files(
        thesis.id, thesis.attachments, AttachmentKind.SUPERVISOR_REVIEW, "posudky"
    )

    assert (posudky / opp_name).exists()
    assert thesis.attachments[0].is_current is True


def test_prune_missing_documents(service: ThesisService) -> None:
    thesis = Thesis(type=ThesisType.BP, academic_year="2025/2026", title_cs="Vzorová práce")
    service.upsert_thesis(thesis)

    base = thesis_documents_dir(thesis.id)
    present = "text/Vzor_text-prace_2026-06-01.pdf"
    missing = "text/Vzor_text-prace_2026-05-01.pdf"
    _write(base / present)  # existuje
    # `missing` schválně nevytvoříme

    thesis.attachments = [
        Attachment(label="present", url_or_path=present, kind=AttachmentKind.THESIS_TEXT, is_file=True),
        Attachment(label="missing", url_or_path=missing, kind=AttachmentKind.THESIS_TEXT, is_file=True),
        Attachment(label="odkaz", url_or_path="https://example.org", kind=AttachmentKind.OTHER, is_file=False),
    ]
    service.upsert_thesis(thesis)

    removed = service.prune_missing_documents(thesis.id)
    assert removed == 1

    refreshed = service.get_thesis(thesis.id)
    assert refreshed is not None
    labels = {a.label for a in refreshed.attachments}
    assert labels == {"present", "odkaz"}
