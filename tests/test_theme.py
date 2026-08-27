"""Focused regression tests for the generated Firefox theme."""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check as theme_check  # noqa: E402
import common  # noqa: E402
import generate  # noqa: E402


class ThemeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.palette_path = ROOT / "palette" / "apollo.json"
        self.manifest_path = ROOT / "manifest.json"
        self.package_path = ROOT / "package.json"
        self.palette = json.loads(self.palette_path.read_text(encoding="utf-8"))
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.package = json.loads(self.package_path.read_text(encoding="utf-8"))
        self.colors = self.manifest["theme"]["colors"]

    def test_palette_snapshot_matches_pinned_hash(self) -> None:
        digest = hashlib.sha256(self.palette_path.read_bytes()).hexdigest()
        self.assertEqual(common.EXPECTED_PALETTE_SHA256, digest)

    def test_palette_source_hash_matches_provenance(self) -> None:
        self.assertEqual(
            common.EXPECTED_SOURCE_SHA256,
            self.palette["provenance"]["sourceSha256"],
        )

    def test_manifest_matches_regenerated_output(self) -> None:
        expected = generate.render_manifest(generate.build_manifest())
        self.assertEqual(expected, self.manifest_path.read_text(encoding="utf-8"))

    def test_gecko_identity_is_exact(self) -> None:
        self.assertEqual(2, self.manifest["manifest_version"])
        self.assertEqual("Apollo Theme for Firefox", self.manifest["name"])
        gecko = self.manifest["browser_specific_settings"]["gecko"]
        self.assertEqual("humble-apollo@d0n9x1n", gecko["id"])
        self.assertEqual({"required": ["none"]}, gecko["data_collection_permissions"])

    def test_manifest_and_package_versions_agree(self) -> None:
        self.assertEqual("0.2.0", self.manifest["version"])
        self.assertEqual(self.package["version"], self.manifest["version"])

    def test_every_theme_color_comes_from_palette(self) -> None:
        palette_colors = set(self.palette["colors"].values())
        for role, color in self.colors.items():
            with self.subTest(role=role, color=color):
                self.assertIn(color, palette_colors)

    def test_text_roles_meet_contrast_on_their_background(self) -> None:
        for text_role, background_role in common.TEXT_BACKGROUNDS.items():
            foreground = self.colors[text_role]
            background = self.colors[background_role]
            with self.subTest(text_role=text_role, background_role=background_role):
                self.assertGreaterEqual(common.contrast_ratio(foreground, background), 4.5)

    def test_restricted_color_never_used_for_text(self) -> None:
        restricted = set(self.palette["constraints"]["restrictedColors"])
        for text_role in common.TEXT_BACKGROUNDS:
            with self.subTest(text_role=text_role):
                self.assertNotIn(self.colors[text_role], restricted)

    def test_accent_is_consistent(self) -> None:
        accent = self.palette["colors"]["accent"]
        for role in common.ACCENT_ROLES:
            with self.subTest(role=role):
                self.assertEqual(accent, self.colors[role])

    def test_validation_rejects_uncovered_text_role(self) -> None:
        color_roles = common.COLOR_ROLES + (("new_text", "ansiBrightBlack"),)
        errors = theme_check.validate_role_coverage(
            color_roles,
            common.TEXT_BACKGROUNDS,
            common.ACCENT_ROLES,
        )
        self.assertIn("new_text has no declared text background", errors)

    def test_validation_rejects_uncovered_accent_role(self) -> None:
        color_roles = common.COLOR_ROLES + (("new_attention", "accent"),)
        errors = theme_check.validate_role_coverage(
            color_roles,
            common.TEXT_BACKGROUNDS,
            common.ACCENT_ROLES,
        )
        self.assertIn("new_attention maps accent but is not checked as an accent role", errors)


if __name__ == "__main__":
    unittest.main()
