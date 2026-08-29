#!/usr/bin/env python3
"""Generate both Firefox theme manifests deterministically from Apollo snapshots."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from common import (
    DARK_VARIANT,
    PACKAGE_PATH,
    ROOT,
    VARIANTS,
    VariantSpec,
    load_json,
    load_palette,
    resolve_palette_roles,
)


def build_manifest(variant: VariantSpec = DARK_VARIANT) -> dict[str, Any]:
    """Build one complete static Manifest V2 theme object."""
    package = load_json(PACKAGE_PATH)
    palette = load_palette(variant)
    roles = resolve_palette_roles(palette)
    colors = {
        firefox_role: roles[palette_role]
        for firefox_role, palette_role in variant.color_roles
    }
    return {
        "manifest_version": 2,
        "version": package["version"],
        "name": variant.theme_name,
        "description": variant.description,
        "browser_specific_settings": {
            "gecko": {
                "id": variant.gecko_id,
                "data_collection_permissions": {"required": ["none"]},
            }
        },
        "theme": {"colors": colors},
    }


def render_manifest(manifest: dict[str, Any]) -> str:
    """Serialize a manifest with stable indentation and a trailing newline."""
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def check_manifest(
    expected: str,
    variant: VariantSpec = DARK_VARIANT,
) -> int:
    """Return non-zero if one committed manifest differs from generated output."""
    path = variant.manifest_path
    actual = path.read_text(encoding="utf-8") if path.exists() else ""
    relative = path.relative_to(ROOT)
    if actual != expected:
        print(
            f"{relative} is out of date; run python3 scripts/generate.py",
            file=sys.stderr,
        )
        return 1
    print(f"{relative} is up to date")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify both manifests without writing them",
    )
    args = parser.parse_args()
    status = 0
    for variant in VARIANTS:
        rendered = render_manifest(build_manifest(variant))
        if args.check:
            status |= check_manifest(rendered, variant)
            continue
        variant.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        variant.manifest_path.write_text(rendered, encoding="utf-8", newline="\n")
        print(f"wrote {variant.manifest_path.relative_to(ROOT)}")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
