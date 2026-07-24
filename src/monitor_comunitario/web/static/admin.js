const ADMIN_KEY_STORAGE_KEY = "monitor-comunitario-admin-api-key";

const elements = {
  form: document.querySelector("#admin-key-form"),
  keyInput: document.querySelector("#admin-api-key"),
  clearKeyButton: document.querySelector("#clear-admin-key"),
  refreshButton: document.querySelector("#refresh-dashboard"),
  runButton: document.querySelector("#run-monitoring"),
  status: document.querySelector("#dashboard-status"),
  apiStatus: document.querySelector("#api-status"),
  apiMeta: document.querySelector("#api-meta"),
  databaseStatus: document.querySelector("#database-status"),
  databaseMeta: document.querySelector("#database-meta"),
  schedulerStatus: document.querySelector("#scheduler-status"),
  schedulerMeta: document.querySelector("#scheduler-meta"),
  latestRunStatus: document.querySelector("#latest-run-status"),
  latestRunMeta: document.querySelector("#latest-run-meta"),
  metricNoticesFound: document.querySelector("#metric-notices-found"),
  metricNoticesCreated: document.querySelector("#metric-notices-created"),
  metricUsersChecked: document.querySelector("#metric-users-checked"),
  metricMatchesCreated: document.querySelector("#metric-matches-created"),
  metricNotificationsCreated: document.querySelector("#metric-notifications-created"),
  detailEnvironment: document.querySelector("#detail-environment"),
  detailTimezone: document.querySelector("#detail-timezone"),
  detailNotificationProvider: document.querySelector("#detail-notification-provider"),
  detailEvolutionEnabled: document.querySelector("#detail-evolution-enabled"),
  runId: document.querySelector("#run-id"),
  runStartedAt: document.querySelector("#run-started-at"),
  runFinishedAt: document.querySelector("#run-finished-at"),
  runErrorMessage: document.querySelector("#run-error-message"),
  runsTableBody: document.querySelector("#runs-table-body"),
  usersTableBody: document.querySelector("#users-table-body"),
};

function setStatus(message, variant = "info") {
  elements.status.textContent = message;
  elements.status.dataset.variant = variant;
}

function getAdminKey() {
  return sessionStorage.getItem(ADMIN_KEY_STORAGE_KEY) || "";
}

function setAdminKey(value) {
  sessionStorage.setItem(ADMIN_KEY_STORAGE_KEY, value.trim());
}

function clearAdminKey() {
  sessionStorage.removeItem(ADMIN_KEY_STORAGE_KEY);
  elements.keyInput.value = "";
}

function adminHeaders() {
  return {
    "X-Admin-API-Key": getAdminKey(),
  };
}

async function fetchJson(path, options = {}) {
  const response = await fetch(path, options);
  let payload = null;

  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail = payload?.detail || response.statusText || "Request failed";
    throw new Error(`${path}: ${response.status} ${detail}`);
  }

  return payload;
}

function formatValue(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  return String(value);
}

function formatDate(value) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("pt-BR");
}

function booleanLabel(value) {
  return value ? "sim" : "não";
}

function renderHealth(health) {
  elements.apiStatus.textContent = health.status || "ok";
  elements.apiMeta.textContent = `${formatValue(health.environment)} · ${formatValue(
    health.timezone,
  )}`;
}

function renderReadiness(readiness) {
  elements.databaseStatus.textContent = readiness.database || "ok";
  elements.databaseMeta.textContent = readiness.status || "ready";
}

function renderDiagnostics(diagnostics) {
  elements.schedulerStatus.textContent = diagnostics.scheduler.enabled ? "enabled" : "disabled";
  elements.schedulerMeta.textContent = `${diagnostics.scheduler.hour}:${String(
    diagnostics.scheduler.minute,
  ).padStart(2, "0")}`;

  elements.detailEnvironment.textContent = formatValue(diagnostics.environment);
  elements.detailTimezone.textContent = formatValue(diagnostics.timezone);
  elements.detailNotificationProvider.textContent = formatValue(diagnostics.notifications.provider);
  elements.detailEvolutionEnabled.textContent = booleanLabel(
    diagnostics.notifications.evolution_enabled,
  );

  renderLatestRun(diagnostics.latest_run);
}

function renderLatestRun(run) {
  if (!run) {
    elements.latestRunStatus.textContent = "no runs";
    elements.latestRunMeta.textContent = "sem execução registrada";
    elements.metricNoticesFound.textContent = "0";
    elements.metricNoticesCreated.textContent = "0";
    elements.metricUsersChecked.textContent = "0";
    elements.metricMatchesCreated.textContent = "0";
    elements.metricNotificationsCreated.textContent = "0";
    elements.runId.textContent = "—";
    elements.runStartedAt.textContent = "—";
    elements.runFinishedAt.textContent = "—";
    elements.runErrorMessage.textContent = "—";
    return;
  }

  elements.latestRunStatus.textContent = formatValue(run.status);
  elements.latestRunMeta.textContent = `run #${run.id}`;
  elements.metricNoticesFound.textContent = formatValue(run.notices_found);
  elements.metricNoticesCreated.textContent = formatValue(run.notices_created);
  elements.metricUsersChecked.textContent = formatValue(run.users_checked);
  elements.metricMatchesCreated.textContent = formatValue(run.matches_created);
  elements.metricNotificationsCreated.textContent = formatValue(run.notifications_created);
  elements.runId.textContent = formatValue(run.id);
  elements.runStartedAt.textContent = formatDate(run.started_at);
  elements.runFinishedAt.textContent = formatDate(run.finished_at);
  elements.runErrorMessage.textContent = run.error_message || "—";
}

