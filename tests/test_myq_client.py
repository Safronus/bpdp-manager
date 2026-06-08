"""MyQ konektor — sestavení požadavků (login + upload) s mockovanou sítí.

Reálný server netestujeme (interní, vyžaduje přihlášení); ověřujeme, že klient
skládá požadavky ve tvaru zachyceném z reálného provozu (HAR) a že přihlašovací
údaje nikam neukládá.
"""

from __future__ import annotations

import json
import re
import urllib.parse as up
from pathlib import Path

import pytest

from bpdpmanager.services.myq_client import (
    _FILE_FIELD,
    _PRINT_SETTINGS,
    MyQAuthError,
    MyQClient,
    MyQError,
)

_LOGIN_PAGE = (
    '<html><body class="Web_ViewLogin"><form id="wsfForm" method="post">'
    '<input type="hidden" name="wsfState" id="wsfState"/>'
    '<input type="hidden" name="wsfHashId" '
    'value="abc123abc123abc123abc123abc12300" id="wsfHashId"/>'
    '<script>g_app(0,{"requestID":0,"instanceID":"wsfLOGIN1"});</script>'
    '<div id="C12" class="wsfBtnTabs wsfCtrl Wsf_Ctrls_Menu_CtrlMenu"></div>'
    '<div id="C3" class="wsfCtrl Wsf_Forms_CtrlForm Web_Login_FormLogin">'
    '<select name="C6" id="C6" class="wsfCtrl Wsf_Forms_CtrlComboBox">'
    '<option value="&quot;en&quot;">English</option>'
    '<option value="&quot;cs&quot;" selected="selected">Čeština</option>'
    "</select>"
    '<input name="domain" type="text" id="C7input" value=""/>'
    '<input name="user" type="text" id="C8input" value=""/>'
    '<input name="pwd" type="password" id="C9input" value=""/>'
    "</div></form></body></html>"
)
_APP_PAGE = (
    '<html><input type="hidden" name="wsfHashId" '
    'value="ffff1111ffff1111ffff1111ffff1111" id="wsfHashId"/>'
    '<script>g_app(0,{"requestID":0,"instanceID":"wsfAPP1"});</script>'
    '<li class="wsfFormLogoutUserName">Testovací Uživatel</li>'
    '<button>Odhlásit</button></html>'
)


