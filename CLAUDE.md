# CLAUDE.md

## Project

This repository contains **Firefox Apollo Theme** and **Firefox Apollo Light Theme**, two separately installable static Firefox WebExtension themes using Manifest V2. There is no runtime JavaScript, background process, CSS, network access, or persistent state. Firefox renders browser chrome from each manifest's `theme.colors` object; static Firefox themes cannot bundle two themes in one manifest.

Both manifests are deterministic generated output. The implementation is:

- `palette/apollo.json` and `palette/apollo-light.json`: committed exact snapshots of the canonical dark and light palettes.
- `scripts/common.py`: variant specs, Firefox role mappings, stable identities, palette hashes, and contrast helpers.
- `scripts/generate.py`: generates `manifest.json` and `variants/light/manifest.json`; `--check` detects drift without writing.
- `scripts/check.py`: validates both snapshot hashes, palette membership, text contrast, restricted colors, accents, and generated output.
- `tests/test_theme.py`: focused stdlib-only regression tests.

The package and repository identity remains `firefox-apollo-theme` at `https://github.com/apollo-theme/firefox-apollo-theme`. The display names are `Firefox Apollo Theme` and `Firefox Apollo Light Theme`.

## Immutable compatibility identity

Never change the dark Gecko ID **`humble-apollo@d0n9x1n`**. AMO associates it with the public 0.1.2 release, and changing it would break upgrade continuity. The light theme has separate stable Gecko ID **`apollo-light@d0n9x1n`**. Never substitute one identity for the other or upload light as a version of the dark AMO listing. Repository name, display names, and AMO URL slugs are independent. Do not claim marketplace availability without confirming it on AMO.

Preserve `browser_specific_settings.gecko.data_collection_permissions.required = ["none"]` in both manifests when changing generation.

## Commands

Run from the repository root:

```sh
npm ci                                      # exact Node dependencies
python3 scripts/generate.py                 # regenerate both manifests
npm run check                               # both palette hashes + drift + semantic checks
npm test                                    # complete Python unittest suite
npm run lint                                # strict web-ext lint for both source roots
npm run build                               # both ZIPs in web-ext-artifacts/
npm run dev:dark                            # interactive dark preview
npm run dev:light                           # interactive light preview
```

Run one named test:

```sh
python3 -m unittest tests/test_theme.py -k test_gecko_identity_is_exact -v
```

Both preview commands use the `deved` binary alias and a temporary profile. Do not run them in unattended automation because they launch an interactive browser.

## Change workflow

1. Never hand-edit either generated manifest.
2. For Firefox role changes, edit the variant's `color_roles`, text-background pairs, or accent roles in `scripts/common.py`.
3. Run `python3 scripts/generate.py`.
4. Run `npm run check`, `npm test`, `npm run lint`, and `npm run build`.
5. Inspect the temporary theme in Firefox Developer Edition before release.

For a canonical palette update, copy the corresponding `palette/apollo.json` or `palette/apollo-light.json` byte-for-byte, compute its SHA-256, update that variant spec's expected palette and source hashes in `scripts/common.py`, regenerate, and rerun all checks. Do not weaken the hash or drift checks to accept an unexplained mismatch.

## Palette constraints

This project uses the canonical Apollo palette snapshot.

- Canvas: `#141617`
- Raised surface: `#1d2021`
- Primary text: `#cfbc97`
- Secondary text: `#d5c4a1`
- Inactive text: `#928374`
- Focus/accent: `#fabd2f`
- Selection: `#3c3836`

Use only colors present in the snapshot. Never use `#665c54` for normal or small text; it is restricted to ANSI bright black and, in this adapter, a non-text active surface. Keep every mapped text pair at or above the palette's 4.5 contrast minimum. Inactive text belongs on the `#141617` canvas because it falls just below 4.5 on the raised surface.

Manifest V2 does not provide general error, warning, success, or information roles. Do not invent unsupported keys to force status colors into Firefox. `web-ext lint --warnings-as-errors` is the schema gate.

## Packaging and release

Package metadata and both manifest versions must match. The release workflow also requires a tag `v<version>` matching all three values. `npm run build` creates separate dark and light ZIPs, each containing only its own manifest. ZIP and XPI artifacts are ignored and must not be committed. CI and release workflows use `npm ci` and the committed lockfile.

Permanent Firefox installation requires separate Mozilla signing for each identity. GitHub release ZIPs are unsigned and do not prove marketplace availability. Do not push, tag, create a release, transfer/rename GitHub resources, sign, or publish to AMO unless the maintainer explicitly requests that external action.
