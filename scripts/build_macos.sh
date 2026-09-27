#!/usr/bin/env bash
# Sestaví BPDPManager.app + .dmg pro macOS (Apple Silicon) přes PyInstaller.
#
# Kroky: PyInstaller build → ad-hoc podpis → ověření podpisu → smoke test
# zabalené aplikace (--self-test nad dočasnými daty) → DMG.
#
# Build běží MIMO repozitář (výchozí ~/.cache/bpdpmanager-build): repo leží na
# iCloud Ploše a build/ + dist/ s tisíci soubory by iCloud synchronizoval.
#
# Proměnné prostředí (volitelné):
#   PYTHON       interpret s nainstalovaným projektem (výchozí .venv/bin/python)
#   BUILD_ROOT   pracovní/cílová složka buildu (výchozí ~/.cache/bpdpmanager-build)
#
# Použití:  scripts/build_macos.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -z "${PYTHON:-}" ]]; then
    if [[ -x "$ROOT/.venv/bin/python" ]]; then
        # .venv bývá symlink mimo iCloud (~/.venvs/…). Interpret MUSÍ běžet přes
        # rozřešenou cestu: PyInstaller jinak porovná cestu balíčku PySide6
        # (přes symlink) s cestou Qt knihoven (rozřešenou), usoudí, že Qt je
        # „systémové", a vyrobí neúplný QtWebEngineCore.framework, který pak
        # nejde podepsat (codesign: „bundle format unrecognized").
        PYTHON="$(cd "$ROOT/.venv" && pwd -P)/bin/python"
    else
        PYTHON="python3"
    fi
fi
BUILD_ROOT="${BUILD_ROOT:-$HOME/.cache/bpdpmanager-build}"
DIST="$BUILD_ROOT/dist"
APP="$DIST/BPDPManager.app"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "❌ Build je jen pro macOS." >&2; exit 1
fi

VERSION="$("$PYTHON" - "$ROOT" <<'PY'
import pathlib, re, sys
src = pathlib.Path(sys.argv[1], "src", "bpdpmanager", "__init__.py").read_text(encoding="utf-8")
print(re.search(r'__version__\s*=\s*"([^"]+)"', src).group(1))
PY
)"
DMG="$DIST/BPDPManager-$VERSION-macos-arm64.dmg"

echo "▶ BPDPManager $VERSION — build do $BUILD_ROOT (Python: $("$PYTHON" -c 'import sys;print(sys.version.split()[0])'))"
mkdir -p "$BUILD_ROOT"

echo "▶ 1/5 PyInstaller…"
"$PYTHON" -m PyInstaller --noconfirm --clean --log-level WARN \
    --distpath "$DIST" --workpath "$BUILD_ROOT/work" \
    "$ROOT/packaging/bpdpmanager.spec"
[[ -d "$APP" ]] || { echo "❌ PyInstaller nevytvořil $APP" >&2; exit 1; }

echo "▶ 2/5 ad-hoc podpis…"
codesign --force --deep --sign - "$APP"

echo "▶ 3/5 ověření podpisu…"
codesign --verify --deep --strict "$APP"
# Názvy souborů v balíčku jen ASCII: Finder při přetažení do Aplikací převede
# diakritiku na NFD a podpis (počítaný nad NFC) by přestal sedět.
NON_ASCII="$(cd "$APP" && find . -name '*[! -~]*' | head -5)"
if [[ -n "$NON_ASCII" ]]; then
    echo "❌ V balíčku jsou názvy s diakritikou (Finder by rozbil podpis):" >&2
    echo "$NON_ASCII" >&2
    exit 1
fi

echo "▶ 4/5 smoke test zabalené aplikace (dočasná data)…"
SELFTEST_DATA="$(mktemp -d -t bpdp-selftest)"
QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}" BPDPMANAGER_DATA_DIR="$SELFTEST_DATA" \
    "$APP/Contents/MacOS/BPDPManager" --self-test
rm -rf "$SELFTEST_DATA"

echo "▶ 5/5 DMG…"
STAGE="$BUILD_ROOT/dmg-stage"
rm -rf "$STAGE" "$DMG"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
hdiutil create -quiet -volname "BPDPManager $VERSION" -srcfolder "$STAGE" \
    -ov -format UDZO "$DMG"
rm -rf "$STAGE"

APP_SIZE="$(du -sh "$APP" | cut -f1)"
DMG_SIZE="$(du -sh "$DMG" | cut -f1)"
echo "✅ Hotovo: $APP ($APP_SIZE)"
echo "✅ DMG:    $DMG ($DMG_SIZE)"

# Výstupy pro GitHub Actions.
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    {
        echo "version=$VERSION"
        echo "dmg=$DMG"
        echo "dmg_name=$(basename "$DMG")"
    } >> "$GITHUB_OUTPUT"
fi
