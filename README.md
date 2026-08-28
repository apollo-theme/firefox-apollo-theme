<h1 align="center">Firefox Apollo Theme</h1>

<p align="center">A static, high-contrast Firefox theme built with the canonical Apollo palette.</p>

<p align="center">
  <a href="https://apollo-theme.github.io/#app-firefox"><img alt="Preview" src="https://img.shields.io/badge/Preview-Website-d3869b?style=flat-square&amp;labelColor=141617"></a>
  <a href="https://github.com/apollo-theme/firefox-apollo-theme/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/apollo-theme/firefox-apollo-theme/ci.yml?branch=main&amp;style=flat-square&amp;label=CI&amp;labelColor=141617"></a>
  <a href="https://github.com/apollo-theme/firefox-apollo-theme/releases/latest"><img alt="Latest Release" src="https://img.shields.io/github/v/release/apollo-theme/firefox-apollo-theme?sort=semver&amp;style=flat-square&amp;label=Release&amp;labelColor=141617&amp;color=b8bb26"></a>
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/License-MIT-b8bb26?style=flat-square&amp;labelColor=141617"></a>
  <a href="manifest.json"><img alt="Target Firefox" src="https://img.shields.io/badge/Target-Firefox-fb4934?style=flat-square&amp;labelColor=141617"></a>
  <a href="palette/apollo.json"><img alt="Canonical palette" src="https://img.shields.io/badge/palette-canonical-fabd2f?style=flat-square&amp;labelColor=141617"></a>
</p>

<p align="center">
  <a href="https://apollo-theme.github.io/#app-firefox"><img alt="Firefox Apollo Theme simulated preview" src="https://raw.githubusercontent.com/apollo-theme/apollo-theme.github.io/main/previews/firefox.svg" width="900"></a>
</p>

<p align="center"><em>Simulated preview — Firefox chrome can vary with browser and operating-system settings.</em></p>

## Identity

| | |
| --- | --- |
| Official display name | **Firefox Apollo Theme** |
| Repository and package | `firefox-apollo-theme` |
| Version | `1.0.0` |
| Gecko GUID | `humble-apollo@d0n9x1n` |

The Gecko GUID is an immutable compatibility identity. It preserves upgrade continuity with public version 0.1.2 even though the display name and repository name are different.

## Local preview

Use Firefox Developer Edition for development. Either run:

```sh
npm ci
npm run dev
```

`dev` targets an installed Firefox Developer Edition (`web-ext` alias `deved`) and uses a temporary profile. It opens an interactive browser, so it is not run in CI.

To load the theme into an already-open Developer Edition instead:

1. Open `about:debugging#/runtime/this-firefox`.
2. Select **Load Temporary Add-on…**.
3. Choose `manifest.json` from this repository.

Temporary add-ons disappear when Firefox restarts.

## Develop and verify

`manifest.json` is generated; do not edit it directly. Edit the role mapping in `scripts/common.py`, then regenerate and verify:

```sh
python3 scripts/generate.py
npm run check
npm test
npm run lint
npm run build
```

Run one focused test with:

```sh
python3 -m unittest tests/test_theme.py -k test_gecko_identity_is_exact -v
```

`npm run build` writes `web-ext-artifacts/firefox-apollo-theme.zip`. The archive intentionally contains only `manifest.json`.

## Palette mapping

The committed `palette/apollo.json` is an exact snapshot of the canonical palette. Its SHA-256 is pinned by the Python checks so both palette and generated-manifest drift fail deterministically.

| Firefox role | Apollo value |
| --- | --- |
| Canvas, inactive frame, new tab, recessed fields | `#141617` |
| Toolbar, selected tab, popup, sidebar | `#1d2021` |
| Primary text and icons | `#cfbc97` |
| Selected/highlighted text | `#d5c4a1` |
| Inactive tab text | `#928374` |
| Focus, loading, attention | `#fabd2f` |
| Selection and separators | `#3c3836` |

`#665c54` is never used for normal or small text. Firefox Manifest V2 has no general danger, success, or information color roles, so those canonical status colors remain unmapped rather than being assigned to unrelated browser chrome.

## Install, sign, and uninstall

The GitHub build and release artifact is an unsigned ZIP for source distribution and inspection. It is not a Mozilla-signed XPI and cannot be installed permanently in standard Firefox. Do not rename an unsigned ZIP to XPI and expect Firefox to accept it.

Firefox requires a Mozilla-signed XPI for permanent installation. Build the ZIP, then upload it as a new version of the existing AMO listing, or sign with `web-ext` and AMO API credentials:

```sh
npx web-ext sign --channel listed \
  --api-key "$AMO_JWT_ISSUER" \
  --api-secret "$AMO_JWT_SECRET"
```

`--channel listed` publishes to AMO; use `--channel unlisted` only for a signed, self-distributed XPI. The latest GitHub Release does not imply that the same version has been published to AMO. This repository makes no claim that version 1.0.0 is available from the marketplace.

To uninstall, open `about:addons`, select **Themes**, switch to another theme, then remove **Firefox Apollo Theme**.

## Visual check

After temporary loading, inspect normal and private windows at regular and compact densities:

- active and inactive tabs, loading indicator, separators, and selected-tab focus;
- address bar unfocused, focused, typed selection, and autocomplete popup;
- toolbar icons, attention state, bookmarks, sidebar, and new-tab page;
- readable text in default, hover, selected, inactive, and high-contrast OS states.

Automated checks validate schema, palette membership, restricted text colors, and WCAG contrast. A human visual pass is still required before release.

## Release

A `v*` tag runs `.github/workflows/release.yml`. The workflow uses `npm ci`, checks generated output and tests, lints, verifies the tag matches both `manifest.json` and `package.json`, builds, and attaches `firefox-apollo-theme.zip` to a GitHub Release.

Before tagging, bump `package.json`, regenerate `manifest.json`, and commit both. External pushing, tagging, GitHub release creation, and AMO submission are deliberate maintainer actions.

The Gecko ID remains **`humble-apollo@d0n9x1n`** for upgrade continuity with public version 0.1.2. It must never change. The existing AMO URL slug may continue to be `humble-apollo`; this repository does not claim that AMO changed it.
