# Product Copy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the approved Portuguese product language across the resident journey and operational surfaces without changing behavior, routes, data, or legal obligations.

**Architecture:** Treat the approved copy map in `docs/superpowers/specs/2026-08-10-product-copy-guidelines.md` as the single editorial source. Apply it where copy is rendered: static HTML for first paint, JavaScript for runtime status, Python services for email and Hermes templates, and narrow assertions that guard the resident-critical promises.

**Tech Stack:** FastAPI, static HTML/CSS/JavaScript, Python services, pytest.

**Language rule:** All visible Portuguese copy introduced by this plan must use normal Brazilian
Portuguese accents in the source files. ASCII-only excerpts below identify the intended wording;
they are not a license to ship unaccented resident-facing text.

---

## File map

| File | Responsibility |
| --- | --- |
| `src/monitor_comunitario/web/static/index.html` | Portuguese first-paint copy for public registration and consent. |
| `src/monitor_comunitario/web/static/app.js` | Runtime registration, email verification, access-code, consent, and advertising status copy. |
| `src/monitor_comunitario/web/static/member.html` | Portuguese first-paint copy for member access and data deletion. |
| `src/monitor_comunitario/web/static/member.js` | Runtime member access, empty states, notification source label, and deletion status copy. |
| `src/monitor_comunitario/web/static/admin.html` | Compact operator-facing labels and instructions. |
| `src/monitor_comunitario/web/static/admin.js` | Runtime admin status, empty-state, and action copy. |
| `src/monitor_comunitario/services/email_verification.py` | Verification email subject and body. |
| `src/monitor_comunitario/services/hermes_catalog.py` | WhatsApp confirmation and completion templates. |
| `src/monitor_comunitario/web/static/privacy.html` | Plain-language privacy summary while preserving legal meaning. |
| `src/monitor_comunitario/web/static/terms.html` | Plain-language headings and resident-facing summaries while preserving legal meaning. |
| `src/monitor_comunitario/web/static/cookies.html` | Plain-language cookie and local-storage explanation. |
| `tests/unit/test_web_home.py` | Public and legal page content assertions. |
| `tests/unit/test_member_access.py` | Member page and notification-label assertions. |
| `tests/unit/test_email_verification_provider.py` | Outbound email subject/body assertions. |
| `tests/unit/test_hermes_catalog.py` | Deterministic WhatsApp template assertions. |
| `tests/unit/test_admin_dashboard.py` | Operator dashboard static/runtime copy assertions. |

## Task 1: Public registration and consent copy

**Files:**
- Modify: `src/monitor_comunitario/web/static/index.html`
- Modify: `src/monitor_comunitario/web/static/app.js`
- Modify: `tests/unit/test_web_home.py`

- [ ] **Step 1: Add failing public-copy assertions**

Add assertions that protect the main promise, confirmation order, and privacy wording:

```python
assert "Saiba sobre desligamentos programados perto de voce." in response.text
assert "Confirme seu e-mail" in response.text
assert "Usar apenas o necessario" in script_response.text
assert "cruzamento com bairro e rua" not in response.text
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `uv run pytest tests/unit/test_web_home.py -q`

Expected: failure because the previous public copy is still present.

- [ ] **Step 3: Replace first-paint public copy in `index.html`**

Apply the approved copy map exactly. The central section must read:

```html
<h1>Saiba sobre desligamentos programados perto de voce.</h1>
<p class="hero-copy">
  Cadastre seu endereco para receber avisos. Se ja tem cadastro, entre para consultar seus avisos.
</p>
```

Keep the source boundary explicit:

```html
<p class="disclaimer">
  Este e um servico independente. Consulte a Celesc para informacoes oficiais e atualizadas.
