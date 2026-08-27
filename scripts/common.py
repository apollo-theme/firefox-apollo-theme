"""Shared constants and validation helpers for the Firefox adapter."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PALETTE_PATH = ROOT / "palette" / "apollo.json"
PACKAGE_PATH = ROOT / "package.json"
MANIFEST_PATH = ROOT / "manifest.json"
EXPECTED_PALETTE_SHA256 = "550f8c36cf4ef6ac99551541d1fe9554f77d563fa1e7c129a6a82583321d61ef"
EXPECTED_SOURCE_SHA256 = "0ed79939b82134b14ea3e339ebabee1f22ee5d12bb80915b0a407b5affb5f5ac"

THEME_NAME = "Apollo Theme for Firefox"
DESCRIPTION = "A high-contrast Firefox theme generated from the canonical Apollo palette."
GECKO_ID = "humble-apollo@d0n9x1n"

# Ordered for stable generated JSON and grouped by Firefox chrome region.
COLOR_ROLES = (
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


def load_palette() -> dict[str, Any]:
    """Load the committed Apollo palette snapshot."""
    return load_json(PALETTE_PATH)


def palette_sha256() -> str:
    """Return the exact snapshot SHA-256 digest."""
    return hashlib.sha256(PALETTE_PATH.read_bytes()).hexdigest()


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
