from __future__ import annotations

import pathlib
import sys


BASE_DIR = pathlib.Path(__file__).resolve().parent
APP_DIR = BASE_DIR / "CachyOS-Helper"
sys.path.insert(0, str(APP_DIR))

from cachy_helper.gui import main


if __name__ == "__main__":
    raise SystemExit(main())
