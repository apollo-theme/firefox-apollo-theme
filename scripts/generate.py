#!/usr/bin/env python3
"""Generate manifest.json deterministically from the Apollo snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from common import (
    COLOR_ROLES,
    DESCRIPTION,
    GECKO_ID,
    MANIFEST_PATH,
    PACKAGE_PATH,
    THEME_NAME,
    load_json,
    load_palette,
    resolve_palette_roles,
)


def build_manifest() -> dict[str, Any]:
    """Build the complete static Manifest V2 theme object."""
    package = load_json(PACKAGE_PATH)
    palette = load_palette()
    roles = resolve_palette_roles(palette)
    colors = {firefox_role: roles[palette_role] for firefox_role, palette_role in COLOR_ROLES}
    return {
        "manifest_version": 2,
        "version": package["version"],
        "name": THEME_NAME,
        "description": DESCRIPTION,
        "browser_specific_settings": {
            "gecko": {
                "id": GECKO_ID,
                "data_collection_permissions": {"required": ["none"]},
            }
        },
        "theme": {"colors": colors},
    }


def render_manifest(manifest: dict[str, Any]) -> str:
    """Serialize a manifest with stable indentation and a trailing newline."""
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def check_manifest(expected: str) -> int:
    """Return non-zero if the committed manifest differs from generated output."""
    actual = MANIFEST_PATH.read_text(encoding="utf-8") if MANIFEST_PATH.exists() else ""
    if actual != expected:
        print(
            "manifest.json is out of date; run python3 scripts/generate.py",
            file=sys.stderr,
        )
        return 1
    print("manifest.json is up to date")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify manifest.json without writing it",
    )
    args = parser.parse_args()
    rendered = render_manifest(build_manifest())
    if args.check:
        return check_manifest(rendered)
    MANIFEST_PATH.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"wrote {MANIFEST_PATH.relative_to(MANIFEST_PATH.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
