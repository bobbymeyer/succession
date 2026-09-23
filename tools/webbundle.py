"""Zip the `succession` package for the browser game to run under Pyodide.

    python tools/webbundle.py web/public/engine.zip

The web build calls this (web/scripts/assets.mjs), so the game in the browser
always runs the rules and bots in this checkout. Stdlib only.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "succession"


def bundle(out: Path) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in PACKAGE.rglob("*.py") if "__pycache__" not in p.parts)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            # A fixed timestamp keeps the zip byte-identical between builds.
            info = zipfile.ZipInfo(str(path.relative_to(ROOT)), date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    return len(files)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    out = Path(argv[0])
    count = bundle(out)
    print(f"wrote {count} files to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
