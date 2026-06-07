"""Přímé vyhledání a stažení CSV s kvalifikační prací ze STAG (stag.utb.cz).

Veřejný záznam kvalifikační práce nevyžaduje přihlášení. Modul replikuje sled
požadavků, který v prohlížeči provádí *Prohlížení → Kvalifikační práce*:

1. ``GET prohlizeni.html``        → JSESSIONID + ``_csrf`` token
2. následuj odkaz **PraceState**  → vyhledávací formulář (``formPrace``)
3. ``POST`` formuláře             → tabulka výsledků (řádek = jedna práce,
   ``praceIdno`` je zakódované v ``pc_interactionstate`` odkazu řádku)
4. ``GET ProhlizeniPrint CSV``    → CSV s prací dle ``adipIdno`` (= ``praceIdno``)

Modul je **čistě síťová vrstva** (pouze standardní knihovna ``urllib``).
Parsování staženého CSV řeší :mod:`bpdpmanager.services.stag_csv_importer`.

Architektura: UI sahá na STAG jen přes tento modul (žádné HTTP přímo v UI).
"""

from __future__ import annotations

import base64
import html
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from http.cookiejar import CookieJar

# ── Konstanty ────────────────────────────────────────────────────────────────

BASE_URL = "https://stag.utb.cz"
PROHLIZENI_URL = f"{BASE_URL}/portal/studium/prohlizeni.html"
# Veřejný export jedné práce do CSV (funguje i bez session, dle adipIdno).
CSV_EXPORT_URL = (
    f"{BASE_URL}/StagPortletsJSR168/ProhlizeniPrint"
    "?stateClass=cz.zcu.stag.portlets168.prohlizeni.prace.PraceInfoState"
    "&wservice=kvalifikacniprace/getKvalifikacniPrace"
    "&outputFormat=CSV&adipIdno={adipidno}&lang=cs"
)

_USER_AGENT = "Mozilla/5.0 (BPDPManager STAG import)"
_DEFAULT_TIMEOUT = 30.0

# Role druhé osoby ve vyhledávání (kromě studenta).
ROLE_SUPERVISOR = "vedouci"
ROLE_OPPONENT = "oponent"


# Když ani delší timeout nestačí (STAG přílohu nestihl připravit/odeslat),
# uživateli vždy zbývá ruční cesta — nabídneme ji přímo v chybové hlášce.
MANUAL_DOWNLOAD_HINT = (
    "Soubor jde vždy stáhnout ze STAGu ručně (přes webový prohlížeč) "
    "a přidat k práci v sekci „Dokumenty“."
)
_TIMEOUT_MSG = (
    "STAG neodpověděl včas — velký soubor nebo příprava na serveru trvá "
    "příliš dlouho. " + MANUAL_DOWNLOAD_HINT
)


class StagError(Exception):
    """Chyba při komunikaci se STAG (síť, neočekávaná odpověď, prázdný výsledek)."""


class StagCancelledError(StagError):
    """Stahování bylo přerušeno uživatelem (progress callback vrátil ``False``)."""


# Velikost bloku pro streamované stahování souborů (průběžný progres).
_DOWNLOAD_CHUNK = 64 * 1024

# Timeout pro stahování SOUBORŮ je výrazně delší než pro běžné dotazy: STAG
# velké přílohy / ZIP balíčky generuje až na vyžádání, takže než začne posílat
# data (TTFB), může to trvat i desítky sekund až minuty (prohlížeč žádný pevný
# limit nemá). Krátký 30s timeout takové soubory zbytečně shazoval.
# Kalibrace dle reálného měření celé knihovny (≈585 souborů):
# i největší 948MB ZIP dojel za ~370 s (TTFB 162 s + přenos), nejhorší poměr
# čas/velikost ≈ 0,4 s/MB. Volíme ~1,2 s/MB (≈3× rezerva) + malou bázi pro
# drobné soubory; strop 30 min pokryje i hypoteticky obří přílohy.
_DOWNLOAD_TIMEOUT = 900.0       # fallback, když velikost neznáme (> nejhorší pozorovaný čas)
_DOWNLOAD_TIMEOUT_BASE = 120.0  # rezerva na spojení + krátký TTFB u malých souborů
_DOWNLOAD_TIMEOUT_PER_MB = 1.2  # s/MB navíc (TTFB roste s velikostí + přenos)
_DOWNLOAD_TIMEOUT_MAX = 1800.0  # strop (30 min)


