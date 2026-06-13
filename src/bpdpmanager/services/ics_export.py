"""Export harmonogramu obhajob do iCalendar (.ics).

Vytvoří **jeden** .ics soubor s jednou událostí (``VEVENT``) na každou obhajobu
a volitelnou připomínkou (``VALARM``). Univerzální formát — Apple Kalendář
i Outlook ho naimportují přímo, Google přes import souboru.

Čistá logika bez UI a IO (snadno testovatelné). Časy se zapisují jako
„floating" lokální čas (bez časové zóny), což je pro osobní rozvrh dostatečné.
"""

from __future__ import annotations

from datetime import datetime

_PRODID = "-//BPDPManager//Harmonogram obhajob//CS"


def _esc(text: str) -> str:
    """Escapuje TEXT hodnotu dle RFC 5545 (``\\`` ``;`` ``,`` newline)."""
    return (
        (text or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """Zalomí řádek na max 75 oktetů (pokračování odsazené mezerou).

    Zalamuje po celých znacích (UTF-8 bezpečně), takže diakritika nepraskne.
    """
    if len(line.encode("utf-8")) <= 75:
        return line
    parts: list[str] = []
    cur = ""
    cur_len = 0
    for ch in line:
        b = len(ch.encode("utf-8"))
        # Pokračovací řádky mají na začátku mezeru (1 oktet) → limit 74 na obsah.
        limit = 75 if not parts else 74
        if cur_len + b > limit:
            parts.append(cur)
            cur, cur_len = ch, b
        else:
            cur += ch
            cur_len += b
    parts.append(cur)
    return "\r\n ".join(parts)


def _dt(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%S")


def build_ics(events: list[dict], *, dtstamp: datetime) -> str:
    """Sestaví obsah .ics souboru z událostí.

    ``events`` je seznam dictů s klíči ``uid``, ``start`` (datetime),
    ``end`` (datetime), ``summary``, volitelně ``location``, ``description``
    a ``reminder_min`` (int = minut předem, nebo ``None`` = bez připomínky).
    ``dtstamp`` se předává zvenčí (kvůli determinismu/testovatelnosti).
    """
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{_PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    stamp = _dt(dtstamp) + "Z"
    for e in events:
        lines += [
            "BEGIN:VEVENT",
            f"UID:{e['uid']}",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{_dt(e['start'])}",
            f"DTEND:{_dt(e['end'])}",
            f"SUMMARY:{_esc(e['summary'])}",
        ]
        if e.get("location"):
            lines.append(f"LOCATION:{_esc(e['location'])}")
        if e.get("description"):
            lines.append(f"DESCRIPTION:{_esc(e['description'])}")
        rem = e.get("reminder_min")
        if rem is not None:
            lines += [
                "BEGIN:VALARM",
                "ACTION:DISPLAY",
                f"DESCRIPTION:{_esc(e['summary'])}",
                f"TRIGGER:-PT{int(rem)}M",
                "END:VALARM",
            ]
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(ln) for ln in lines) + "\r\n"
