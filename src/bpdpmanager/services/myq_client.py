"""Konektor na tiskovou bránu MyQ (myq.utb.cz) — odeslání PDF k tisku.

MyQ web běží na stavovém frameworku **WSF** (stejný princip jako STAG portál).
Tisk se proto neprovádí jedním REST voláním, ale **sekvencí** akcí nad
serverovými komponentami. Klient ji „nahrává a přehrává" (record-replay):

    login(jméno, PIN)            POST /cs/      onLogin (objekt C3)
    upload(pdf):
        ① createTabCtrl "jobs"   POST /cs/app/  (otevři frontu úloh)
        ② onPrintFile (C68)      POST /cs/app/  (otevři nahrávací dialog)
        ③ onOK (C96) multipart   POST /cs/app/  (soubor C99 + nastavení tisku)

Postaveno na čistém **stdlib** (`urllib` + `CookieJar`) — žádné nové závislosti,
stejně jako ``stag_api.py``. **Přihlašovací údaje se NIKAM neukládají** —
předají se do :meth:`MyQClient.login` a dál se nedrží.

POZOR — křehkost: control ID, názvy polí a hodnoty nastavení jsou **zachyceny
z reálného provozu** (HAR, MyQ 8.2, 2026-06). Ověřeno, že jsou napříč sezeními
**stabilní**, ale když UTB MyQ aktualizuje UI, je nutné konstanty níže doladit.
Mapování přihlašovacích polí je nejisté a ladí se při prvním živém běhu.
"""

from __future__ import annotations

import json
import re
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.cookiejar import CookieJar
from pathlib import Path

BASE_URL = "https://myq.utb.cz"
LOGIN_PATH = "/cs/"
APP_PATH = "/cs/app/"

_USER_AGENT = "Mozilla/5.0 (BPDPManager MyQ print)"
_DEFAULT_TIMEOUT = 30.0

# ── WSF konstanty zachycené z HAR (doladit, kdyby MyQ změnilo UI) ──────────────
# Přihlášení (POST /cs/): formulář i jeho control ID se mezi sezeními LIŠÍ,
# proto je nehardcodujeme — parsujeme živý formulář (viz _parse_login_form).
# Jediné stabilní je CSS třída přihlašovacího formuláře a názvy polí user/pwd.
_LOGIN_FORM_CLASS = "Web_Login_FormLogin"
_LOGIN_OBJECT_FALLBACK = "C3"       # když se id formuláře nepodaří najít
# Tisk (POST /cs/app/):
_TAB_OBJECT = "C2"                   # createTabCtrl
_PRINT_OBJECT = "C68"               # onPrintFile (tlačítko „Tisk souboru")
_DIALOG_OBJECT = "C96"              # onOK (potvrzení nahrávacího dialogu)
_REFRESH_OBJECT = "C47"            # refresh fronty po odeslání
_FILE_FIELD = "C99"                # multipart pole se souborem
_SETTINGS_CTRL = "C103"           # control nastavení tisku (selId v ctrlsState)
_SETTINGS_SELID = "*1"
# Hodnoty polí nastavení tisku z dialogu — zachycené pro „oboustranně".
# Pozn.: MyQ serializuje hodnoty jako JSON řetězce, proto i uvozovky.
_PRINT_SETTINGS: dict[str, str] = {
    "C100": '"0"',
    "C102": '"0"',
    "C103": '"1"',
    "C104": '"0"',
    "C105": '"0"',
}


class MyQError(Exception):
    """Chyba při komunikaci s MyQ (síť, neočekávaná odpověď)."""


class MyQAuthError(MyQError):
    """Přihlášení do MyQ se nezdařilo (špatné jméno/PIN, vypršelá session)."""


