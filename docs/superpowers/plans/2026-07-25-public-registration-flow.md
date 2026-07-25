# Public Registration Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify the public homepage around registration and member-area access without changing backend behavior.

**Architecture:** Keep this as a static frontend slice in the existing HTML/CSS/JS files. Use tests that assert the public page and JS expose the intended flow markers, then make minimal copy/layout updates.

**Tech Stack:** FastAPI static routes, plain HTML/CSS/JavaScript, pytest/TestClient.

---

### Task 1: Public Page Flow Markers

**Files:**
- Modify: `tests/unit/test_web_home.py`
- Modify: `src/monitor_comunitario/web/static/index.html`
- Modify: `src/monitor_comunitario/web/static/styles.css`

- [ ] **Step 1: Write the failing test**

Add assertions that the homepage contains the two path layout, explicit member access copy, no primary ID lookup language, and a stronger post-registration code panel.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_web_home.py -q`

Expected: FAIL because the new flow marker classes/copy do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Update the public page copy and layout classes. Preserve existing element IDs used by `app.js`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_web_home.py -q`

Expected: PASS.

### Task 2: Frontend Script Contract

**Files:**
- Modify: `tests/unit/test_web_home.py`
- Modify: `src/monitor_comunitario/web/static/app.js`

- [ ] **Step 1: Write the failing test**

Assert that public JS still uses `/users`, keeps `copyAccessCode`, and moves focus to the access-code panel after successful registration.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_web_home.py -q`

Expected: FAIL because focus handling does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Add focus support to the access-code panel without changing API payload or storage behavior.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_web_home.py -q`

Expected: PASS.

### Task 3: Verification and PR

**Files:**
- Modify: `.gitignore`
- Modify: `docs/superpowers/plans/2026-07-25-public-registration-flow.md`

- [ ] **Step 1: Run full validation**

Run:

```powershell
node --check src/monitor_comunitario/web/static/app.js
uv run ruff check .
uv run mypy src
uv run pytest
```

Expected: all pass.

- [ ] **Step 2: Commit and open PR**

Commit message: `style(ux): simplify public registration flow`

PR should close #56 and reference #25.