def download_timeout_for(size_hint: int) -> float:
    """Flexibilní timeout pro stažení souboru podle jeho velikosti.

    Velký soubor (STAG ho déle připravuje a déle posílá) dostane více času,
    malý naopak selže rychleji, když opravdu visí. Při neznámé velikosti
    vrací velkorysý fallback. Přibližně ``base + 1,2 s/MB``, max 30 min.
    """
    if not size_hint or size_hint <= 0:
        return _DOWNLOAD_TIMEOUT
    size_mb = size_hint / (1024 * 1024)
    return min(
        _DOWNLOAD_TIMEOUT_MAX,
        _DOWNLOAD_TIMEOUT_BASE + size_mb * _DOWNLOAD_TIMEOUT_PER_MB,
    )


# Detail práce (veřejný, bez přihlášení) — odtud se tahá seznam souborů.
DETAIL_URL = (
    f"{BASE_URL}/StagPortletsJSR168/CleanUrl"
    "?urlid=prohlizeni-prace-detail&praceIdno={praceidno}"
)


@dataclass
class StagFile:
    """Jeden soubor u práce ve STAG (plný text / příloha / posudek)."""

    soubidno: str          # ID souboru ve STAG
    filename: str          # název souboru (např. „Novak_M_v.pdf")
    download_path: str     # relativní cesta ke stažení (k BASE_URL)
    section: str = "other"  # text | appendix | supervisor_review | opponent_review | other
    size_hint: int = 0     # odhad velikosti v bajtech z výpisu STAG (0 = neznámá)


@dataclass
class StagThesisResult:
    """Jeden řádek z výsledků vyhledávání kvalifikačních prací."""

    adipidno: str
    surname: str = ""
    name: str = ""
    title: str = ""
    type_label: str = ""
    supervisor: str = ""
    reviewer: str = ""
    year: str = ""  # rok obhajoby (z data obhajoby v tabulce výsledků)
    status_code: str = ""  # STAG kód stavu z tabulky výsledků (DUO/ND/DBPOO/OPUNO…)
    defense_date: str = ""  # datum obhajoby „DD.MM.RRRR" (prázdné u nedokončených)
    # Doplněno až dotažením CSV detailu (tabulka výsledků je neobsahuje):
    academic_year: str = ""  # akademický rok „RRRR/RRRR" (z data zadání)
    obor: str = ""           # STAG kód oboru (oborKombinaceStudenta)

    @property
    def student_full(self) -> str:
        parts = [p for p in (self.surname, self.name) if p]
        return " ".join(parts) if parts else "(neznámý student)"

    @property
    def display_label(self) -> str:
        """Lidsky čitelný popis pro výběr ve frontě výsledků."""
        bits: list[str] = [self.student_full]
        if self.title:
            bits.append(f"— {self.title}")
        meta = [m for m in (self.type_label, self.year) if m]
        if meta:
            bits.append("(" + ", ".join(meta) + ")")
        return " ".join(bits)


# ── Klient ───────────────────────────────────────────────────────────────────