</p>
```

Replace the form introduction, three-step cards, access-code panel, existing-registration panel,
and consent labels using the values from the approved specification. Do not change form IDs,
attributes, links, route paths, or `data-i18n` keys.

- [ ] **Step 4: Replace runtime public copy in `app.js`**

Keep error behavior unchanged and replace only the resident-facing strings. Use these exact
messages for the confirmation path:

```javascript
setStatus("Enviamos um codigo para seu e-mail. Confirme-o para continuar.");
setStatus("E-mail confirmado. Agora responda a mensagem enviada no WhatsApp para concluir o cadastro.");
setStatus("Codigo copiado. Guarde-o para entrar na area do morador.");
```

Use the approved consent actions:

```javascript
rejectConsentButton.textContent = "Usar apenas o necessario";
acceptConsentButton.textContent = "Aceitar opcionais";
```

Do not translate non-Portuguese catalog values in this task. Their revision is intentionally out
of scope for issue #130.

- [ ] **Step 5: Run focused tests and inspect the diff**

Run: `uv run pytest tests/unit/test_web_home.py -q`

Expected: PASS.

Run: `git diff --check`

Expected: no output.

- [ ] **Step 6: Commit the public-copy slice**

```bash
git add src/monitor_comunitario/web/static/index.html src/monitor_comunitario/web/static/app.js tests/unit/test_web_home.py
git commit -m "feat(copy): simplify public registration language"
```

## Task 2: Email and WhatsApp confirmation copy

**Files:**
- Modify: `src/monitor_comunitario/services/email_verification.py`
- Modify: `src/monitor_comunitario/services/hermes_catalog.py`
- Modify: `tests/unit/test_email_verification_provider.py`
- Modify: `tests/unit/test_hermes_catalog.py`

- [ ] **Step 1: Add failing delivery-copy assertions**

Add assertions that verify the resident-facing delivery contract without asserting secrets:

```python
assert "Confirme seu cadastro no Monitor Comunitario" in payload["subject"]
assert "Ele vale por 48 horas." in payload["textContent"]
assert "Responda OK para confirmar ou CANCELAR para encerrar o cadastro." in template.body
```

- [ ] **Step 2: Run focused tests and verify they fail**

Run: `uv run pytest tests/unit/test_email_verification_provider.py tests/unit/test_hermes_catalog.py -q`

Expected: failure because the old subjects and templates are still present.

- [ ] **Step 3: Update the email sender in `email_verification.py`**

Keep recipient, `Message-ID`, provider payload, and expiration calculation unchanged. Set:

```python
message["Subject"] = "Confirme seu cadastro no Monitor Comunitario"
message.set_content(
    "Use este codigo para confirmar seu e-mail: "
    f"{otp}. Ele vale por {settings.email_verification_ttl_seconds // 3600} horas. "
    "Se voce nao iniciou este cadastro, ignore esta mensagem."
)
```

Use the same subject and body in the Brevo payload so SMTP and Brevo have identical copy.

- [ ] **Step 4: Update deterministic Hermes templates**

Preserve template keys and placeholders. Replace only `body` values:

```python
body=(
    "Oi, {name}. Voce quer receber avisos de desligamentos programados para o endereco "
    "cadastrado? Responda OK para confirmar ou CANCELAR para encerrar o cadastro. "
    "Esta confirmacao vale por {phone_confirmation_ttl_hours} horas."
)
```

For completion:

```python
body=(
    "Cadastro confirmado. Guarde seu codigo de acesso: {access_code}. "
    "Entre na area do morador para ver seus avisos: {url}"
)
```

- [ ] **Step 5: Run focused tests and inspect the diff**

Run: `uv run pytest tests/unit/test_email_verification_provider.py tests/unit/test_hermes_catalog.py -q`

Expected: PASS.

Run: `git diff --check`

Expected: no output.

- [ ] **Step 6: Commit the confirmation-copy slice**

```bash
git add src/monitor_comunitario/services/email_verification.py src/monitor_comunitario/services/hermes_catalog.py tests/unit/test_email_verification_provider.py tests/unit/test_hermes_catalog.py
git commit -m "feat(copy): clarify registration confirmations"
```

## Task 3: Member area copy

**Files:**
- Modify: `src/monitor_comunitario/web/static/member.html`
- Modify: `src/monitor_comunitario/web/static/member.js`
- Modify: `tests/unit/test_member_access.py`

- [ ] **Step 1: Add failing member-copy assertions**

Add assertions for the resident entry point and notice source label:

```python
assert "Seus avisos" in page_response.text
assert "Entrar" in page_response.text
assert "Ver aviso original da Celesc" in script_response.text
assert "Nao encontramos avisos para seu endereco." in script_response.text
```

- [ ] **Step 2: Run focused tests and verify they fail**

Run: `uv run pytest tests/unit/test_member_access.py -q`

Expected: failure because the previous labels are still present.

- [ ] **Step 3: Update first-paint copy in `member.html`**

Use the approved language without altering access controls:

```html
<h1>Seus avisos</h1>
<p>Entre com o telefone cadastrado e seu codigo de acesso.</p>
<h2 id="member-access-title">Entrar</h2>
<p>Voce recebeu este codigo ao confirmar o cadastro.</p>
```

Set the deletion section to `Excluir meus dados` and preserve its permanent-deletion warning.
Do not remove the code-entry or checkbox confirmation controls.

- [ ] **Step 4: Update runtime copy in `member.js`**

Use exact strings:

```javascript
memberNotifications.innerHTML = '<div class="empty-state">Nao encontramos avisos para seu endereco.</div>';
detailsSummary.textContent = "Ver aviso original da Celesc";
setMemberStatus("Voce saiu desta sessao.");
setMemberStatus("Seu cadastro e seus dados foram excluidos.");
```

Keep DOM construction and `textContent` usage intact; do not introduce new `innerHTML` for
untrusted values.

- [ ] **Step 5: Run focused tests and inspect the diff**

Run: `uv run pytest tests/unit/test_member_access.py -q`

Expected: PASS.

Run: `git diff --check`

Expected: no output.

- [ ] **Step 6: Commit the member-copy slice**

```bash
git add src/monitor_comunitario/web/static/member.html src/monitor_comunitario/web/static/member.js tests/unit/test_member_access.py
git commit -m "feat(copy): simplify member area language"
```

## Task 4: Compact admin language

**Files:**
- Modify: `src/monitor_comunitario/web/static/admin.html`
- Modify: `src/monitor_comunitario/web/static/admin.js`
- Modify: `tests/unit/test_admin_dashboard.py`

- [ ] **Step 1: Add failing admin-copy assertions**

Add assertions that protect concise operator labels:

```python
assert "Visao da operacao" in page_response.text
assert "Executar coleta agora" in page_response.text
assert "Cadastros pendentes" in page_response.text
assert "Acompanhe a coleta, os avisos e os cadastros pendentes." in page_response.text
```

- [ ] **Step 2: Run focused tests and verify they fail**

Run: `uv run pytest tests/unit/test_admin_dashboard.py -q`

Expected: failure because the previous admin labels are still present.

- [ ] **Step 3: Update static admin labels in `admin.html`**

Replace the dashboard title and action labels:

```html
<h1>Visao da operacao</h1>
<p>Acompanhe a coleta, os avisos e os cadastros pendentes.</p>
<span data-i18n="button.run_monitoring">Executar coleta agora</span>
```

Rename the pending-user section to `Cadastros pendentes` and shorten its instruction to
`Libere apenas cadastros confirmados.` Keep API, database, and event labels where they describe
real operator state.

- [ ] **Step 4: Update dynamic admin messages in `admin.js`**

Replace the resident-independent operational messages while preserving request paths and status
handling:

```javascript
appendTableMessage(elements.runsTableBody, 6, "Nenhuma coleta registrada.");
appendTableMessage(elements.usersTableBody, 6, "Nenhum cadastro encontrado.");
setStatus("Dados atualizados.", "success");
setStatus(`Cadastro #${userId} liberado para receber avisos.`, "success");
```

- [ ] **Step 5: Run focused tests and inspect the diff**

Run: `uv run pytest tests/unit/test_admin_dashboard.py -q`

Expected: PASS.

Run: `git diff --check`

Expected: no output.

- [ ] **Step 6: Commit the admin-copy slice**

```bash
git add src/monitor_comunitario/web/static/admin.html src/monitor_comunitario/web/static/admin.js tests/unit/test_admin_dashboard.py
git commit -m "feat(copy): streamline operational dashboard text"
```

## Task 5: Legal and cookie page clarity

**Files:**
- Modify: `src/monitor_comunitario/web/static/privacy.html`
- Modify: `src/monitor_comunitario/web/static/terms.html`
- Modify: `src/monitor_comunitario/web/static/cookies.html`
- Modify: `tests/unit/test_web_home.py`

- [ ] **Step 1: Add failing legal-summary assertions**

Add assertions that preserve the legal page routes while requiring plain public summaries:

```python
assert "Sua privacidade" in privacy_response.text
assert "Usamos apenas os dados necessarios" in privacy_response.text
assert "Cookies necessarios" in cookie_response.text
```

- [ ] **Step 2: Run focused tests and verify they fail**

Run: `uv run pytest tests/unit/test_web_home.py -q`

Expected: failure because the plain-language summaries are not yet present.

- [ ] **Step 3: Revise legal-page headings and summaries**

Keep every existing data category, retention statement, source disclaimer, and rights statement.
Add or replace only introductory summaries using this pattern:

```html
<p>
  Usamos apenas os dados necessarios para localizar sua regiao, mostrar avisos e manter seu cadastro.
