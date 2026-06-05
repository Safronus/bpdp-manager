"""Testy opravy archivace posudků — žádná kumulace „_archiv_" + repair názvů."""

from __future__ import annotations

from pathlib import Path

import pytest

from bpdpmanager.models import Attachment, Thesis
from bpdpmanager.models.enums import AttachmentKind, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def test_archiving_does_not_renest_old_archives(service: ThesisService, tmp_path: Path) -> None:
    t = Thesis(type=ThesisType.BP, academic_year="2024/2025")
    service.upsert_thesis(t)
    src = tmp_path / "p.xlsx"
    src.write_bytes(b"x")

    # Tři generace posudku za sebou (attach_review_files archivuje předchozí).
    for _ in range(3):
        s = tmp_path / "gen.xlsx"
        s.write_bytes(b"x")
        service.attach_document(t.id, s, kind=AttachmentKind.SUPERVISOR_REVIEW)
        # simuluj archivaci předchozích current souborů
        t2 = service.get_thesis(t.id)
        service._archive_previous_review_files(
            t2.id, t2.attachments, AttachmentKind.SUPERVISOR_REVIEW, "posudky"
        )
        service.upsert_thesis(t2)

    # Žádný název nesmí mít „_archiv_" vícekrát (kumulace).
    for att in service.get_thesis(t.id).attachments:
        assert att.url_or_path.count("_archiv_") <= 1, att.url_or_path


def test_repair_collapses_nested_archive(service: ThesisService) -> None:
    t = Thesis(type=ThesisType.BP, academic_year="2024/2025")
    nested = (
        "posudky/archiv/X_posudek-vedouciho_2026-06-05"
        "_archiv_2026-06-05_210633_archiv_2026-06-05_213241_archiv_2026-06-05_215737.xlsx"
    )
    t.attachments = [
        Attachment(label=Path(nested).name, url_or_path=nested,
                   kind=AttachmentKind.SUPERVISOR_REVIEW, is_file=True,
                   is_current=False, version=1),
    ]
    service.upsert_thesis(t)

    n = service.repair_review_archive_names()
    assert n == 1
    att = service.get_thesis(t.id).attachments[0]
    # Sloučeno na první archiv segment.
    assert att.url_or_path == (
        "posudky/archiv/X_posudek-vedouciho_2026-06-05_archiv_2026-06-05_210633.xlsx"
    )
    assert att.url_or_path.count("_archiv_") == 1


def test_repair_idempotent_on_clean(service: ThesisService) -> None:
    t = Thesis(type=ThesisType.BP, academic_year="2024/2025")
    clean = "posudky/archiv/X_2026-06-05_archiv_2026-06-05_215737.xlsx"
    t.attachments = [
        Attachment(label="x", url_or_path=clean, kind=AttachmentKind.SUPERVISOR_REVIEW,
                   is_file=True, is_current=False, version=1),
    ]
    service.upsert_thesis(t)
    assert service.repair_review_archive_names() == 0
