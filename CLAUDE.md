# CLAUDE.md

## Project

This repository contains **Firefox Apollo Theme**, a static Firefox WebExtension theme using Manifest V2. There is no runtime JavaScript, background process, CSS, network access, or persistent state. Firefox renders browser chrome from `manifest.json`'s `theme.colors` object.

`manifest.json` is deterministic generated output. The implementation is:

- `palette/apollo.json`: committed exact snapshot of the canonical Apollo palette.
- `scripts/common.py`: Firefox role mapping, stable identity, palette hash, and contrast helpers.
- `scripts/generate.py`: generates `manifest.json`; `--check` detects drift without writing.
- `scripts/check.py`: validates the snapshot hash, palette membership, text contrast, restricted colors, accents, and generated output.
- `tests/test_theme.py`: focused stdlib-only regression tests.

The package and repository identity is `firefox-apollo-theme`; the display name is `Firefox Apollo Theme`; the repository URL is `https://github.com/apollo-theme/firefox-apollo-theme`.

## Immutable compatibility identity

Never change the Gecko ID **`humble-apollo@d0n9x1n`**. AMO associates it with the public 0.1.2 release, and changing it would break upgrade continuity. Repository name, display name, and AMO URL slug are independent. The existing AMO slug may remain `humble-apollo`; do not claim it changed without confirming it on AMO.

Preserve `browser_specific_settings.gecko.data_collection_permissions.required = ["none"]` when changing generation.

## Commands

Run from the repository root:

```sh
npm ci                                      # exact Node dependencies
python3 scripts/generate.py                 # regenerate manifest.json
npm run check                               # palette hash + generated drift + semantic checks
npm test                                    # complete Python unittest suite
npm run lint                                # strict web-ext manifest lint
npm run build                               # web-ext-artifacts/firefox-apollo-theme.zip
npm run dev                                 # interactive Firefox Developer Edition preview
```

Run one named test:

```sh
python3 -m unittest tests/test_theme.py -k test_gecko_identity_is_exact -v
```

`npm run dev` uses the `deved` binary alias and a temporary profile. Do not run it in unattended automation because it launches an interactive browser.

## Change workflow

1. Never hand-edit `manifest.json`.
2. For Firefox role changes, edit `COLOR_ROLES`, text-background pairs, or accent roles in `scripts/common.py`.
3. Run `python3 scripts/generate.py`.
4. Run `npm run check`, `npm test`, `npm run lint`, and `npm run build`.
5. Inspect the temporary theme in Firefox Developer Edition before release.

For a canonical palette update, copy the canonical `palette/apollo.json` byte-for-byte, compute its SHA-256, update `EXPECTED_PALETTE_SHA256` in `scripts/common.py`, regenerate, and rerun all checks. Do not weaken the hash or drift checks to accept an unexplained mismatch.

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

Package metadata and manifest version must match. The release workflow also requires a tag `v<version>` matching both values. ZIP and XPI artifacts are ignored and must not be committed. CI and release workflows use `npm ci` and the committed lockfile.

Permanent Firefox installation requires Mozilla signing. Do not push, tag, create a release, transfer/rename GitHub resources, or publish to AMO unless the maintainer explicitly requests that external action.