function renderRunsTable(runs) {
  if (!runs.length) {
    elements.runsTableBody.innerHTML = '<tr><td colspan="6">Nenhuma execução registrada.</td></tr>';
    return;
  }

  elements.runsTableBody.innerHTML = runs
    .map(
      (run) => `
        <tr>
          <td>${run.id}</td>
          <td>${formatValue(run.status)}</td>
          <td>${formatDate(run.started_at)}</td>
          <td>${formatValue(run.notices_found)}</td>
          <td>${formatValue(run.matches_created)}</td>
          <td>${formatValue(run.notifications_created)}</td>
        </tr>
      `,
    )
    .join("");
}

function renderUsersTable(users) {
  if (!users.length) {
    elements.usersTableBody.innerHTML = '<tr><td colspan="6">Nenhum cadastro encontrado.</td></tr>';
    return;
  }

  elements.usersTableBody.innerHTML = users
    .map((user) => {
      const approved = Boolean(user.notifications_approved);
      const active = Boolean(user.is_active);
      const status = `${active ? "ativo" : "inativo"} · ${approved ? "aprovado" : "pendente"}`;
      const action = approved
        ? '<span class="muted-text">liberado</span>'
        : `<button class="button button-primary approve-user" type="button" data-user-id="${user.id}">Aprovar</button>`;

      return `
        <tr>
          <td>${user.id}</td>
          <td>${formatValue(user.name)}</td>
          <td>${formatValue(user.phone)}</td>
          <td>${formatValue(user.municipality)}</td>
          <td>${status}</td>
          <td>${action}</td>
        </tr>
      `;
    })
    .join("");
}

async function refreshDashboard() {
  setStatus("Atualizando dados operacionais...");

  const [health, readiness] = await Promise.all([fetchJson("/health"), fetchJson("/ready")]);
  renderHealth(health);
  renderReadiness(readiness);

  if (!getAdminKey()) {
    setStatus("Informe a chave administrativa para carregar diagnostics protegidos.", "warning");
    return;
  }

  const [diagnostics, runs] = await Promise.all([
    fetchJson("/admin/diagnostics", { headers: adminHeaders() }),
    fetchJson("/admin/runs?limit=10", { headers: adminHeaders() }),
  ]);
  const users = await fetchJson("/admin/users?include_inactive=true", {
    headers: adminHeaders(),
  });

  renderDiagnostics(diagnostics);
  renderRunsTable(runs);
  renderUsersTable(users);
  setStatus("Dashboard atualizado com sucesso.", "success");
}

async function approveUser(userId) {
  if (!getAdminKey()) {
    setStatus("Informe a chave administrativa antes de aprovar cadastros.", "warning");
    return;
  }

  await fetchJson(`/admin/users/${userId}`, {
    method: "PATCH",
    headers: {
      ...adminHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ notifications_approved: true }),
  });

  setStatus(`Cadastro #${userId} aprovado para notificações.`, "success");
  await refreshDashboard();
}

async function triggerManualRun() {
  if (!getAdminKey()) {
    setStatus("Informe a chave administrativa antes de rodar o monitoramento.", "warning");
    return;
  }

  const confirmed = window.confirm(
    "Rodar o monitoramento manual agora? Essa ação pode demorar durante a coleta.",
  );

  if (!confirmed) {
    return;
  }

  elements.runButton.disabled = true;
  setStatus("Executando monitoramento manual...");

  try {
    await fetchJson("/admin/runs/manual", {
      method: "POST",
      headers: adminHeaders(),
    });
    setStatus("Monitoramento manual concluído. Atualizando painel...", "success");
    await refreshDashboard();
  } finally {
    elements.runButton.disabled = false;
  }
}

function hydrateStoredKey() {
  const storedKey = getAdminKey();

  if (storedKey) {
    elements.keyInput.value = storedKey;
    setStatus("Chave administrativa carregada da sessão. Atualize o painel.");
  }
}

function bindEvents() {
  elements.form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setAdminKey(elements.keyInput.value);
    setStatus("Chave salva nesta sessão. Atualizando painel...", "success");
    await refreshDashboard();
  });

  elements.clearKeyButton.addEventListener("click", () => {
    clearAdminKey();
    setStatus("Chave removida desta sessão.", "warning");
  });

  elements.refreshButton.addEventListener("click", async () => {
    try {
      await refreshDashboard();
    } catch (error) {
      setStatus(error.message, "error");
    }
  });

  elements.runButton.addEventListener("click", async () => {
    try {
      await triggerManualRun();
    } catch (error) {
      setStatus(error.message, "error");
    }
  });

  elements.usersTableBody.addEventListener("click", async (event) => {
    const button = event.target.closest(".approve-user");

    if (!button) {
      return;
    }

    try {
      await approveUser(button.dataset.userId);
    } catch (error) {
      setStatus(error.message, "error");
    }
  });
}

hydrateStoredKey();
bindEvents();

refreshDashboard().catch((error) => {
  setStatus(error.message, "error");
});
