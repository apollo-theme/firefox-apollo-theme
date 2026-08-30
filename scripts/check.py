#!/usr/bin/env python3
"""Validate the palette snapshot and generated Firefox adapter."""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
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
FENCE_OPEN = re.compile(
    r"^[ \t]{0,3}(?:(?:[-+*]|\d+[.)])[ \t]+)?(`{3,}|~{3,})([^\r\n]*)$"
)
BLOCKQUOTE_PREFIX = re.compile(r"^(?:[ \t]{0,3}> ?)+")
INLINE_CODE = re.compile(r"(?<!\\)(`+)(.*?)(?<!\\)\1", re.DOTALL)
MARKDOWN_IMAGE = re.compile(r"!\[[^\]]*\](?:\([^)]*\)|\[[^\]]*\])")
MARKDOWN_SHORTCUT_IMAGE = re.compile(r"!\[([^\]\n]+)\]")
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\](?:\([^)]*\)|\[[^\]]*\])")
MARKDOWN_SHORTCUT_LINK = re.compile(r"(?<!!)\[([^\]\n]+)\]")
LINK_DEFINITION = re.compile(r"(?m)^[ \t]{0,3}\[[^\]]+\]:\s+\S+.*$")
README_PATH = ROOT / "README.md"

VISIBLE_VARIANT_NAMES = ("Apollo Dark", "Apollo Light")
README_LINE_MARKERS = ("npm run dev:dark", "npm run dev:light")
README_TOKEN_MARKERS = ("--source-dir .", "--source-dir variants/light")
README_MARKERS = README_LINE_MARKERS + README_TOKEN_MARKERS
DARK_IDENTITY_MAPPING = (
    "Apollo Dark uses the official display name Apollo Theme and immutable Gecko GUID "
    "humble-apollo@d0n9x1n."
)
LIGHT_IDENTITY_MAPPING = (
    "Apollo Light uses the official display name Apollo Light Theme and Gecko GUID "
    "apollo-light@d0n9x1n."
)
RELEASE_DISCLAIMER = (
    "The latest GitHub Release does not imply that either variant has been published "
    "to AMO."
)
MARKETPLACE_DISCLAIMER = (
    "This repository makes no claim that version 1.1.1 of either theme is available "
    "from the marketplace."
)
DARK_SIGNING_COMMAND = (
    "npx web-ext sign --source-dir . --channel listed \\\n"
    '  --api-key "$AMO_JWT_ISSUER" \\\n'
    '  --api-secret "$AMO_JWT_SECRET" \\\n'
    "  --ignore-files package.json package-lock.json README.md CLAUDE.md LICENSE "
    "palette scripts tests variants .github"
)
LIGHT_SIGNING_COMMAND = (
    "npx web-ext sign --source-dir variants/light --channel listed \\\n"
    '  --api-key "$AMO_JWT_ISSUER" \\\n'
    '  --api-secret "$AMO_JWT_SECRET"'
)
MARKETPLACE_AVAILABILITY_ADVERBS = (
    "already",
    "currently",
    "generally",
    "now",
    "publicly",
)
POSITIVE_MARKETPLACE_CLAIM = re.compile(
    r"\b(?:both\s+(?:themes|variants)|Apollo\s+(?:Dark|Light)(?:\s+Theme)?|"
    r"Apollo(?:\s+Light)?\s+Theme)\s+(?:is|are)\s+"
    rf"(?:(?:{'|'.join(MARKETPLACE_AVAILABILITY_ADVERBS)})\s+){{0,2}}"
    r"available\s+(?:at|from|in|on|through)\s+(?:the\s+)?"
    r"(?:Firefox\s+Add-ons\s+)?(?:marketplace|AMO)\b",
    re.IGNORECASE,
)
NO_CLAIM_SCOPE = re.compile(
    r"\bmakes\s+no\s+claim\s+that(?:\s+\S+){0,8}\s*$",
    re.IGNORECASE,
)


class _VisibleHTMLParser(HTMLParser):
    """Collect text rendered by non-hidden HTML elements."""

    HIDDEN_ELEMENTS = {"code", "pre", "script", "style", "template"}
    VOID_ELEMENTS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.stack: list[tuple[str, bool]] = []
        self.hidden_depth = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        tag = tag.lower()
        attributes = {name.lower(): value for name, value in attrs}
        style = (attributes.get("style") or "").replace(" ", "").lower()
        hidden = bool(
            self.hidden_depth
            or tag in self.HIDDEN_ELEMENTS
            or "hidden" in attributes
            or (attributes.get("aria-hidden") or "").lower() == "true"
            or "display:none" in style
            or "visibility:hidden" in style
        )
        if tag not in self.VOID_ELEMENTS:
            self.stack.append((tag, hidden))
            if hidden:
                self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if not self.stack:
            return
        while self.stack:
            open_tag, hidden = self.stack.pop()
            if hidden:
                self.hidden_depth -= 1
            if open_tag == tag:
                break

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            self.parts.append(data)


def _strip_blockquote_markers(markdown: str) -> str:
    """Expose Markdown content inside standard blockquote prefixes."""
    return "".join(
        BLOCKQUOTE_PREFIX.sub("", line)
        for line in markdown.splitlines(keepends=True)
    )


def _leading_indentation_columns(line: str) -> int:
    """Return leading indentation using four-column Markdown tab stops."""
    columns = 0
    for character in line:
        if character == " ":
            columns += 1
        elif character == "\t":
            columns += 4 - columns % 4
        else:
            break
    return columns


