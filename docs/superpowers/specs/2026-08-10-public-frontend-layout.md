# Public Frontend Layout Design

**Issue:** #133

## Goal

Modernize the public registration page without changing the registration, consent, member-area, or preference behavior. The page must feel like a practical community service, not a collection of marketing cards.

## Approved Direction

- Keep a compact, single-line header with brand, primary navigation, theme control, and language control.
- Use a segmented theme control: light, system, and dark represented by familiar icons. System remains the default and center option.
- Use compact flag buttons for Portuguese (Brazil), English, Spanish, French, and Simplified Chinese. The active language is announced accessibly.
- Keep the opening short and open, followed by the registration form. Remove the large hero/advertising composition and the repeated boxed-card treatment.
- Present the three onboarding steps as a flat horizontal strip, with a mobile stacked fallback.
- Present registration as an open two-column section: short contextual introduction on the left and the form on the right. The form itself retains a clear surface for readability.
- Retain all current product copy from the prior copy revision; this work changes hierarchy and wording only where a translation requires it.
- Remove public advertising placeholders from the primary path. Ad and consent runtime behavior remain compatible if ads are enabled later.

## Functional Requirements

- Preserve IDs, input names, links, consent controls, and JS hooks used by the existing registration flow.
- Theme and language settings persist using the existing local-storage keys.
- Language selection translates every visible static string on the public page and all runtime messages created by `app.js`.
- Use `textContent` for translated runtime content; no translation values may be rendered as HTML.
- All controls are keyboard accessible, expose labels/tooltips, and have clear focus styles.
- The layout remains usable at 320px and wide desktop widths without clipped controls, horizontal overflow, or overlapping content.
- The dark theme must use high-contrast text, surfaces, borders, inputs, and controls.

## Out of Scope

- Redesigning member or administrative pages.
- Changing backend APIs, validation rules, session behavior, consent persistence, or notification workflows.
- Changing production configuration or deploying the result.

## Validation

- Extend home-page assertions for the new preference controls and translation hooks.
- Run Ruff, Mypy, and the full pytest suite.
- Inspect the public page at desktop and mobile widths in light, dark, and system modes, including each supported language.
