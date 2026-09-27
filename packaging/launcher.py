"""Vstupní skript zabalené aplikace (PyInstaller).

``bpdpmanager/__main__.py`` používá relativní importy, takže ho PyInstaller
nemůže spustit přímo jako top-level skript — tenhle launcher ho jen importuje
jako součást balíčku a předá návratový kód.
"""

import sys

from bpdpmanager.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
