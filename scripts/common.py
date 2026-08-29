"""Shared constants and validation helpers for the Firefox adapter."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "package.json"

# Ordered for stable generated JSON and grouped by Firefox chrome region.
DARK_COLOR_ROLES = (
    ("frame", "background"),
    ("frame_inactive", "background"),
    ("tab_background_text", "foregroundInactive"),
    ("tab_selected", "surface"),
    ("tab_text", "foreground"),
    ("tab_line", "accent"),
    ("tab_loading", "accent"),
    ("tab_background_separator", "selection"),
    ("toolbar", "surface"),
    ("toolbar_text", "foreground"),
    ("toolbar_field", "background"),
    ("toolbar_field_text", "foreground"),
    ("toolbar_field_focus", "surface"),
    ("toolbar_field_text_focus", "foregroundSecondary"),
    ("toolbar_field_border_focus", "accent"),
    ("toolbar_field_separator", "selection"),
    ("toolbar_vertical_separator", "selection"),
    ("toolbar_field_highlight", "selection"),
    ("toolbar_field_highlight_text", "foregroundSecondary"),
    ("button_background_hover", "selection"),
    ("button_background_active", "ansiBrightBlack"),
    ("icons", "foreground"),
    ("icons_attention", "accent"),
    ("ntp_background", "background"),
    ("ntp_text", "foreground"),
    ("popup", "surface"),
    ("popup_border", "selection"),
    ("popup_highlight", "selection"),
    ("popup_highlight_text", "foregroundSecondary"),
    ("popup_text", "foreground"),
    ("sidebar", "surface"),
    ("sidebar_border", "selection"),
    ("sidebar_highlight", "selection"),
    ("sidebar_highlight_text", "foregroundSecondary"),
    ("sidebar_text", "foreground"),
    ("bookmark_text", "foreground"),
)
LIGHT_COLOR_ROLES = tuple(
    (role, "surfaceHover" if role == "button_background_active" else palette_role)
    for role, palette_role in DARK_COLOR_ROLES
)


@dataclass(frozen=True)
class VariantSpec:
    """Stable identity, paths, and role mapping for one Firefox theme variant."""

    key: str
    palette_path: Path
    manifest_path: Path
    theme_name: str
    description: str
    gecko_id: str
    expected_palette_sha256: str
    expected_source_sha256: str
    color_roles: tuple[tuple[str, str], ...]


DARK_VARIANT = VariantSpec(
    key="dark",
    palette_path=ROOT / "palette" / "apollo.json",
    manifest_path=ROOT / "manifest.json",
    theme_name="Firefox Apollo Theme",
    description="A high-contrast Firefox theme generated from the canonical Apollo palette.",
    gecko_id="humble-apollo@d0n9x1n",
    expected_palette_sha256="550f8c36cf4ef6ac99551541d1fe9554f77d563fa1e7c129a6a82583321d61ef",
    expected_source_sha256="0ed79939b82134b14ea3e339ebabee1f22ee5d12bb80915b0a407b5affb5f5ac",
    color_roles=DARK_COLOR_ROLES,
)
LIGHT_VARIANT = VariantSpec(
    key="light",
    palette_path=ROOT / "palette" / "apollo-light.json",
    manifest_path=ROOT / "variants" / "light" / "manifest.json",
    theme_name="Firefox Apollo Light Theme",
    description="A high-contrast light Firefox theme generated from the canonical Apollo Light palette.",
    gecko_id="apollo-light@d0n9x1n",
    expected_palette_sha256="b0dbdeb719ed1931c424e9590562689325ecac1609e2fed6406ec5c4d3dc5763",
    expected_source_sha256="55116926ba2b625837d9ae89349a5688d60d0b32acdbd8887e1c0d225f079c3d",
    color_roles=LIGHT_COLOR_ROLES,
)
VARIANTS = (DARK_VARIANT, LIGHT_VARIANT)

# Dark aliases retain the original adapter API and defaults.
PALETTE_PATH = DARK_VARIANT.palette_path
MANIFEST_PATH = DARK_VARIANT.manifest_path
EXPECTED_PALETTE_SHA256 = DARK_VARIANT.expected_palette_sha256
EXPECTED_SOURCE_SHA256 = DARK_VARIANT.expected_source_sha256
THEME_NAME = DARK_VARIANT.theme_name
DESCRIPTION = DARK_VARIANT.description
GECKO_ID = DARK_VARIANT.gecko_id
COLOR_ROLES = DARK_VARIANT.color_roles

TEXT_BACKGROUNDS = {
    "tab_background_text": "frame",
    "tab_text": "tab_selected",
    "toolbar_text": "toolbar",
    "toolbar_field_text": "toolbar_field",
    "toolbar_field_text_focus": "toolbar_field_focus",
    "toolbar_field_highlight_text": "toolbar_field_highlight",
    "ntp_text": "ntp_background",
    "popup_highlight_text": "popup_highlight",
    "popup_text": "popup",
    "sidebar_highlight_text": "sidebar_highlight",
    "sidebar_text": "sidebar",
    "bookmark_text": "toolbar",
}

ACCENT_ROLES = (
    "tab_line",
    "tab_loading",
    "toolbar_field_border_focus",
    "icons_attention",
)


def load_json(path: Path) -> dict[str, Any]:
    """Load a UTF-8 JSON object from *path*."""
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def load_palette(variant: VariantSpec = DARK_VARIANT) -> dict[str, Any]:
    """Load one committed Apollo palette snapshot, defaulting to dark."""
    return load_json(variant.palette_path)


def palette_sha256(variant: VariantSpec = DARK_VARIANT) -> str:
    """Return one exact snapshot SHA-256 digest, defaulting to dark."""
    return hashlib.sha256(variant.palette_path.read_bytes()).hexdigest()


def resolve_palette_roles(palette: dict[str, Any]) -> dict[str, str]:
    """Resolve role aliases and expose named colors in one lookup."""
    colors = palette["colors"]
    resolved = dict(colors)
    for role, reference in palette["roles"].items():
        prefix = "{colors."
        if not reference.startswith(prefix) or not reference.endswith("}"):
            raise ValueError(f"unsupported palette reference for {role}: {reference}")
        resolved[role] = colors[reference[len(prefix) : -1]]
    return resolved


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    """Return the WCAG contrast ratio for two opaque sRGB hex colors."""
    lighter, darker = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)
