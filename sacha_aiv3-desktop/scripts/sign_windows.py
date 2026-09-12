"""
scripts/sign_windows.py — code-sign the .exe (Windows).

Expects signtool on PATH or SIGNOOL_PATH / SIGNTOOL_PATH env. Runs a dry
check by default; pass --exec to actually sign.

    python scripts/sign_windows.py            # checks
    python scripts/sign_windows.py --exec     # signs dist/SACHA_V3/*.exe
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _find_signtool() -> str | None:
    for env in ("SIGNTOOL_PATH", "SIGNOOL_PATH"):
        found = os.environ.get(env)
        if found:
            return found
    try:
        return shutil.which("signtool")
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Sign SACHA_V3 Windows binaries")
    parser.add_argument("--exec", action="store_true", help="actually sign (default: check only)")
    parser.add_argument("--cert", default=os.environ.get("SIGN_CERT", ""), help="certificate path")
    args = parser.parse_args()

    signtool = _find_signtool()
    if not signtool:
        print("[sign] signtool not found — install Windows SDK or set SIGNTOOL_PATH")
        return 1
    targets = [p for p in (ROOT / "dist" / "SACHA_V3").glob("*.exe")] if (ROOT / "dist" / "SACHA_V3").exists() else []
    if not targets:
        print("[sign] no built executables under dist/SACHA_V3 — run scripts/build.py first")
        return 1
    print(f"[sign] signtool: {signtool}")
    for exe in targets:
        print(f"[sign] {'signing' if args.exec else 'would sign'} {exe.name}")
        if not args.exec:
            continue
        if not args.cert:
            print("[sign] --exec requires --cert (or SIGN_CERT env)")
            return 1
        cmd = [signtool, "sign", "/f", args.cert, "/fd", "SHA256", str(exe)]
        rc = subprocess.call(cmd)
        if rc != 0:
            print(f"[sign] failed for {exe.name} (rc={rc})")
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
