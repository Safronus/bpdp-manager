"""Hromadný export PDF mých posudků do zvolené složky (pro tisk).

Sdílí logiku mezi záložkami „Aktuálně vedené práce" (posudek vedoucího)
a „Oponované práce" (posudek oponenta). UI vrstva jen sestaví seznam úloh
(jméno, cesta k PDF) a zavolá :func:`export_my_review_pdfs`.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget


def export_my_review_pdfs(
    parent: QWidget, jobs: list[tuple[str, Path | None]]
) -> None:
    """Zkopíruje nejnovější PDF mých posudků pro vybrané práce do složky.

    ``jobs`` je seznam dvojic ``(jméno_studenta, cesta_k_PDF | None)``. Práce
    bez vytvořeného PDF posudku se přeskočí a uvedou v souhrnu. Při kolizi
    názvu ve cílové složce se soubor přepíše.
    """
    if not jobs:
        QMessageBox.information(
            parent, "Export PDF posudků", "Nevybrali jste žádnou práci."
        )
        return

    have = [(name, pdf) for (name, pdf) in jobs if pdf is not None and pdf.exists()]
    missing = [name for (name, pdf) in jobs if pdf is None or not pdf.exists()]

    if not have:
        QMessageBox.information(
            parent,
            "Export PDF posudků",
            "Žádná z vybraných prací nemá vytvořený PDF posudek — "
            "není co exportovat.",
        )
        return

    target = QFileDialog.getExistingDirectory(
        parent, "Vyberte složku pro export PDF posudků"
    )
    if not target:
        return
    target_dir = Path(target)

    exported: list[str] = []
    failed: list[str] = []
    for name, pdf in have:
        try:
            shutil.copy2(pdf, target_dir / pdf.name)  # přepíše existující
            exported.append(name)
        except OSError as exc:
            failed.append(f"{name} ({exc.strerror or exc})")

    lines = [f"✅ Exportováno {len(exported)} PDF posudků do:", str(target_dir)]
    if missing:
        lines += ["", f"⏭ Přeskočeno (bez PDF posudku): {len(missing)}"]
        lines += [f"   • {n}" for n in missing]
    if failed:
        lines += ["", f"⚠ Nepodařilo se zkopírovat: {len(failed)}"]
        lines += [f"   • {n}" for n in failed]
    QMessageBox.information(parent, "Souhrn exportu posudků", "\n".join(lines))