def _strip_indented_code(markdown: str) -> str:
    """Remove nonblank Markdown lines indented by at least four columns."""
    visible_lines: list[str] = []
    for line in markdown.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        newline = line[len(content) :]
        list_item = re.match(
            r"^[ \t]{0,3}(?:[-+*]|\d{1,9}[.)])(?P<spacing>[ \t]+)(?P<body>.*)$",
            content,
        )
        candidate = (
            list_item.group("spacing")[1:] + list_item.group("body")
            if list_item
            else content
        )
        if candidate.strip() and _leading_indentation_columns(candidate) >= 4:
            visible_lines.append(newline)
        else:
            visible_lines.append(line)
    return "".join(visible_lines)


def _strip_fenced_code(markdown: str) -> str:
    """Remove Markdown fenced blocks, including longer matching closers."""
    visible_lines: list[str] = []
    fence_character: str | None = None
    minimum_closer_length = 0

    for line in markdown.splitlines(keepends=True):
        logical_line = line.rstrip("\r\n")
        if fence_character is None:
            opener = FENCE_OPEN.fullmatch(logical_line)
            if opener:
                delimiter, info = opener.groups()
                if delimiter[0] == "~" or "`" not in info:
                    fence_character = delimiter[0]
                    minimum_closer_length = len(delimiter)
                    continue
            visible_lines.append(line)
            continue

        closer = re.fullmatch(
            rf"[ \t]{{0,3}}{re.escape(fence_character)}"
            rf"{{{minimum_closer_length},}}[ \t]*",
            logical_line,
        )
        if closer:
            fence_character = None
            minimum_closer_length = 0

    return "".join(visible_lines)


def visible_prose(markdown: str) -> str:
    """Return normalized prose that a README reader can see outside code."""
    prose = _strip_blockquote_markers(markdown)
    prose = _strip_fenced_code(prose)
    prose = _strip_indented_code(prose)
    prose = INLINE_CODE.sub(" ", prose)
    prose = prose.replace(r"\`", "`")
    prose = MARKDOWN_IMAGE.sub(" ", prose)
    prose = MARKDOWN_SHORTCUT_IMAGE.sub(" ", prose)
    prose = LINK_DEFINITION.sub(" ", prose)
    prose = MARKDOWN_LINK.sub(r"\1", prose)
    prose = MARKDOWN_SHORTCUT_LINK.sub(r"\1", prose)
    prose = re.sub(r"<!--.*?-->", " ", prose, flags=re.DOTALL)

    parser = _VisibleHTMLParser()
    parser.feed(prose)
    text = " ".join(parser.parts)
    text = re.sub(r"[*_~]", "", text)
    text = re.sub(r"[#>|]", " ", text)
    return " ".join(text.split())


def _has_exact_visible_name(prose: str, name: str) -> bool:
    pattern = rf"(?<![\w./-]){re.escape(name)}(?![\w./-]|\s+Theme\b)"
    return re.search(pattern, prose) is not None


def _has_exact_marker(markdown: str, marker: str) -> bool:
    if marker in README_LINE_MARKERS:
        pattern = rf"(?m)^[ \t]*{re.escape(marker)}[ \t]*$"
    else:
        pattern = rf"(?<![\w:./-]){re.escape(marker)}(?![\w:./-])"
    return re.search(pattern, markdown) is not None


def validate_readme_contract(markdown: str) -> list[str]:
    """Return failures in the documented Dark and Light Firefox contract."""
    errors: list[str] = []
    prose = visible_prose(markdown)

    for name in VISIBLE_VARIANT_NAMES:
        if not _has_exact_visible_name(prose, name):
            errors.append(f"README visible prose must name {name} exactly")
    for marker in README_MARKERS:
        if not _has_exact_marker(markdown, marker):
            errors.append(f"README must contain exact marker: {marker}")
    for mapping in (DARK_IDENTITY_MAPPING, LIGHT_IDENTITY_MAPPING):
        if mapping not in prose:
            errors.append(f"README visible prose must contain identity mapping: {mapping}")
    for heading in ("### Apollo Dark signing", "### Apollo Light signing"):
        if re.search(rf"(?m)^{re.escape(heading)}[ \t]*$", markdown) is None:
            errors.append(f"README must contain signing heading: {heading}")
    for label, command in (
        ("Apollo Dark", DARK_SIGNING_COMMAND),
        ("Apollo Light", LIGHT_SIGNING_COMMAND),
    ):
        if command not in markdown:
            errors.append(f"README must contain complete {label} signing command")
    for disclaimer in (RELEASE_DISCLAIMER, MARKETPLACE_DISCLAIMER):
        if disclaimer not in prose:
            errors.append(f"README visible prose must contain marketplace disclaimer: {disclaimer}")
    for claim in POSITIVE_MARKETPLACE_CLAIM.finditer(prose):
        sentence_start = max(
            prose.rfind(".", 0, claim.start()),
            prose.rfind("!", 0, claim.start()),
            prose.rfind("?", 0, claim.start()),
        )
        if not NO_CLAIM_SCOPE.search(prose[sentence_start + 1 : claim.start()]):
            errors.append("README must not claim marketplace availability")
            break

    return errors


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
    """Return deterministic failures for every theme variant and the README."""
    errors = [error for variant in VARIANTS for error in validate_variant(variant)]
    readme = README_PATH.read_text(encoding="utf-8")
    return errors + validate_readme_contract(readme)


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
