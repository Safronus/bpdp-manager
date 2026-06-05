"""Odesílání posudků e-mailem sekretářkám oborů.

Čistě transportní/skládací vrstva (stdlib ``smtplib`` + ``email``). UI sahá na
poštu jen přes tento modul. Heslo se **nikdy neukládá** — předává se jako
argument při každém odeslání / testu.

Pozn. k UTB Office365: dokumentace CVT UTB uvádí pro odchozí poštu
``outlook.office365.com:587`` (STARTTLS) s **OAuth2**. Pokud má tenant vypnutý
Basic Auth (SMTP AUTH), přímé přihlášení heslem selže — pro ten případ má
volající k dispozici fallback :func:`save_as_eml` (otevře hotový e-mail
v mailovém klientovi uživatele, kde je přihlášen přes OAuth2).
"""

from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

from ..models import SmtpConfig


class EmailError(Exception):
    """Chyba při sestavení / odeslání / testu e-mailu (čitelná pro uživatele)."""


@dataclass
class MailDraft:
    """Připravený e-mail (bez hesla) — k odeslání nebo uložení jako .eml."""

    from_addr: str
    to: list[str]
    subject: str
    body: str
    cc: list[str] = field(default_factory=list)
    from_name: str = ""
    attachments: list[Path] = field(default_factory=list)

    @property
    def recipients(self) -> list[str]:
        """Všichni příjemci (To + Cc) — pro SMTP obálku."""
        seen: list[str] = []
        for addr in [*self.to, *self.cc]:
            a = (addr or "").strip()
            if a and a not in seen:
                seen.append(a)
        return seen


# ── Sestavení zprávy ─────────────────────────────────────────────────────────


def build_message(draft: MailDraft) -> EmailMessage:
    """Sestaví ``EmailMessage`` z draftu (tělo + PDF přílohy)."""
    if not draft.from_addr.strip():
        raise EmailError("Chybí e-mail odesílatele (doplň ho v profilu).")
    if not draft.recipients:
        raise EmailError("Není zadán žádný příjemce.")

    msg = EmailMessage()
    msg["From"] = formataddr((draft.from_name or "", draft.from_addr.strip()))
    msg["To"] = ", ".join(a.strip() for a in draft.to if a.strip())
    if draft.cc:
        msg["Cc"] = ", ".join(a.strip() for a in draft.cc if a.strip())
    msg["Subject"] = draft.subject
    msg.set_content(draft.body)

    for path in draft.attachments:
        p = Path(path)
        if not p.is_file():
            raise EmailError(f"Příloha neexistuje: {p.name}")
        data = p.read_bytes()
        # Posudky jsou PDF; u ostatních použij obecný binární typ.
        if p.suffix.lower() == ".pdf":
            maintype, subtype = "application", "pdf"
        else:
            maintype, subtype = "application", "octet-stream"
        msg.add_attachment(
            data, maintype=maintype, subtype=subtype, filename=p.name
        )
    return msg


def save_as_eml(draft: MailDraft, path: Path) -> Path:
    """Uloží zprávu jako ``.eml`` (k otevření v mailovém klientovi uživatele)."""
    msg = build_message(draft)
    path = Path(path)
    path.write_bytes(bytes(msg))
    return path


# ── SMTP ─────────────────────────────────────────────────────────────────────


def _connect(smtp: SmtpConfig, timeout: float = 30.0) -> smtplib.SMTP:
    """Naváže spojení dle konfigurace (STARTTLS / SSL / bez šifrování)."""
    host = (smtp.host or "").strip()
    if not host:
        raise EmailError("Chybí adresa SMTP serveru (zkontroluj nastavení e-mailu).")
    try:
        if smtp.security == "ssl":
            ctx = ssl.create_default_context()
            conn: smtplib.SMTP = smtplib.SMTP_SSL(
                host, smtp.port, timeout=timeout, context=ctx
            )
        else:
            conn = smtplib.SMTP(host, smtp.port, timeout=timeout)
            conn.ehlo()
            if smtp.security == "starttls":
                ctx = ssl.create_default_context()
                conn.starttls(context=ctx)
                conn.ehlo()
        return conn
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailError(
            f"Nepodařilo se připojit k serveru {host}:{smtp.port} — {exc}"
        ) from exc


