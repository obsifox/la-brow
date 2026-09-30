# Extension And Theme Compatibility

## Purpose

The product runs on a mobile engine while its users expect the desktop Firefox theme and add-on ecosystem. This layer states exactly which desktop surfaces are honoured, which are applied on a best effort basis, and which are refused. It never claims full desktop parity.

## Components

```text
extensions/manifest.py    parses a WebExtension manifest version 2 or 3
extensions/compat.py      evaluates declared sections and permissions against the matrix
extensions/themes.py      translates theme colours into a product gradient specification
extensions/policy.py      install policy: limits, prohibited permissions, acknowledgement
extensions/store.py       registry of recorded add-ons and the active theme
config/compat/*.yaml      the matrix and the install policy, both reviewable by hand
```

## Compatibility Levels

| Level | Meaning |
| --- | --- |
| supported | the mobile runtime honours the surface |
| partial | the surface is accepted and can behave or render differently |
| unsupported | the surface is refused because the runtime cannot honour it |

Declared sections and requested permissions are scored with the weights in the matrix. The score maps to `COMPATIBLE`, `PARTIAL` or `NOT_SUPPORTED`, and every evaluation returns the compatibility notice.

## Theme Translation

A desktop theme manifest carries a `theme.colors` map and optional `theme.images`. The translation produces a product theme specification:

| Output | Source |
| --- | --- |
| gradient stops | `frame`, `toolbar`, `tab_selected` |
| accent and glow | `tab_selected`, `button_background_hover` |
| palette | the full colour map with product defaults for absent keys |
| properties | `color_scheme`, `content_color_scheme` |
| image state | `theme_frame` is reported as pending because the packaged theme is required |

Colour values may be hex, rgb, rgba, named colours or stop arrays. Contrast pairs of text against its surface and reports a finding when the reading ratio is below the recommended value.

## Install Policy

| Rule | Behaviour |
| --- | --- |
| acknowledgement | an installation is refused until the compatibility notice is confirmed |
| prohibited permissions | `nativeMessaging`, `management`, `experiments`, `devtools`, `geckoProfiler`, `mozAddonManager` |
| prohibited sections | `devtools_page`, `experiment_apis` |
| manifest limits | 256 KiB serialised manifest, 128 character name, 64 permissions |
| signature | unverified packages are accepted after acknowledgement and are always listed as unverified |
| desktop store flows | add-ons that expect a desktop store installation are installed from a local manifest only |

## Notice Shown At Install Time

> This add-on targets desktop Firefox. Parts of it may not display or behave correctly in the mobile application, and the theme or interface changes it declares are applied on a best effort basis.

The notice is stored with every record together with the acknowledgement flag, so the interface can always show what the user agreed to.

## Interface Surface

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /api/compat/firefox-desktop | matrix, runtime and install notice |
| GET | /api/extensions | recorded add-ons, themes, active theme, signature state |
| POST | /api/extensions/inspect | compatibility report and theme translation without storing anything |
| POST | /api/extensions/install | record an add-on, refused without the acknowledgement |
| DELETE | /api/extensions/{id} | remove an add-on or theme |
| GET | /api/themes | recorded themes and the active gradient |
| PUT | /api/themes/active | activate a recorded theme |

## Mobile Surface

The Android application reads the same interface. The add-on screen shows the runtime matrix, inspects a pasted manifest, requires the acknowledgement toggle before installing, lists recorded add-ons with their signature state, and applies the active theme gradient across the shell through the theme engine.
