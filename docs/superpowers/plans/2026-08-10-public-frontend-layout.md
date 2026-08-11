# Public Frontend Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a modern, accessible public registration page with compact icon preferences and complete public-page translation.

**Architecture:** Keep `index.html` as the semantic shell and retain each registration hook. Public text lives in `preferences.js`; static nodes use `data-i18n`, while `app.js` looks up runtime text through the same dictionary. CSS replaces the public card grid with open layout bands while preserving shared selectors for member and admin pages.

**Tech Stack:** FastAPI static files, vanilla HTML/CSS/JavaScript, pytest, Playwright.

---

### Task 1: Lock the public-page contract

**Files:**
- Modify: `tests/unit/test_web_home.py`
- Modify: `src/monitor_comunitario/web/static/index.html`

- [ ] Add failing assertions for `data-theme-option="system"`, `data-language-option="fr"`, `registration-layout`, and `data-i18n="public.hero.title"`.
- [ ] Run `uv run pytest tests/unit/test_web_home.py -q` and confirm the new assertions fail.
- [ ] Replace only the public shell, preserving the registration, consent, verification, access-code, and script IDs. Implement segmented icon buttons for theme and flag buttons for language.
- [ ] Re-run `uv run pytest tests/unit/test_web_home.py -q` and commit with `feat(web): modernize public page structure`.

### Task 2: Make preferences accessible and complete

**Files:**
- Modify: `tests/unit/test_web_home.py`
- Modify: `src/monitor_comunitario/web/static/preferences.js`

- [ ] Add failing assertions for public-page dictionary keys, preference button selectors, and `window.monitorTranslations`.
- [ ] Run `uv run pytest tests/unit/test_web_home.py -q` and confirm failure.
- [ ] Add translations for public copy, form labels, consent, footer, verification, and status text in `pt`, `en`, `es`, `fr`, and `zh`; expose a lookup that interpolates text values without HTML.
- [ ] Bind buttons to the existing storage preferences and synchronize `aria-pressed` state. Keep native selects as hidden compatibility controls.
- [ ] Re-run the focused test and commit with `feat(web): translate public registration experience`.

### Task 3: Translate runtime feedback and restyle the public page

**Files:**
- Modify: `tests/unit/test_web_home.py`
- Modify: `src/monitor_comunitario/web/static/app.js`
- Modify: `src/monitor_comunitario/web/static/styles.css`

- [ ] Add a failing assertion for calls such as `translate("public.status.submitting")` and `translate("public.access.unavailable")`.
- [ ] Run the focused test and confirm failure.
- [ ] Replace hard-coded public runtime messages with the shared dictionary, excluding server-provided error details.
- [ ] Create public-only open layout bands, a flat responsive service-step strip, stable icon controls, visible focus states, and high-contrast dark colors. Do not alter member/admin layout selectors.
- [ ] Re-run the focused test and commit with `feat(web): refine public registration experience`.

### Task 4: Verify behavior and responsive presentation

**Files:**
- Modify: `docs/agent/HANDOFF.md`

- [ ] Run `uv run ruff check .`, `uv run mypy src`, and `uv run pytest`.
- [ ] Run local browser checks at 1440px and 390px for light, dark, system, and all five languages; verify no clipped controls, overlap, or horizontal scroll.
- [ ] Record issue `#133`, PR, validation, and deferred privacy blocker `#132` in the handoff.
- [ ] Commit with `docs(agent): record public frontend delivery`.