class StagClient:
    """Drží session (cookies + ``_csrf``) napříč požadavky jednoho hledání."""

    def __init__(self, timeout: float = _DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout
        self._cookies = CookieJar()
        ctx = ssl.create_default_context()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._cookies),
            urllib.request.HTTPSHandler(context=ctx),
        )
        self._csrf: str | None = None

    # --- nízkoúrovňové HTTP ------------------------------------------------

    def _request(
        self,
        url: str,
        data: bytes | None = None,
        *,
        decode: bool = True,
        ajax: bool = False,
    ) -> str | bytes:
        headers = {"User-Agent": _USER_AGENT, "Accept": "text/html,*/*"}
        if data is not None:
            headers["Content-Type"] = (
                "application/x-www-form-urlencoded; charset=UTF-8"
            )
        if ajax:
            headers["X-Requested-With"] = "XMLHttpRequest"
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with self._opener.open(req, timeout=self.timeout) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            raise StagError(
                f"STAG odpověděl chybou HTTP {exc.code}. "
                "Zkus to znovu, případně stáhni CSV ručně z webu STAG."
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise StagError(
                "Nepodařilo se spojit se STAG (stag.utb.cz). "
                "Zkontroluj připojení k internetu."
            ) from exc
        if not decode:
            return raw
        return raw.decode("utf-8", "replace")

    # --- veřejné API -------------------------------------------------------

    def search(
        self,
        student_surname: str,
        person_surname: str = "",
        person_role: str = ROLE_OPPONENT,
    ) -> list[StagThesisResult]:
        """Vyhledá kvalifikační práce dle příjmení studenta (+ volitelně
        příjmení vedoucího/oponenta).

        ``person_role`` určuje, do kterého pole se ``person_surname`` vloží:
        ``ROLE_SUPERVISOR`` → vedoucí, ``ROLE_OPPONENT`` → oponent.
        """
        student_surname = (student_surname or "").strip()
        person_surname = (person_surname or "").strip()
        if not student_surname and not person_surname:
            raise StagError("Zadej příjmení studenta nebo vedoucího/oponenta.")

        action_url = self._open_search_form()

        fields = {
            "studentSearchPrijmeni": student_surname,
            "stavStudentaSearchTyp": "",
            "praceSearchNazev": "",
            "praceSearchVedouci": "",
            "praceSearchOponent": "",
            "praceSearchKlicovaSlova": "",
            "praceSearchKlicovaSlovaAnglicky": "",
            "praceSearchTykaSePraxe": "",
            "praceSearchFakultaVSKP": "",
            "_csrf": self._csrf or "",
        }
        if person_surname:
            if person_role == ROLE_SUPERVISOR:
                fields["praceSearchVedouci"] = person_surname
            else:
                fields["praceSearchOponent"] = person_surname

        data = urllib.parse.urlencode(fields, encoding="utf-8").encode()
        page = self._request(BASE_URL + action_url, data=data)
        assert isinstance(page, str)

        # STAG implicitně stránkuje (server vrací jen první stránku ~20 ř.),
        # takže by se část vedených/oponovaných prací do seznamu nedostala.
        # Výsledková stránka ale nese odkaz „Vypnout stránkování" — následuj
        # ho a parsuj kompletní seznam (header „Nalezeno N záznamů").
        page = self._maybe_disable_pagination(page)
        return _parse_results(page)

    def _maybe_disable_pagination(self, page: str) -> str:
        """Pokud výsledková stránka nabízí „Vypnout stránkování", načte plnou
        (nestránkovanou) variantu a vrátí ji; jinak vrátí původní stránku."""
        link = _find_disable_pagination_link(page)
        if not link:
            return page
        try:
            full = self._request(BASE_URL + link)
        except StagError:
            return page
        if isinstance(full, str) and "prace_prijmeni_search_result_big" in full:
            return full
        return page

    def download_csv(self, adipidno: str) -> bytes:
        """Stáhne CSV s prací dle ``adipIdno`` (veřejný export)."""
        adipidno = (adipidno or "").strip()
        if not adipidno.isdigit():
            raise StagError(f"Neplatné STAG ID práce: {adipidno!r}")
        url = CSV_EXPORT_URL.format(adipidno=adipidno)
        raw = self._request(url, decode=False)
        assert isinstance(raw, bytes)
        if not raw or b";" not in raw[:400]:
            raise StagError(
                "STAG nevrátil platné CSV (možná byl záznam mezitím odebrán)."
            )
        return raw

    def list_thesis_files(self, praceidno: str) -> list[StagFile]:
        """Vrátí seznam veřejných souborů práce (plný text, přílohy, posudky).

        Replikuje AJAX volání z detailu práce (``GenericAjaxLoad2`` — pro každou
        sekci jeden POST do resource fáze portletu se seznamem souborů).
        """
        praceidno = (praceidno or "").strip()
        if not praceidno.isdigit():
            raise StagError(f"Neplatné STAG ID práce: {praceidno!r}")

        detail = self._request(DETAIL_URL.format(praceidno=praceidno))
        assert isinstance(detail, str)

        files: list[StagFile] = []
        for url_b64, body_b64 in _find_ajax_loads(detail):
            url = _b64_std(url_b64)
            body = _b64_std(body_b64)
            if not url or not body:
                continue
            section = _section_from_body(body)
            try:
                frag = self._request(
                    BASE_URL + url, data=body.encode("utf-8"), ajax=True
                )
            except StagError:
                continue
            assert isinstance(frag, str)
            for soubidno, fname, href, size in _parse_file_fragment(frag):
                files.append(
                    StagFile(
                        soubidno=soubidno,
                        filename=fname,
                        download_path=href,
                        section=section,
                        size_hint=size,
                    )
                )
        _refine_sections(files)
        return files

    def download_file(self, download_path: str) -> bytes:
        """Stáhne jeden soubor dle relativní cesty (``StagFile.download_path``)."""
        path = (download_path or "").strip()
        if not path:
            raise StagError("Chybí cesta ke stažení souboru.")
        url = path if path.startswith("http") else BASE_URL + path
        raw = self._request(url, decode=False)
        assert isinstance(raw, bytes)
        if not raw:
            raise StagError("STAG vrátil prázdný soubor.")
        return raw

    def download_file_streamed(
        self,
        download_path: str,
        on_progress: Callable[[int, int | None], bool | None] | None = None,
        timeout: float | None = None,
    ) -> bytes:
        """Stáhne soubor **po blocích** a po každém zavolá ``on_progress``.

        ``on_progress(downloaded, total)`` dostane počet stažených bajtů a
        celkovou velikost (z ``Content-Length``; ``None`` když není známá).
        Když callback vrátí ``False``, stahování se přeruší a vyhodí se
        :class:`StagCancelledError`. ``timeout`` je delší než u běžných dotazů
        (velké/on-demand ZIP přílohy mají dlouhý TTFB). Vrací obsah souboru.
        """
        path = (download_path or "").strip()
        if not path:
            raise StagError("Chybí cesta ke stažení souboru.")
        url = path if path.startswith("http") else BASE_URL + path
        headers = {"User-Agent": _USER_AGENT, "Accept": "*/*"}
        req = urllib.request.Request(url, headers=headers)
        chunks: list[bytes] = []
        downloaded = 0
        to = timeout if timeout is not None else _DOWNLOAD_TIMEOUT
        try:
            with self._opener.open(req, timeout=to) as resp:
                cl = resp.headers.get("Content-Length")
                total = int(cl) if cl and cl.isdigit() else None
                if on_progress is not None and on_progress(0, total) is False:
                    raise StagCancelledError("Stahování přerušeno.")
                while True:
                    chunk = resp.read(_DOWNLOAD_CHUNK)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    if on_progress is not None and on_progress(downloaded, total) is False:
                        raise StagCancelledError("Stahování přerušeno.")
        except urllib.error.HTTPError as exc:
            raise StagError(
                f"STAG odpověděl chybou HTTP {exc.code} při stahování souboru."
            ) from exc
        except TimeoutError as exc:  # socket.timeout je podtřída TimeoutError
            raise StagError(_TIMEOUT_MSG) from exc
        except (urllib.error.URLError, OSError) as exc:
            # URLError často obaluje socket.timeout → rozliš podle příčiny.
            if isinstance(getattr(exc, "reason", None), TimeoutError):
                raise StagError(_TIMEOUT_MSG) from exc
            raise StagError(
                "Nepodařilo se stáhnout soubor ze STAG (spojení / timeout). "
                + MANUAL_DOWNLOAD_HINT
            ) from exc
        raw = b"".join(chunks)
        if not raw:
            raise StagError("STAG vrátil prázdný soubor.")
        return raw

    # --- vnitřní -----------------------------------------------------------

    def _open_search_form(self) -> str:
        """Načte úvodní stránku, vytáhne ``_csrf`` a vrátí *action* URL
        vyhledávacího formuláře kvalifikačních prací (``formPrace``)."""
        page = self._request(PROHLIZENI_URL + "?pc_lang=cs")
        assert isinstance(page, str)

        m_csrf = re.search(r'name="_csrf"\s+value="([0-9a-f-]+)"', page)
        self._csrf = m_csrf.group(1) if m_csrf else None

        prace_link = _find_prace_state_link(page)
        if not prace_link:
            raise StagError(
                "Na STAG se nepodařilo najít sekci Kvalifikační práce "
                "(změna webu STAG?). Stáhni CSV ručně z webu."
            )
        form_page = self._request(BASE_URL + prace_link)
        assert isinstance(form_page, str)

        m_action = re.search(
            r"name='formPrace'[^>]*action=\"([^\"]+)\"", form_page
        )
        if not m_action:
            raise StagError(
                "Na STAG se nepodařilo najít vyhledávací formulář prací "
                "(změna webu STAG?). Stáhni CSV ručně z webu."
            )
        # _csrf bývá i v action URL — preferuj hodnotu z hidden inputu,
        # ale když chyběl, vytáhni ho z action.
        if not self._csrf:
            m2 = re.search(r"_csrf=([0-9a-f-]+)", form_page)
            if m2:
                self._csrf = m2.group(1)
        return html.unescape(m_action.group(1))


# ── Parsování ──────────────────────────────────────────────────────────────


# Znaky base64 v JBoss tokenech: písmena/číslice + výplň ``*`` (= ``=``) a
# možné varianty základní (``+`` ``/``) i URL-safe (``-`` ``_``) abecedy.
_JBPNS_CHARS = r"[A-Za-z0-9*+/_-]"


def _b64_jbpns(token: str) -> bytes:
    """Dekóduje JBoss portal stav (``JBPNS_…``/base64, ``*`` zastupuje ``=``)."""
    s = token.replace("JBPNS_", "").replace("*", "=")
    s += "=" * (-len(s) % 4)
    for decoder in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            return decoder(s)
        except (ValueError, TypeError):
            continue
    return b""


def _find_prace_state_link(page: str) -> str | None:
    """Najde odkaz, jehož ``pc_navigationalstate`` kóduje ``PraceState``."""
    for raw_link in re.findall(
        r'"(/portal/studium/prohlizeni\.html\?[^"]*'
        r"pc_navigationalstate=JBPNS_" + _JBPNS_CHARS + r'+[^"]*)"',
        page,
    ):
        m = re.search(
            r"pc_navigationalstate=(JBPNS_" + _JBPNS_CHARS + r"+)", raw_link
        )
        if not m:
            continue
        if b"prace.PraceState" in _b64_jbpns(m.group(1)):
            return html.unescape(raw_link)
    return None


def _extract_praceidno(href: str) -> str | None:
    """Z ``pc_interactionstate`` odkazu řádku vytáhne ``praceIdno``."""
    m = re.search(r"pc_interactionstate=(JBPNS_" + _JBPNS_CHARS + r"+)", href)
    if not m:
        return None
    raw = _b64_jbpns(m.group(1))
    mm = re.search(rb"praceIdno[^0-9]{0,10}(\d{2,})", raw)
    return mm.group(1).decode() if mm else None


def _b64_std(token: str) -> str:
    """Dekóduje standardní base64 (argumenty ``GenericAjaxLoad2``) na text."""
    try:
        return base64.b64decode(token + "=" * (-len(token) % 4)).decode("utf-8", "replace")
    except (ValueError, TypeError):
        return ""


# GenericAjaxLoad2('<b64 url>', '<b64 post body>', ...) — sekce souborů v detailu.
_AJAX_LOAD_RE = re.compile(
    r"GenericAjaxLoad2\(\s*'([A-Za-z0-9+/=]+)'\s*,\s*'([A-Za-z0-9+/=]+)'", re.S
)


def _find_ajax_loads(detail_html: str) -> list[tuple[str, str]]:
    """Vrátí dvojice (b64 URL, b64 POST tělo) ze všech sekcí souborů detailu."""
    return _AJAX_LOAD_RE.findall(detail_html)


def _section_from_body(body: str) -> str:
    """Z POST těla (``pp_page`` / ``sou_aplikace``) odvodí typ sekce souborů.

    STAG má sekci souborů identifikovanou přímo v těle požadavku (spolehlivé,
    nezávislé na názvu souboru). „Soubor s průběhem obhajoby" nese v těle
    identifikátor s „OBHAJOB"/„PRUBEH".
    """
    up = body.upper()
    if "VEDOUCIHO" in up:
        return "supervisor_review"
    if "OPONENTA" in up or "OPONENTSKE" in up:
        return "opponent_review"
    if "OBHAJOB" in up or "PRUBEH" in up:
        return "defense_record"  # protokol / průběh obhajoby (SZZ)
    if "PRILOHY" in up:
        return "appendix"
    if "ELPODOBA" in up or "EL_PODOBA" in up:
        return "elpodoba"  # plný text + případné přílohy (rozliší se pořadím)
    return "other"


# <a ... href="...PagesDispatcherServlet?...soubidno=NNN...">název.pdf</a> (217 KB)
# Velikost za odkazem je volitelná (STAG ji u souborů uvádí, ale ne vždy).
_FILE_LINK_RE = re.compile(
    r'<a\b[^>]*href="([^"]*soubidno=(\d+)[^"]*)"[^>]*>(.*?)</a>'
    r'(?:\s*\(\s*([\d.,\s]+?)\s*([kKmMgG]?B)\s*\))?',
    re.S,
)


def _size_to_bytes(num: str, unit: str) -> int:
    """Převede „217", „KB" (resp. „1,2", „MB") na bajty. Nezdar → 0."""
    cleaned = re.sub(r"\s+", "", num or "").replace(",", ".")
    try:
        val = float(cleaned)
    except ValueError:
        return 0
    mult = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}.get(
        (unit or "").upper(), 1
    )
    return int(val * mult)