</p>
```

For cookies, explain local storage without environment-variable names in the resident-facing body.
Keep `ADS_ENABLED` and `ANALYTICS_ENABLED` exactly as they are today in the existing technical
note, so the current technical disclosure and its test remain valid.

- [ ] **Step 4: Run focused tests and inspect legal meaning manually**

Run: `uv run pytest tests/unit/test_web_home.py -q`

Expected: PASS.

Review the diff and confirm it does not remove consent, deletion, retention, third-party, or
Celesc source disclaimers.

- [ ] **Step 5: Commit the legal-copy slice**

```bash
git add src/monitor_comunitario/web/static/privacy.html src/monitor_comunitario/web/static/terms.html src/monitor_comunitario/web/static/cookies.html tests/unit/test_web_home.py
git commit -m "docs(copy): clarify privacy and cookie pages"
```

## Task 6: Full regression and delivery

**Files:**
- Modify: `docs/agent/HANDOFF.md`

- [ ] **Step 1: Run static quality checks**

Run:

```powershell
uv run ruff check .
uv run mypy src
```

Expected: both commands exit with code 0.

- [ ] **Step 2: Run the complete test suite**

Run: `uv run pytest`

Expected: all tests pass.

- [ ] **Step 3: Perform manual resident-flow verification**

Verify in a browser or Playwright:

1. The public page makes no delivery guarantee and identifies Celesc as the official source.
2. Registration explains e-mail confirmation followed by WhatsApp confirmation.
3. The e-mail and WhatsApp strings state the 48-hour window.
4. Member access uses `codigo de acesso` consistently.
5. Deletion copy still communicates permanent deletion.
6. Admin labels remain actionable.

- [ ] **Step 4: Record the implementation handoff**

Append a concise `docs/agent/HANDOFF.md` entry with issue #130, PR links, commits, validation
commands and results, the Portuguese-only scope, and any remaining translation work. Do not
record credentials, personal data, or environment values.

- [ ] **Step 5: Commit the handoff**

```bash
git add docs/agent/HANDOFF.md
git commit -m "docs(agent): hand off product copy revision"
```

## Self-review

- Spec coverage: Tasks 1-5 cover every approved copy surface; Task 6 covers quality, resident
  flow verification, and continuity documentation.
- Scope: the plan does not modify behavior, schemas, route contracts, infrastructure, or
  translations outside Portuguese.
- Safety: confirmation templates retain their placeholders and TTL values; member rendering keeps
  existing safe `textContent` behavior.
- No placeholders: the copy changes and commands required by each task are explicit.
