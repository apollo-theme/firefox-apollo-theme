#!/usr/bin/env python3
"""Validate the palette snapshot and generated Firefox adapter."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

import generate
from common import (
    ACCENT_ROLES,
    DARK_VARIANT,
    ROOT,
    TEXT_BACKGROUNDS,
    VARIANTS,
    VariantSpec,
    contrast_ratio,
    load_json,
    load_palette,
    palette_sha256,
)

HEX_COLOR = re.compile(r"^#[0-9a-f]{6}$")


def validate_role_coverage(
    color_roles: tuple[tuple[str, str], ...],
    text_backgrounds: dict[str, str],
    accent_roles: tuple[str, ...],
) -> list[str]:
    """Require validation metadata for every mapped text and accent role."""
    errors: list[str] = []
    mappings = dict(color_roles)

    for role in mappings:
        if "text" in role.split("_") and role not in text_backgrounds:
            errors.append(f"{role} has no declared text background")
    for role, palette_role in color_roles:
        if palette_role == "accent" and role not in accent_roles:
            errors.append(f"{role} maps accent but is not checked as an accent role")

    for text_role, background_role in text_backgrounds.items():
        if text_role not in mappings:
            errors.append(f"{text_role} declares a text background but is not generated")
        if background_role not in mappings:
            errors.append(f"{text_role} references unknown background {background_role}")
    for role in accent_roles:
        if mappings.get(role) != "accent":
            errors.append(f"{role} is checked as accent but does not map accent")

    return errors


def validate_variant(variant: VariantSpec = DARK_VARIANT) -> list[str]:
    """Return deterministic validation failures for one theme variant."""
    errors = validate_role_coverage(
        variant.color_roles,
        TEXT_BACKGROUNDS,
        ACCENT_ROLES,
    )
    palette = load_palette(variant)
    manifest = load_json(variant.manifest_path)
    colors: dict[str, str] = manifest["theme"]["colors"]
    prefix = f"{variant.key}: "

    digest = palette_sha256(variant)
    if digest != variant.expected_palette_sha256:
        errors.append(
            f"{prefix}palette snapshot hash is {digest}, expected {variant.expected_palette_sha256}"
        )
    source_digest = palette["provenance"].get("sourceSha256")
    if source_digest != variant.expected_source_sha256:
        errors.append(
            f"{prefix}palette source hash is {source_digest}, expected {variant.expected_source_sha256}"
        )

    expected_manifest = generate.render_manifest(generate.build_manifest(variant))
    actual_manifest = variant.manifest_path.read_text(encoding="utf-8")
    if actual_manifest != expected_manifest:
        errors.append(
            f"{prefix}{variant.manifest_path.relative_to(ROOT)} "
            "differs from deterministic generated output"
        )

    palette_colors = set(palette["colors"].values())
    for role, color in colors.items():
        if not HEX_COLOR.fullmatch(color):
            errors.append(
                f"{prefix}{role} is not a lowercase six-digit hex color: {color}"
            )
        if color not in palette_colors:
            errors.append(
                f"{prefix}{role} uses a color outside the Apollo palette: {color}"
            )

    minimum = float(palette["constraints"]["minimumTextContrast"])
    restricted = set(palette["constraints"]["restrictedColors"])
    for text_role, background_role in TEXT_BACKGROUNDS.items():
        foreground = colors[text_role]
        background = colors[background_role]
        ratio = contrast_ratio(foreground, background)
        if ratio < minimum:
            errors.append(
                f"{prefix}{text_role} contrast on {background_role} is "
                f"{ratio:.2f}, below {minimum:.2f}"
            )
        if foreground in restricted:
            errors.append(
                f"{prefix}{text_role} uses restricted text color {foreground}"
            )

    accent = palette["colors"]["accent"]
    for role in ACCENT_ROLES:
        if colors[role] != accent:
            errors.append(
                f"{prefix}{role} must use accent {accent}, found {colors[role]}"
            )

    return errors


def validate() -> list[str]:
    """Return deterministic validation failures for every theme variant."""
    return [error for variant in VARIANTS for error in validate_variant(variant)]


def main() -> int:
    try:
        errors = validate()
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"check failed: {error}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    for variant in VARIANTS:
        print(f"valid: {variant.palette_path.relative_to(ROOT)}")
        print(f"valid: {variant.manifest_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