def _parse_file_fragment(fragment_html: str) -> list[tuple[str, str, str, int]]:
    """Z fragmentu vytáhne (soubidno, název, download href, velikost v bajtech)."""
    out: list[tuple[str, str, str, int]] = []
    for href, soubidno, label, size_num, size_unit in _FILE_LINK_RE.findall(
        fragment_html
    ):
        path = html.unescape(href)
        name = _WS_RE.sub(" ", html.unescape(_TAG_RE.sub("", label))).strip()
        size = _size_to_bytes(size_num, size_unit) if size_unit else 0
        out.append((soubidno, name, path, size))
    return out


def _fold_ascii(s: str) -> str:
    """Malá písmena bez diakritiky — pro porovnávání názvů souborů."""
    import unicodedata

    nfd = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in nfd if not unicodedata.combining(c)).lower()


def is_defense_record_filename(name: str) -> bool:
    """True, když název souboru vypadá jako protokol/zápis o průběhu obhajoby.

    Pokrývá reálné názvy ze STAG: ``obhajoba_19.pdf``,
    ``09_Prijmeni_zapis_o_statni_zaverecne_zkousky.pdf``, „protokol o obhajobě"
    apod. Záměrně NEbere posudky ani prezentace.
    """
    f = _fold_ascii(name)
    # „obhajoba…" jako začátek názvu (po případných číslicích/podtržítkách).
    core = f.lstrip("0123456789_-. ")
    if core.startswith("obhajoba") or core.startswith("obhajob_"):
        return True
    if "zapis" in f and ("statni" in f or "zaverecn" in f):
        return True
    if ("prubeh" in f or "protokol" in f or "zaznam" in f) and "obhajob" in f:
        return True
    return False


