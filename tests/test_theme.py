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

    def test_light_manifest_matches_regenerated_output(self) -> None:
        expected = generate.render_manifest(generate.build_manifest(common.LIGHT_VARIANT))
        self.assertEqual(
            expected,
            common.LIGHT_VARIANT.manifest_path.read_text(encoding="utf-8"),
        )

    def test_light_variant_passes_semantic_validation(self) -> None:
        self.assertEqual([], theme_check.validate_variant(common.LIGHT_VARIANT))

    def test_gecko_identity_is_exact(self) -> None:
        self.assertEqual(2, self.manifest["manifest_version"])
        self.assertEqual("Firefox Apollo Theme", self.manifest["name"])
        gecko = self.manifest["browser_specific_settings"]["gecko"]
        self.assertEqual("humble-apollo@d0n9x1n", gecko["id"])
        self.assertEqual({"required": ["none"]}, gecko["data_collection_permissions"])

    def test_light_variant_generates_separate_identity_and_roles(self) -> None:
        light = generate.build_manifest(common.LIGHT_VARIANT)
        self.assertEqual(ROOT / "variants" / "light" / "manifest.json", common.LIGHT_VARIANT.manifest_path)
        self.assertEqual("Firefox Apollo Light Theme", light["name"])
        gecko = light["browser_specific_settings"]["gecko"]
        self.assertEqual("apollo-light@d0n9x1n", gecko["id"])
        self.assertEqual({"required": ["none"]}, gecko["data_collection_permissions"])
        self.assertEqual("#f9f5d7", light["theme"]["colors"]["frame"])
        self.assertEqual("#3c3836", light["theme"]["colors"]["toolbar_text"])
        self.assertEqual("#8a5200", light["theme"]["colors"]["tab_line"])
        self.assertEqual(
            "#f2e5bc",
            light["theme"]["colors"]["button_background_active"],
        )

    def test_manifest_and_package_versions_agree(self) -> None:
        light_manifest = json.loads(
            common.LIGHT_VARIANT.manifest_path.read_text(encoding="utf-8")
        )
        self.assertEqual("1.1.1", self.package["version"])
        self.assertEqual(
            {self.package["version"]},
            {self.manifest["version"], light_manifest["version"]},
        )

    def test_readme_presents_both_variants_through_uninstall(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for required in (
            "previews/firefox.svg",
            "previews/firefox-light.svg",
            "Firefox Apollo Theme",
            "Firefox Apollo Light Theme",
            "remove **Firefox Apollo Theme** or **Firefox Apollo Light Theme**",
        ):
            with self.subTest(required=required):
                self.assertIn(required, readme)
        self.assertNotIn("will appear", readme)
        self.assertNotIn("coming soon", readme.lower())

    def test_release_workflow_uses_app_first_name(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        self.assertIn("Build Firefox Apollo Themes", workflow)
        self.assertIn("## Firefox Apollo Themes ${TAG}", workflow)
        self.assertIn("name: Firefox Apollo Themes ${{ github.ref_name }}", workflow)
        self.assertNotIn("Apollo Theme for Firefox", workflow)

    def test_package_and_release_cover_both_static_themes(self) -> None:
        scripts = self.package["scripts"]
        lint_commands = " ".join(
            command for name, command in scripts.items() if name.startswith("lint")
        )
        build_commands = " ".join(
            command for name, command in scripts.items() if name.startswith("build")
        )
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        ci_workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        for manifest_path, archive_name in (
            ("manifest.json", "firefox-apollo-theme.zip"),
            ("variants/light/manifest.json", "firefox-apollo-light-theme.zip"),
        ):
            with self.subTest(manifest_path=manifest_path):
                self.assertIn(archive_name, build_commands)
                self.assertIn(manifest_path, workflow)
                self.assertIn(archive_name, workflow)
                self.assertIn(archive_name, ci_workflow)
        self.assertIn("web-ext lint --source-dir . ", lint_commands)
        self.assertIn("--ignore-files", lint_commands)
        self.assertIn("variants", lint_commands)
        self.assertIn("--source-dir variants/light", lint_commands)
        self.assertIn("web-ext build --source-dir . ", build_commands)
        self.assertIn("--source-dir variants/light", build_commands)
        self.assertIn("LIGHT_MANIFEST", workflow)
        self.assertIn('"$TAG" != "$LIGHT_MANIFEST"', workflow)

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