class MyQClient:
    """Drží jednu přihlášenou MyQ session (cookies + ``wsfHashId``)."""

    def __init__(
        self, timeout: float = _DEFAULT_TIMEOUT, *, verify_tls: bool = True
    ) -> None:
        self.timeout = timeout
        self.verify_tls = verify_tls
        self._cookies = CookieJar()
        ctx = ssl.create_default_context()
        if not verify_tls:
            # Interní MyQ server může posílat neúplný řetězec / mít interní CA,
            # kterou má jen keychain prohlížeče (ne Python). Na vědomé přání
            # uživatele ověření vypneme (jen pro tento interní, důvěryhodný host).
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._cookies),
            urllib.request.HTTPSHandler(context=ctx),
        )
        self._hash_id: str | None = None
        self._instance_id: str = ""
        self._req_id = 0
        self._app_ready = False

    # ── nízkoúrovňové HTTP ────────────────────────────────────────────────
    def _open(
        self,
        path: str,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
        *,
        decode: bool = True,
    ) -> str:
        url = path if path.startswith("http") else BASE_URL + path
        h = {"User-Agent": _USER_AGENT, "Accept": "*/*"}
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, data=data, headers=h)
        try:
            with self._opener.open(req, timeout=self.timeout) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            raise MyQError(f"MyQ odpověděl chybou HTTP {exc.code}.") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise MyQError(self._connect_error_message(exc)) from exc
        return raw.decode("utf-8", "replace") if decode else raw

    @staticmethod
    def _connect_error_message(exc: Exception) -> str:
        """Lidsky čitelná diagnostika selhání spojení s MyQ.

        MyQ (`myq.utb.cz`) běží na **vnitřní univerzitní síti** (privátní IP).
        Mimo ni se jméno sice přeloží, ale na server se nelze připojit —
        proto zdůrazňujeme síť/VPN, ne „internet".
        """
        reason = getattr(exc, "reason", exc)
        net_hint = (
            "MyQ je dostupné jen z univerzitní sítě (myq.utb.cz má interní "
            "adresu). Připoj se na fakultní síť nebo univerzitní VPN a zkus "
            "to znovu."
        )
        if isinstance(reason, ssl.SSLError):
            return (
                f"Selhalo ověření TLS certifikátu MyQ ({reason}). "
                "MyQ server posílá certifikát, který Python neumí ověřit "
                "(neúplný řetězec / interní univerzitní CA). V dialogu odznač "
                "„Ověřit TLS certifikát serveru“ a zkus to znovu."
            )
        if isinstance(reason, socket.gaierror):
            return (
                "Název myq.utb.cz nejde přeložit (DNS). " + net_hint
            )
        if isinstance(reason, TimeoutError) or isinstance(exc, TimeoutError):
            return "MyQ (myq.utb.cz) neodpovídá — spojení vypršelo. " + net_hint
        return f"Nepodařilo se spojit s MyQ (myq.utb.cz): {reason}. " + net_hint

    def _post_form(self, path: str, fields: dict[str, str]) -> str:
        data = urllib.parse.urlencode(fields, encoding="utf-8").encode()
        return self._open(
            path,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
            },
        )

    @staticmethod
    def _parse_tokens(html: str) -> tuple[str | None, str]:
        """Vytáhne ``wsfHashId`` (skryté pole) a ``instanceID`` (JS bootstrap)."""
        hash_id = None
        m = re.search(r'name="wsfHashId"\s+value="([0-9a-fA-F]+)"', html)
        if m:
            hash_id = m.group(1)
        instance = ""
        m = re.search(r'"instanceID"\s*:\s*"([^"]+)"', html)
        if m:
            instance = m.group(1)
        return hash_id, instance

    @staticmethod
    def _is_logged_in(html: str) -> bool:
        return "Odhlásit" in html or "FormLogout" in html

    @staticmethod
    def _parse_login_form(html: str) -> dict:
        """Rozparsuje živý přihlašovací formulář MyQ.

        Vrací: ``fields`` (název → výchozí hodnota všech <input> krom wsfState),
        ``user`` (name, control_id) pole jména, ``pin`` (name, control_id) pole
        hesla/PINu, ``form_ctrl`` id formuláře. Control ID i názvy čteme z živé
        stránky, protože se mezi sezeními liší.
        """
        fields: dict[str, str] = {}
        user_field: tuple[str, str] | None = None
        pin_field: tuple[str, str] | None = None
        for m in re.finditer(r"<input\b[^>]*>", html):
            tag = m.group(0)
            name_m = re.search(r'name="([^"]*)"', tag)
            if not name_m:
                continue
            name = name_m.group(1)
            if name == "wsfState":
                continue  # plníme zvlášť (JSON stav)
            value = (re.search(r'value="([^"]*)"', tag) or (None, ""))[1]
            typ = (re.search(r'type="([^"]*)"', tag) or (None, "text"))[1]
            idv = (re.search(r'id="([^"]*)"', tag) or (None, ""))[1]
            ctrl = idv[:-5] if idv.endswith("input") else ""
            fields[name] = value
            if typ == "password" and pin_field is None:
                pin_field = (name, ctrl)
            elif typ == "text" and name == "user":
                user_field = (name, ctrl)
        # fallback: jméno = první textové pole, které není „domain"/heslo
        if user_field is None:
            for m in re.finditer(r"<input\b[^>]*>", html):
                tag = m.group(0)
                name_m = re.search(r'name="([^"]*)"', tag)
                typ = (re.search(r'type="([^"]*)"', tag) or (None, "text"))[1]
                if name_m and typ == "text" and name_m.group(1) not in ("domain",):
                    idv = (re.search(r'id="([^"]*)"', tag) or (None, ""))[1]
                    user_field = (name_m.group(1),
                                  idv[:-5] if idv.endswith("input") else "")
                    break
        form_m = re.search(
            r'id="(C\d+)"[^>]*\b' + re.escape(_LOGIN_FORM_CLASS), html
        )
        return {
            "fields": fields,
            "user": user_field,
            "pin": pin_field,
            "form_ctrl": form_m.group(1) if form_m else _LOGIN_OBJECT_FALLBACK,
        }

    # ── veřejné API ───────────────────────────────────────────────────────
    def login(self, username: str, pin: str) -> None:
        """Přihlásí se do MyQ jménem + PINem. Údaje se nikam neukládají."""
        username = (username or "").strip()
        pin = (pin or "").strip()
        if not username or not pin:
            raise MyQAuthError("Zadej přihlašovací jméno i PIN.")

        page = self._open(LOGIN_PATH)
        # Už přihlášen (živá session)? Pak login přeskočíme.
        if self._is_logged_in(page):
            self._load_app()
            return

        hash_id, instance = self._parse_tokens(page)
        form = self._parse_login_form(page)
        if not hash_id or form["user"] is None or form["pin"] is None:
            raise MyQError(
                "Nepodařilo se rozpoznat přihlašovací formulář MyQ "
                "(změna stránky?). Zkus to znovu, případně se přihlas ručně "
                "přes web."
            )
        user_name, user_ctrl = form["user"]
        pin_name, pin_ctrl = form["pin"]

        # Stav formuláře: vyplníme jen jméno + PIN do jejich controlů.
        ctrls: dict[str, dict] = {"C1": {"_focusedCtrl": pin_ctrl}}
        if user_ctrl:
            ctrls[user_ctrl] = {"modified": True, "value": username}
        if pin_ctrl:
            ctrls[pin_ctrl] = {"modified": True, "value": pin}
        wsf = {
            "async": True, "hash": {}, "object": form["form_ctrl"],
            "method": "onLogin", "params": {}, "ctrlsState": ctrls,
            "deletedServerCtrls": [], "requestID": 0, "instanceID": instance,
        }

        # POST: wsfState + wsfHashId + pojmenovaná pole formuláře
        # (user/pwd přepsaná, ostatní — domain apod. — ve svém defaultu).
        post_fields = dict(form["fields"])
        post_fields[user_name] = username
        post_fields[pin_name] = pin
        post_fields["wsfState"] = json.dumps(wsf, ensure_ascii=False)
        post_fields["wsfHashId"] = hash_id
        self._post_form(LOGIN_PATH, post_fields)

        # Ověření: dashboard musí ukazovat odhlášení (= jsme přihlášení).
        app = self._open(APP_PATH)
        if not self._is_logged_in(app):
            raise MyQAuthError(
                "Přihlášení do MyQ se nezdařilo — zkontroluj jméno a PIN."
            )
        self._apply_app_page(app)

    def _load_app(self) -> None:
        self._apply_app_page(self._open(APP_PATH))

    def _apply_app_page(self, app_html: str) -> None:
        self._hash_id, self._instance_id = self._parse_tokens(app_html)
        if not self._hash_id:
            raise MyQError("MyQ nevrátil očekávanou stránku aplikace.")
        self._req_id = 0
        self._app_ready = False

    def _wsf_post(self, wsf: dict) -> str:
        return self._post_form(
            APP_PATH,
            {
                "wsfState": json.dumps(wsf, ensure_ascii=False),
                "wsfHashId": self._hash_id or "",
            },
        )

    def _next_req(self) -> int:
        rid = self._req_id
        self._req_id += 1
        return rid

    def _ensure_jobs_tab(self) -> None:
        """Otevře frontu úloh (jednou za session) — tam je tlačítko Tisk."""
        if self._app_ready:
            return
        self._wsf_post({
            "async": True, "hash": {"r": "dashboard"}, "object": _TAB_OBJECT,
            "method": "createTabCtrl", "params": ["*dashboard", {}],
            "ctrlsState": {"C2": {"defaultPageRef": "*dashboard"}},
            "deletedServerCtrls": [], "requestID": self._next_req(),
            "instanceID": self._instance_id,
        })
        self._wsf_post({
            "async": True, "hash": {"r": "jobs"}, "object": _TAB_OBJECT,
            "method": "createTabCtrl", "params": ["*jobs", {}],
            "ctrlsState": {"C1": {"_focusedCtrl": None}},
            "deletedServerCtrls": [], "requestID": self._next_req(),
            "instanceID": self._instance_id,
        })
        self._app_ready = True

    def upload(self, pdf_path: str | Path) -> None:
        """Nahraje jedno PDF do tiskové fronty (nastavení: oboustranně)."""
        if self._hash_id is None:
            raise MyQError("Nejdřív se přihlas (login).")
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise MyQError(f"Soubor neexistuje: {pdf_path}")

        self._ensure_jobs_tab()

        # ② otevři nahrávací dialog
        self._wsf_post({
            "async": True, "hash": {"r": "jobs"}, "object": _PRINT_OBJECT,
            "method": "onPrintFile", "params": {}, "ctrlsState": {},
            "deletedServerCtrls": [], "requestID": self._next_req(),
            "instanceID": self._instance_id,
        })

        # ③ potvrď dialog s nahraným souborem + nastavením tisku (multipart)
        wsf = {
            "async": True, "hash": {"r": "jobs"}, "object": _DIALOG_OBJECT,
            "method": "onOK", "params": [],
            "ctrlsState": {_SETTINGS_CTRL: {"selId": _SETTINGS_SELID}},
            "deletedServerCtrls": [], "requestID": self._next_req(),
            "instanceID": self._instance_id,
        }
        resp = self._post_multipart(wsf, pdf_path)
        # Úspěch MyQ hlásí bublinou „Operace běží na pozadí".
        if "pozad" not in resp and "bubbleMsg" not in resp.lower():
            raise MyQError(
                "MyQ nepotvrdil přijetí úlohy k tisku (neočekávaná odpověď). "
                "Zkontroluj frontu úloh přímo na webu MyQ."
            )

        # Obnov frontu (jako web po odeslání) — drží stav konzistentní.
        try:
            self._wsf_post({
                "async": True, "hash": {"r": "jobs"}, "object": _REFRESH_OBJECT,
                "method": "refresh", "params": {}, "ctrlsState": {},
                "deletedServerCtrls": [], "requestID": self._next_req(),
                "instanceID": self._instance_id,
            })
        except MyQError:
            pass  # refresh je kosmetický; úloha už je odeslaná

    def _post_multipart(self, wsf: dict, pdf_path: Path) -> str:
        boundary = "----BPDPManager" + uuid.uuid4().hex
        crlf = b"\r\n"
        parts: list[bytes] = []

        def add(name: str, value: bytes, *, filename: str | None = None,
                ctype: str | None = None) -> None:
            disp = f'form-data; name="{name}"'
            if filename is not None:
                disp += f'; filename="{filename}"'
            head = f"--{boundary}\r\nContent-Disposition: {disp}\r\n"
            if ctype:
                head += f"Content-Type: {ctype}\r\n"
            head += "\r\n"
            parts.append(head.encode("utf-8"))
            parts.append(value)
            parts.append(crlf)

        add("wsfState", json.dumps(wsf, ensure_ascii=False).encode("utf-8"))
        add("wsfHashId", (self._hash_id or "").encode("utf-8"))
        add(_FILE_FIELD, pdf_path.read_bytes(),
            filename=pdf_path.name, ctype="application/pdf")
        for name, value in _PRINT_SETTINGS.items():
            add(name, value.encode("utf-8"))
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)

        return self._open(
            APP_PATH,
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
