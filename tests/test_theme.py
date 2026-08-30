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


DARK_MAPPING = (
    "**Apollo Dark** uses the official display name **Apollo Theme** and immutable "
    "Gecko GUID **humble-apollo@d0n9x1n**."
)
LIGHT_MAPPING = (
    "**Apollo Light** uses the official display name **Apollo Light Theme** and Gecko "
    "GUID **apollo-light@d0n9x1n**."
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


class ThemeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.palette_path = ROOT / "palette" / "apollo.json"
        self.manifest_path = ROOT / "manifest.json"
        self.package_path = ROOT / "package.json"
        self.palette = json.loads(self.palette_path.read_text(encoding="utf-8"))
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.package = json.loads(self.package_path.read_text(encoding="utf-8"))
        self.readme = (ROOT / "README.md").read_text(encoding="utf-8")
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
        self.assertEqual("Apollo Theme", self.manifest["name"])
        gecko = self.manifest["browser_specific_settings"]["gecko"]
        self.assertEqual("humble-apollo@d0n9x1n", gecko["id"])
        self.assertEqual({"required": ["none"]}, gecko["data_collection_permissions"])

    def test_addon_names_exclude_mozilla_trademarks(self) -> None:
        expected_names = {
            common.DARK_VARIANT: "Apollo Theme",
            common.LIGHT_VARIANT: "Apollo Light Theme",
        }
        for variant, expected_name in expected_names.items():
            name = generate.build_manifest(variant)["name"]
            with self.subTest(variant=variant.key):
                self.assertEqual(expected_name, name)
                self.assertNotIn("firefox", name.lower())
                self.assertNotIn("mozilla", name.lower())

    def test_light_variant_generates_separate_identity_and_roles(self) -> None:
        light = generate.build_manifest(common.LIGHT_VARIANT)
        self.assertEqual(ROOT / "variants" / "light" / "manifest.json", common.LIGHT_VARIANT.manifest_path)
        self.assertEqual("Apollo Light Theme", light["name"])
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

    def test_visible_prose_counts_only_reader_visible_non_code_text(self) -> None:
        markdown = """
![Apollo Dark image decoy](Apollo-Dark.png)
<a href="badge"><img alt="Apollo Light badge decoy"></a>
<!-- Apollo Dark comment decoy -->
<span hidden>Apollo Light hidden decoy</span>
`Apollo Dark inline-code decoy`
```text
Apollo Light fenced-code decoy
```
[**Apollo Dark**](https://example.invalid/Apollo-Light.png)
<a href="https://example.invalid">Apollo Light</a>
"""
        self.assertEqual("Apollo Dark Apollo Light", theme_check.visible_prose(markdown))

    def test_visible_prose_excludes_raw_preformatted_code(self) -> None:
        markdown = "<pre><strong>Apollo Dark</strong> and Apollo Light</pre>Visible tail"
        self.assertEqual("Visible tail", theme_check.visible_prose(markdown))

    def test_visible_prose_excludes_multi_backtick_inline_code(self) -> None:
        markdown = "``Apollo Dark`` and ```Apollo Light```"
        self.assertEqual("and", theme_check.visible_prose(markdown))

    def test_visible_prose_preserves_escaped_backticks(self) -> None:
        markdown = r"\`Apollo Dark\` and \`Apollo Light\`"
        self.assertEqual(
            "`Apollo Dark` and `Apollo Light`",
            theme_check.visible_prose(markdown),
        )

    def test_visible_prose_hides_unclosed_html_comment_through_eof(self) -> None:
        markdown = "Visible before\n<!-- Apollo Dark\nApollo Light"
        self.assertEqual("Visible before", theme_check.visible_prose(markdown))

    def test_visible_prose_strips_indented_fences_with_longer_closers(self) -> None:
        markdown = """
Visible before
   ~~~text
Apollo Dark
   ```
Apollo Light
  ~~
Apollo Dark
  ~~~~
Visible middle
 ```python
Apollo Light
   ~~~~
Apollo Dark
  ``
Apollo Light
   ````
Visible after
"""
        self.assertEqual(
            "Visible before Visible middle Visible after",
            theme_check.visible_prose(markdown),
        )

    def test_visible_prose_excludes_fences_nested_in_list_items(self) -> None:
        markdown = """
- Visible unordered before
- ~~~text
  Apollo Dark
  ~~~~
- Visible unordered after
1. Visible ordered before
2. ```text
   Apollo Light
   ````
3. Visible ordered after
"""
        prose = theme_check.visible_prose(markdown)
        for visible in (
            "Visible unordered before",
            "Visible unordered after",
            "Visible ordered before",
            "Visible ordered after",
        ):
            with self.subTest(visible=visible):
                self.assertIn(visible, prose)
        self.assertNotIn("Apollo Dark", prose)
        self.assertNotIn("Apollo Light", prose)

    def test_visible_prose_excludes_indented_code_nested_in_list_items(self) -> None:
        markdown = """
- Visible unordered before

      Apollo Dark

- Visible unordered after
1. Visible ordered before

       Apollo Light

2. Visible ordered after
"""
        prose = theme_check.visible_prose(markdown)
        for visible in (
            "Visible unordered before",
            "Visible unordered after",
            "Visible ordered before",
            "Visible ordered after",
        ):
            with self.subTest(visible=visible):
                self.assertIn(visible, prose)
        self.assertNotIn("Apollo Dark", prose)
        self.assertNotIn("Apollo Light", prose)

    def test_visible_prose_excludes_all_images_but_keeps_shortcut_links(self) -> None:
        markdown = """
![Apollo Dark](dark.png)
![Apollo Light][light-preview]
![Apollo Dark][]
![Apollo Light]
[Apollo Dark]
[Apollo Light]

[light-preview]: light.png
[Apollo Dark]: dark-reference.png
[Apollo Light]: light-reference.png
"""
        self.assertEqual(
            "Apollo Dark Apollo Light",
            theme_check.visible_prose(markdown),
        )

    def test_visible_prose_excludes_blockquoted_and_multiline_code(self) -> None:
        markdown = (
            "> Visible quote prose\n"
            ">\n"
            "> ```text\n"
            "> Apollo Dark\n"
            "> ```\n"
            ">\n"
            f"> {' ' * 4}Apollo Light\n"
            ">\n"
            "``Apollo Dark\nApollo Light``\n"
            "Trailing text\n"
        )
        self.assertEqual(
            "Visible quote prose Trailing text",
            theme_check.visible_prose(markdown),
        )

    def test_visible_prose_excludes_tab_indented_blockquote_code(self) -> None:
        markdown = (
            ">     Apollo Dark\n"
            ">\tApollo Light\n"
            "> \tApollo Dark\n"
            "Visible tail"
        )
        self.assertEqual("Visible tail", theme_check.visible_prose(markdown))

    def test_visible_prose_excludes_mixed_space_tab_indented_code(self) -> None:
        markdown = (
            "Visible before\n"
            " \tApollo Dark\n"
            "   \tApollo Light\n"
            "Visible middle\n"
            "- Visible unordered before\n"
            "\n"
            "  \t  Apollo Dark\n"
            "\n"
            "- Visible unordered after\n"
            "1. Visible ordered before\n"
            "\n"
            "   \t   Apollo Light\n"
            "\n"
            "2. Visible ordered after\n"
            "Visible after\n"
        )
        prose = theme_check.visible_prose(markdown)
        for visible in (
            "Visible before",
            "Visible middle",
            "Visible unordered before",
            "Visible unordered after",
            "Visible ordered before",
            "Visible ordered after",
            "Visible after",
        ):
            with self.subTest(visible=visible):
                self.assertIn(visible, prose)
        self.assertNotIn("Apollo Dark", prose)
        self.assertNotIn("Apollo Light", prose)

    def test_readme_contract_ignores_names_only_in_quoted_or_multiline_code(
        self,
    ) -> None:
        mutated = (
            self.readme.replace("Apollo Dark", "Dark variant").replace(
                "Apollo Light", "Light variant"
            )
            + "\n> ```text\n> Apollo Dark\n> ```\n"
            + f"> {' ' * 4}Apollo Light\n"
            + "``Apollo Dark\nApollo Light``\n"
        )
        errors = theme_check.validate_readme_contract(mutated)
        for name in ("Apollo Dark", "Apollo Light"):
            with self.subTest(name=name):
                self.assertIn(
                    f"README visible prose must name {name} exactly",
                    errors,
                )

    def test_readme_contract_passes(self) -> None:
        self.assertEqual([], theme_check.validate_readme_contract(self.readme))

    def test_readme_contract_requires_each_visible_variant_name_independently(self) -> None:
        mutations = {
            "Apollo Dark": self.readme.replace("Apollo Dark", "Apollo Darker"),
            "Apollo Light": self.readme.replace("Apollo Light", "Apollo Lighter"),
        }
        for name, mutated in mutations.items():
            with self.subTest(name=name):
                self.assertIn(
                    f"README visible prose must name {name} exactly",
                    theme_check.validate_readme_contract(mutated),
                )

    def test_readme_contract_ignores_non_prose_variant_name_decoys(self) -> None:
        mutations = {
            "Apollo Dark": self.readme.replace("Apollo Dark", "Dark variant")
            + "\n![Apollo Dark](Apollo-Dark.png)\n<!-- Apollo Dark -->\n"
            + "`Apollo Dark`\nApollo Dark.md\n",
            "Apollo Light": self.readme.replace("Apollo Light", "Light variant")
            + "\n<img alt=\"Apollo Light\" hidden>\n```text\nApollo Light\n```\n"
            + "Apollo Light.png\n",
        }
        for name, mutated in mutations.items():
            with self.subTest(name=name):
                self.assertIn(
                    f"README visible prose must name {name} exactly",
                    theme_check.validate_readme_contract(mutated),
                )

    def test_readme_contract_requires_each_command_marker_independently(self) -> None:
        mutations = {
            "npm run dev:dark": self.readme.replace(
                "npm run dev:dark", "npm run dev:darker"
            ),
            "npm run dev:light": self.readme.replace(
                "npm run dev:light", "npm run dev:lighter"
            ),
            "--source-dir .": self.readme.replace("--source-dir .", "--source-dir ./"),
            "--source-dir variants/light": self.readme.replace(
                "--source-dir variants/light", "--source-dir variants/lighter"
            ),
        }
        for marker, mutated in mutations.items():
            with self.subTest(marker=marker):
                self.assertIn(
                    f"README must contain exact marker: {marker}",
                    theme_check.validate_readme_contract(mutated),
                )

    def test_readme_contract_rejects_marker_prefix_and_suffix_decoys(self) -> None:
        mutations = (
            (
                "npm run dev:dark",
                "prefix npm run dev:dark",
                "npm run dev:dark suffix",
            ),
            (
                "npm run dev:light",
                "prefix npm run dev:light",
                "npm run dev:light suffix",
            ),
            (
                "--source-dir .",
                "x--source-dir .",
                "--source-dir .x",
            ),
            (
                "--source-dir variants/light",
                "x--source-dir variants/light",
                "--source-dir variants/lightx",
            ),
        )
        for marker, invalid_prefix, invalid_suffix in mutations:
            for boundary, replacement in (
                ("prefix", invalid_prefix),
                ("suffix", invalid_suffix),
            ):
                with self.subTest(marker=marker, boundary=boundary):
                    mutated = self.readme.replace(marker, replacement)
                    self.assertIn(
                        f"README must contain exact marker: {marker}",
                        theme_check.validate_readme_contract(mutated),
                    )

    def test_readme_contract_requires_identity_mappings(self) -> None:
        mutations = {
            "dark display name": self.readme.replace(DARK_MAPPING, ""),
            "light display name": self.readme.replace(LIGHT_MAPPING, ""),
            "dark GUID": self.readme.replace(
                "**humble-apollo@d0n9x1n**", "**changed-dark@d0n9x1n**", 1
            ),
            "light GUID": self.readme.replace(
                "**apollo-light@d0n9x1n**", "**changed-light@d0n9x1n**", 1
            ),
        }
        for mapping, mutated in mutations.items():
            with self.subTest(mapping=mapping):
                self.assertTrue(theme_check.validate_readme_contract(mutated))

    def test_readme_contract_requires_separate_complete_signing_examples(self) -> None:
        mutations = {
            "dark heading": self.readme.replace("### Apollo Dark signing", "### Signing"),
            "light heading": self.readme.replace("### Apollo Light signing", "### Signing"),
            "dark command": self.readme.replace(DARK_SIGNING_COMMAND, "npx web-ext sign"),
            "light command": self.readme.replace(LIGHT_SIGNING_COMMAND, "npx web-ext sign"),
        }
        for example, mutated in mutations.items():
            with self.subTest(example=example):
                self.assertTrue(theme_check.validate_readme_contract(mutated))

    def test_readme_contract_requires_exact_marketplace_disclaimers(self) -> None:
        mutated = self.readme.replace(RELEASE_DISCLAIMER, "").replace(
            MARKETPLACE_DISCLAIMER,
            "Both themes are available from the marketplace.",
        )
        errors = theme_check.validate_readme_contract(mutated)
        self.assertTrue(errors)
        self.assertTrue(any("marketplace" in error.lower() or "AMO" in error for error in errors))

    def test_readme_contract_rejects_positive_marketplace_availability_claims(self) -> None:
        for claim in (
            "Both themes are available from the marketplace.",
            "Apollo Dark is available on AMO.",
            "Apollo Light is now available in the Firefox Add-ons marketplace.",
        ):
            with self.subTest(claim=claim):
                self.assertTrue(
                    theme_check.validate_readme_contract(self.readme + "\n" + claim)
                )

    def test_readme_contract_rejects_adverbial_marketplace_availability_claims(
        self,
    ) -> None:
        for claim in (
            "Apollo Dark is currently available from AMO.",
            "Apollo Light is already available on AMO.",
            "Apollo Dark is publicly available through the marketplace.",
            "Apollo Light is generally available in the Firefox Add-ons marketplace.",
            "Both themes are currently available from the marketplace.",
        ):
            with self.subTest(claim=claim):
                self.assertIn(
                    "README must not claim marketplace availability",
                    theme_check.validate_readme_contract(self.readme + "\n" + claim),
                )

    def test_readme_contract_rejects_marketplace_availability_at_claims(self) -> None:
        for claim in (
            "Apollo Dark is available at AMO.",
            "Both themes are currently available at the marketplace.",
        ):
            with self.subTest(claim=claim):
                self.assertIn(
                    "README must not claim marketplace availability",
                    theme_check.validate_readme_contract(self.readme + "\n" + claim),
                )

    def test_readme_contract_allows_negative_marketplace_disclaimers(self) -> None:
        for disclaimer in (
            "Apollo Dark is not available from AMO.",
            "Apollo Light is not available at the marketplace.",
            "This repository makes no claim that Apollo Light is available from the marketplace.",
            "This repository makes no claim that Apollo Dark is currently available from AMO.",
            "This repository makes no claim that Apollo Dark is available at AMO.",
        ):
            with self.subTest(disclaimer=disclaimer):
                self.assertEqual(
                    [],
                    theme_check.validate_readme_contract(
                        self.readme + "\n" + disclaimer
                    ),
                )

    def test_readme_preserves_existing_release_and_uninstall_facts(self) -> None:
        for required in (
            "previews/firefox.svg",
            "previews/firefox-light.svg",
            "unsigned ZIPs",
            "not Mozilla-signed XPIs",
            "version 1.1.1",
            "Both manifests are generated",
            "remove **Apollo Theme** or **Apollo Light Theme**",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.readme)
        self.assertNotIn("will appear", self.readme)
        self.assertNotIn("coming soon", self.readme.lower())

    def test_release_workflow_uses_target_qualified_name(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        self.assertIn("Build Apollo Themes for Firefox", workflow)
        self.assertIn("## Apollo Themes for Firefox ${TAG}", workflow)
        self.assertIn("name: Apollo Themes for Firefox ${{ github.ref_name }}", workflow)

    def test_package_and_release_cover_both_static_themes(self) -> None:
        self.assertEqual("apollo-theme", self.package["name"])
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
            ("manifest.json", "apollo-theme.zip"),
            ("variants/light/manifest.json", "apollo-light-theme.zip"),
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
