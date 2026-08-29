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
  <a href="https://apollo-theme.github.io/#app-firefox"><img alt="Firefox Apollo Theme simulated dark preview" src="https://raw.githubusercontent.com/apollo-theme/apollo-theme.github.io/main/previews/firefox.svg" width="900"></a>
  <a href="https://apollo-theme.github.io/#app-firefox-light"><img alt="Firefox Apollo Light Theme simulated preview" src="https://raw.githubusercontent.com/apollo-theme/apollo-theme.github.io/main/previews/firefox-light.svg" width="900"></a>
</p>

<p align="center"><em>Simulated dark and light previews — Firefox chrome can vary with browser and operating-system settings.</em></p>

## Identity

| | Dark | Light |
| --- | --- | --- |
| Official display name | **Firefox Apollo Theme** | **Firefox Apollo Light Theme** |
| Source manifest | `manifest.json` | `variants/light/manifest.json` |
| Version | `1.1.1` | `1.1.1` |
| Gecko GUID | `humble-apollo@d0n9x1n` | `apollo-light@d0n9x1n` |

The package and repository remain `firefox-apollo-theme`. The dark Gecko GUID is an immutable compatibility identity that preserves upgrade continuity with public version 0.1.2. The light theme has a separate stable GUID because static Firefox themes cannot bundle two themes in one manifest.

## Local preview

Use Firefox Developer Edition for development. Either run:

```sh
npm ci
npm run dev:dark
npm run dev:light
```

Each preview targets an installed Firefox Developer Edition (`web-ext` alias `deved`) and uses a temporary profile. These commands open an interactive browser, so they are not run in CI.

To load either theme into an already-open Developer Edition instead:

1. Open `about:debugging#/runtime/this-firefox`.
2. Select **Load Temporary Add-on…**.
3. Choose `manifest.json` for dark or `variants/light/manifest.json` for light.

Temporary add-ons disappear when Firefox restarts.

## Develop and verify

Both manifests are generated; do not edit them directly. Edit the variant role mapping in `scripts/common.py`, then regenerate and verify:

```sh
python3 scripts/generate.py
npm run check
npm test
npm run lint
npm run build:dark
npm run build:light
```

Run one focused test with:

```sh
python3 -m unittest tests/test_theme.py -k test_gecko_identity_is_exact -v
```

The separate build commands write `web-ext-artifacts/firefox-apollo-theme.zip` and `web-ext-artifacts/firefox-apollo-light-theme.zip`; `npm run build` runs both. Each archive intentionally contains only its own `manifest.json`.

## Palette mapping

The committed `palette/apollo.json` and `palette/apollo-light.json` files are exact snapshots of the canonical dark and light palettes. Their SHA-256 values are pinned by the Python checks so palette and generated-manifest drift fail deterministically.

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

The GitHub build and release artifacts are unsigned ZIPs for source distribution and inspection. They are not Mozilla-signed XPIs and cannot be installed permanently in standard Firefox. Do not rename an unsigned ZIP to XPI and expect Firefox to accept it.

Firefox requires a separately Mozilla-signed XPI for each theme's permanent installation. The dark GUID belongs to its existing AMO listing; the light GUID is a separate identity and must not be uploaded as a version of the dark listing. Build the relevant ZIP, then submit or sign that theme with its matching AMO identity and API credentials:

```sh
npx web-ext sign --channel listed \
  --api-key "$AMO_JWT_ISSUER" \
  --api-secret "$AMO_JWT_SECRET"
```

`--channel listed` publishes to AMO; use `--channel unlisted` only for a signed, self-distributed XPI. The latest GitHub Release does not imply that either variant has been published to AMO. This repository makes no claim that version 1.1.1 of either theme is available from the marketplace.

To uninstall either variant, open `about:addons`, select **Themes**, switch to another theme, then remove **Firefox Apollo Theme** or **Firefox Apollo Light Theme**.

## Visual check

After temporary loading, inspect normal and private windows at regular and compact densities:

- active and inactive tabs, loading indicator, separators, and selected-tab focus;
- address bar unfocused, focused, typed selection, and autocomplete popup;
- toolbar icons, attention state, bookmarks, sidebar, and new-tab page;
- readable text in default, hover, selected, inactive, and high-contrast OS states.

Automated checks validate schema, palette membership, restricted text colors, and WCAG contrast. A human visual pass is still required before release.

## Release

A `v*` tag runs `.github/workflows/release.yml`. The workflow uses `npm ci`, checks generated output and tests, lints both source roots, verifies the tag matches `package.json` and both manifests, builds, and attaches both ZIPs to a GitHub Release.

Before tagging, bump `package.json`, regenerate both manifests, and commit them together. External pushing, tagging, GitHub release creation, signing, and AMO submission are deliberate maintainer actions.

The Gecko ID remains **`humble-apollo@d0n9x1n`** for upgrade continuity with public version 0.1.2. It must never change. The existing AMO URL slug may continue to be `humble-apollo`; this repository does not claim that AMO changed it.