class _FakeNet:
    """Zachytává volání ``_open`` a vrací předem připravené odpovědi."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def __call__(self, path, data=None, headers=None, *, decode=True):
        self.calls.append({"path": path, "data": data, "headers": headers or {}})
        return self.responses.pop(0) if self.responses else ""


def _login(client: MyQClient, net: _FakeNet) -> None:
    client._open = net
    client.login("zacek", "123456")


def test_login_empty_credentials_raises() -> None:
    c = MyQClient()
    with pytest.raises(MyQAuthError):
        c.login("", "123456")
    with pytest.raises(MyQAuthError):
        c.login("zacek", "  ")


def test_login_posts_onlogin_and_credentials_not_stored() -> None:
    c = MyQClient()
    net = _FakeNet([_LOGIN_PAGE, "", _APP_PAGE])  # GET /cs/, POST /cs/, GET /cs/app/
    _login(c, net)

    # 3 volání: GET login, POST login, GET app
    assert [x["path"] for x in net.calls] == ["/cs/", "/cs/", "/cs/app/"]
    post = net.calls[1]
    fields = dict(
        kv.split("=", 1) for kv in post["data"].decode().split("&")
    )
    assert "wsfState" in fields and "wsfHashId" in fields
    # PIN se posílá jako pojmenované pole, jazyk taky; jméno NE (jen ve wsfState)
    assert up.unquote_plus(fields["pwd"]) == "123456"
    assert up.unquote_plus(fields["C6"]) == '"cs"'  # combobox jazyk
    assert "user" not in fields and "domain" not in fields
    wsf = json.loads(up.unquote_plus(fields["wsfState"]))
    assert wsf["method"] == "onLogin"
    assert wsf["object"] == "C3"  # id formuláře z živé stránky
    # credentials v ctrlsState — řetězcové hodnoty MUSÍ mít prefix „*"
    # (WSF jinak bere řetězec jako ID controlu, ne jako literál).
    assert wsf["ctrlsState"]["C8"]["value"] == "*zacek"
    assert wsf["ctrlsState"]["C9"]["value"] == "*123456"
    assert wsf["ctrlsState"]["C12"]["selIDs"] == ["Web_Login_FormLogin"]

    # po přihlášení se vezme wsfHashId z app stránky
    assert c._hash_id == "ffff1111ffff1111ffff1111ffff1111"
    assert c._instance_id == "wsfAPP1"

    # klient si neukládá jméno ani PIN do atributů
    state = " ".join(str(v) for v in vars(c).values())
    assert "zacek" not in state and "123456" not in state


def test_parse_login_form() -> None:
    form = MyQClient._parse_login_form(_LOGIN_PAGE)
    assert form["user"] == ("user", "C8")
    assert form["pin"] == ("pwd", "C9")
    assert form["form_ctrl"] == "C3"
    assert form["tab_ctrl"] == "C12"          # záložkové menu (login/PIN reset)
    assert form["combo"] == ("C6", '"cs"')    # jazyk, vybraná čeština


def test_login_already_logged_in_skips_post() -> None:
    c = MyQClient()
    # GET /cs/ už vrací přihlášenou stránku → žádný onLogin POST, jen načti app
    net = _FakeNet([_APP_PAGE, _APP_PAGE])
    _login(c, net)
    assert [x["path"] for x in net.calls] == ["/cs/", "/cs/app/"]
    assert c._hash_id == "ffff1111ffff1111ffff1111ffff1111"


def test_login_wrong_credentials_raises() -> None:
    c = MyQClient()
    # po POSTu app stránka NEobsahuje „Odhlásit" → špatné přihlášení
    net = _FakeNet([_LOGIN_PAGE, "", "<html>přihlášení selhalo</html>"])
    c._open = net
    with pytest.raises(MyQAuthError):
        c.login("zacek", "000000")


def test_upload_sequence_and_multipart(tmp_path: Path) -> None:
    c = MyQClient()
    _login(c, _FakeNet([_LOGIN_PAGE, "", _APP_PAGE]))

    pdf = tmp_path / "Novák_posudek.pdf"
    pdf.write_bytes(b"%PDF-1.7 test")

    # upload: dashboard, jobs, onPrintFile, onOK(multipart), refresh = 5 volání
    net = _FakeNet(["{}", "{}", "{}", '{"bubbleMsgs":[{"html":"Operace běží na pozadí"}]}', "{}"])
    c._open = net
    c.upload(pdf)

    assert [x["path"] for x in net.calls] == ["/cs/app/"] * 5
    # poslední-ale-jedna je multipart se souborem
    methods = []
    for call in net.calls:
        data = call["data"]
        ct = call["headers"].get("Content-Type", "")
        if "multipart" in ct:
            body = data.decode("utf-8", "replace")
            parts = re.findall(r'name="([^"]+)"(?:; filename="([^"]+)")?', body)
            assert (_FILE_FIELD, pdf.name) in parts
            for k in _PRINT_SETTINGS:
                assert (k, "") in parts
            methods.append("multipart")
        else:
            wsf = json.loads(up.parse_qs(data.decode())["wsfState"][0])
            methods.append(wsf["method"])
    assert methods == ["createTabCtrl", "createTabCtrl", "onPrintFile",
                       "multipart", "refresh"]


def test_upload_threads_rotating_token(tmp_path: Path) -> None:
    """WSF rotuje token: každý další request musí použít requestHash/requestID
    z předchozí odpovědi (jinak 400 „request expired")."""
    c = MyQClient()
    _login(c, _FakeNet([_LOGIN_PAGE, "", _APP_PAGE]))
    # po loginu má klient hash z app stránky
    assert c._hash_id == "ffff1111ffff1111ffff1111ffff1111"
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF")
    net = _FakeNet([
        '{"requestID":1,"requestHash":"H1"}',
        '{"requestID":2,"requestHash":"H2"}',
        '{"requestID":3,"requestHash":"H3"}',
        '{"requestID":4,"requestHash":"H4","bubbleMsgs":[{"html":"pozadí"}]}',
        '{"requestID":5,"requestHash":"H5"}',
    ])
    c._open = net
    c.upload(pdf)

    # wsfHashId poslaný v jednotlivých requestech = hash z PŘEDCHOZÍ odpovědi
    sent_hashes = []
    for call in net.calls:
        data = call["data"]
        if "multipart" in call["headers"].get("Content-Type", ""):
            seg = data.split(b'name="wsfHashId"')[1].split(b"\r\n\r\n")[1]
            sent_hashes.append(seg.split(b"\r\n")[0].decode())
        else:
            sent_hashes.append(up.parse_qs(data.decode())["wsfHashId"][0])
    assert sent_hashes == [
        "ffff1111ffff1111ffff1111ffff1111", "H1", "H2", "H3", "H4"
    ]


def test_upload_unexpected_response_raises(tmp_path: Path) -> None:
    c = MyQClient()
    _login(c, _FakeNet([_LOGIN_PAGE, "", _APP_PAGE]))
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF")
    # onOK vrátí odpověď bez potvrzení → chyba
    net = _FakeNet(["{}", "{}", "{}", '{"error":"neco"}', "{}"])
    c._open = net
    with pytest.raises(MyQError):
        c.upload(pdf)


def test_upload_without_login_raises(tmp_path: Path) -> None:
    c = MyQClient()
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF")
    with pytest.raises(MyQError):
        c.upload(pdf)


def test_upload_missing_file_raises() -> None:
    c = MyQClient()
    _login(c, _FakeNet([_LOGIN_PAGE, "", _APP_PAGE]))
    with pytest.raises(MyQError):
        c.upload("/does/not/exist.pdf")


def test_verify_tls_toggle() -> None:
    import ssl

    def ctx(client):
        return next(h._context for h in client._opener.handlers
                    if hasattr(h, "_context"))

    secure = ctx(MyQClient(verify_tls=True))
    assert secure.verify_mode == ssl.CERT_REQUIRED and secure.check_hostname
    insecure = ctx(MyQClient(verify_tls=False))
    assert insecure.verify_mode == ssl.CERT_NONE and not insecure.check_hostname


def test_connect_error_messages() -> None:
    import socket
    import ssl
    import urllib.error

    msg = MyQClient._connect_error_message
    # timeout / DNS → zdůrazní univerzitní síť / VPN (MyQ je interní)
    assert "VPN" in msg(urllib.error.URLError(TimeoutError("t")))
    assert "vypršelo" in msg(urllib.error.URLError(TimeoutError("t")))
    assert "DNS" in msg(urllib.error.URLError(socket.gaierror(8, "x")))
    assert "VPN" in msg(urllib.error.URLError(socket.gaierror(8, "x")))
    # TLS chyba se hlásí samostatně (není to o síti)
    assert "TLS" in msg(urllib.error.URLError(ssl.SSLError("CERT")))