def _refine_sections(files: list[StagFile]) -> None:
    """V sekci „el. podoba" je 1. soubor plný text, další jsou přílohy;
    soubory s názvem protokolu/zápisu obhajoby přeřadí z „other" na
    „defense_record"."""
    first_elpodoba = True
    for f in files:
        if f.section == "elpodoba":
            f.section = "text" if first_elpodoba else "appendix"
            first_elpodoba = False
        elif f.section == "other" and is_defense_record_filename(f.filename):
            f.section = "defense_record"


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_DATE_RE = re.compile(r"\b(\d{1,2}\.\s*\d{1,2}\.\s*(\d{4}))\b")
_TYPE_KEYWORDS = (
    "diplom",
    "bakal",
    "bachelor",
    "master",
    "disertač",
    "dissertation",
    "rigoróz",
)


def _clean(fragment: str) -> str:
    return _WS_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", fragment))).strip()


# Odkaz „Vypnout stránkování" na výsledkové stránce (přepne na plný seznam).
_DISABLE_PAGING_RE = re.compile(
    r'<a[^>]+href="([^"]+prohlizeni\.html[^"]+)"[^>]*>\s*'
    r"Vypnout stránkování\s*</a>",
    re.S,
)

# Stav práce ve sloupci „Stav práce" — ikonka vlaječky s titulkem,
# ve kterém je kód v závorce, např. „…s úspěšnou obhajobou (DUO)."
_STATUS_CODE_RE = re.compile(
    r"flag_\w+\.gif.{0,60}?title=['\"][^'\"]*?\(([A-Z]{2,7})\)",
    re.S,
)