def _username(smtp: SmtpConfig, from_addr: str) -> str:
    return (smtp.username or "").strip() or (from_addr or "").strip()


def _login(conn: smtplib.SMTP, smtp: SmtpConfig, from_addr: str, password: str) -> None:
    user = _username(smtp, from_addr)
    if not user:
        raise EmailError("Chybí přihlašovací jméno (e-mail) pro SMTP.")
    try:
        conn.login(user, password)
    except smtplib.SMTPAuthenticationError as exc:
        raise EmailError(
            "Přihlášení k SMTP serveru selhalo. U UTB Office365 bývá vypnuté "
            "přihlašování heslem (vyžaduje OAuth2) — v tom případě použij "
            "odeslání přes mailového klienta (.eml).\n\nDetail: "
            f"{exc.smtp_code} {exc.smtp_error!r}"
        ) from exc
    except smtplib.SMTPException as exc:
        raise EmailError(f"Přihlášení k SMTP selhalo: {exc}") from exc


def test_connection(smtp: SmtpConfig, from_addr: str, password: str) -> None:
    """Otestuje spojení + přihlášení (bez odeslání). Při neúspěchu vyhodí EmailError."""
    conn = _connect(smtp)
    try:
        _login(conn, smtp, from_addr, password)
    finally:
        try:
            conn.quit()
        except smtplib.SMTPException:
            pass


def send_via_smtp(smtp: SmtpConfig, password: str, draft: MailDraft) -> None:
    """Odešle zprávu přes SMTP. Při jakémkoli problému vyhodí EmailError."""
    msg = build_message(draft)
    conn = _connect(smtp)
    try:
        _login(conn, smtp, draft.from_addr, password)
        try:
            conn.send_message(msg)
        except smtplib.SMTPException as exc:
            raise EmailError(f"Odeslání se nezdařilo: {exc}") from exc
    finally:
        try:
            conn.quit()
        except smtplib.SMTPException:
            pass


# ── Skládání textu ───────────────────────────────────────────────────────────


def compose_subject(role: str, secretary_name: str = "") -> str:
    """Předmět e-mailu dle role (vedoucí / oponent)."""
    what = "vedoucího" if role == "supervisor" else "oponenta"
    return f"Posudky {what} k odevzdání"


def compose_body(
    items: list[tuple[str, str, str, str]],
    *,
    role: str,
    secretary_name: str = "",
    secretary_greeting: str = "",
    sender_display: str = "",
) -> str:
    """Sestaví tělo e-mailu seskupené dle BP/DP.

    ``items`` = seznam ``(type_code, student_name, student_uni_id, title)``.
    ``secretary_greeting`` — vlastní oslovení; prázdné = formální výchozí.
    """
    what = "vedoucího" if role == "supervisor" else "oponenta"
    custom = (secretary_greeting or "").strip()
    if custom:
        # Vlastní oslovení — doplň čárku, pokud nekončí interpunkcí.
        greeting = custom if custom[-1] in ",.:!?" else f"{custom},"
    elif secretary_name:
        greeting = f"Dobrý den, paní {secretary_name},"
    else:
        greeting = "Dobrý den,"
    lines: list[str] = [
        greeting,
        "",
        f"v příloze zasílám posudky {what} k níže uvedeným kvalifikačním pracím:",
        "",
    ]
    for type_code, label in (("BP", "Bakalářské práce"), ("DP", "Diplomové práce")):
        group = [it for it in items if it[0] == type_code]
        if not group:
            continue
        lines.append(f"{label}:")
        for _tc, name, uni_id, title in group:
            ident = f" ({uni_id})" if uni_id else ""
            lines.append(f"  • {name}{ident} — „{title}“")
        lines.append("")
    lines.append("Děkuji a přeji hezký den.")
    lines.append("")
    lines.append("S pozdravem")
    if sender_display:
        lines.append(sender_display)
    return "\n".join(lines)
