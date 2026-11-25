"""
Version string for did.

Uses :mod:`importlib.metadata` when the package is installed; falls back to
parsing ``did.spec`` in a source checkout (same scheme as ``setup.py``).
"""

from __future__ import annotations

import re
from pathlib import Path


def get_version() -> str:
    """
    Return did version (e.g. ``0.23.1``).

    Prefer the installed distribution metadata; otherwise parse ``did.spec``.
    """
    try:
        from importlib.metadata import PackageNotFoundError, version
    except ImportError:  # pragma: no cover - Python < 3.8
        from importlib_metadata import (  # type: ignore[import-not-found,no-redef]
            PackageNotFoundError,
            version,
        )

    try:
        return version("did")
    except PackageNotFoundError:
        pass

    parsed = _version_from_spec()
    return parsed if parsed is not None else "0.0.0"


def _version_from_spec() -> str | None:
    """Parse ``Version`` and numeric ``Release`` from ``did.spec`` if found."""
    here = Path(__file__).resolve().parent
    for base in [here.parent, *here.parents]:
        spec_path = base / "did.spec"
        if not spec_path.is_file():
            continue
        text = spec_path.read_text(encoding="utf-8")
        vm = re.search(r"^Version:\s*(.+)$", text, re.MULTILINE)
        rm = re.search(r"^Release:\s*(\d+)", text, re.MULTILINE)
        if not vm or not rm:
            return None
        ver = vm.group(1).strip()
        rel = rm.group(1).strip()
        return f"{ver}.{rel}"
    return None