def _find_disable_pagination_link(page: str) -> str | None:
    """Najde odkaz „Vypnout stránkování" (vede na nestránkovaný výpis)."""
    m = _DISABLE_PAGING_RE.search(page)
    return html.unescape(m.group(1)) if m else None


def _parse_results(page: str) -> list[StagThesisResult]:
    """Z výsledkové stránky vytáhne seznam prací (1 i více výsledků)."""
    idx = page.find("prace_prijmeni_search_result_big")
    results: list[StagThesisResult] = []
    seen: set[str] = set()

    if idx >= 0:
        end = page.find("</table>", idx)
        table = page[idx : end if end > 0 else len(page)]
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S):
            anchors = re.findall(
                r'<a[^>]+href="([^"]+prohlizeni\.html[^"]+)"[^>]*>(.*?)</a>',
                tr,
                re.S,
            )
            praceidno = None
            anchor_texts: list[str] = []
            for href, inner in anchors:
                pid = _extract_praceidno(html.unescape(href))
                if pid:
                    praceidno = pid
                    anchor_texts.append(_clean(inner))
            if not praceidno or praceidno in seen:
                continue
            seen.add(praceidno)

            cells = [
                _clean(c)
                for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
            ]
            ms = _STATUS_CODE_RE.search(tr)
            status_code = ms.group(1) if ms else ""
            results.append(
                _build_result(praceidno, cells, anchor_texts, status_code)
            )

    if results:
        return results

    # Fallback — žádná tabulka: zkus přímý CSV-export odkaz (detail jedné práce)
    for adip in dict.fromkeys(
        re.findall(r"[?&]adipIdno=(\d+)", page)
    ):
        results.append(StagThesisResult(adipidno=adip))
    return results


def _build_result(
    praceidno: str,
    cells: list[str],
    anchor_texts: list[str],
    status_code: str = "",
) -> StagThesisResult:
    # Název = nejdelší text odkazu řádku (odkaz na detail práce).
    title = max(anchor_texts, key=len, default="") if anchor_texts else ""

    surname = cells[1] if len(cells) > 1 else ""
    name = cells[2] if len(cells) > 2 else ""
    # Příjmení/jméno bývají také odkaz — pokud cell 1 splývá s názvem, oprav.
    if surname and surname == title:
        surname = ""

    type_label = ""
    year = ""
    defense_date = ""
    for c in cells:
        low = c.lower()
        if not type_label and any(k in low for k in _TYPE_KEYWORDS):
            type_label = c
        if not year:
            md = _DATE_RE.search(c)
            if md:
                year = md.group(2)
                defense_date = md.group(1).replace(" ", "")

    # Vedoucí / oponent — sloupce 6 a 7 v desktop layoutu (best effort).
    supervisor = cells[6] if len(cells) > 6 else ""
    reviewer = cells[7] if len(cells) > 7 else ""

    return StagThesisResult(
        adipidno=praceidno,
        surname=surname,
        name=name,
        title=title,
        type_label=type_label,
        supervisor=supervisor,
        reviewer=reviewer,
        year=year,
        status_code=status_code,
        defense_date=defense_date,
    )


# ── Modul-level convenience ──────────────────────────────────────────────────


def search_theses(
    student_surname: str,
    person_surname: str = "",
    person_role: str = ROLE_OPPONENT,
    *,
    timeout: float = _DEFAULT_TIMEOUT,
) -> list[StagThesisResult]:
    """Jednorázové vyhledání (vytvoří dočasný :class:`StagClient`)."""
    return StagClient(timeout=timeout).search(
        student_surname, person_surname, person_role
    )


def download_csv(adipidno: str, *, timeout: float = _DEFAULT_TIMEOUT) -> bytes:
    """Jednorázové stažení CSV dle ``adipIdno``."""
    return StagClient(timeout=timeout).download_csv(adipidno)


def list_thesis_files(
    praceidno: str, *, timeout: float = _DEFAULT_TIMEOUT
) -> list[StagFile]:
    """Jednorázový výpis souborů práce dle ``praceIdno`` (= ``adipIdno``)."""
    return StagClient(timeout=timeout).list_thesis_files(praceidno)
