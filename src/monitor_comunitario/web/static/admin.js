const CSRF_COOKIE_NAME = "monitor_admin_csrf";

function getCookieValue(name) {
  const prefix = `${name}=`;
  const cookie = document.cookie.split("; ").find((entry) => entry.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : "";
}

function withCsrf(options = {}) {
  const method = (options.method || "GET").toUpperCase();
  if (["GET", "HEAD", "OPTIONS"].includes(method)) {
    return options;
  }

  const csrfToken = getCookieValue(CSRF_COOKIE_NAME);
  return {
    ...options,
    headers: {
      ...(options.headers || {}),
      ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
    },
  };
}
async function fetchJson(path, options = {}) {
  const response = await fetch(path, withCsrf(options));
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

function clearTable(body) {
  body.replaceChildren();
}

function appendTableMessage(body, colspan, message) {
  const row = document.createElement("tr");
  const cell = document.createElement("td");
  cell.colSpan = colspan;
  cell.textContent = message;
  row.append(cell);
  body.append(row);
}

function appendTextCell(row, value) {
  const cell = document.createElement("td");
  cell.textContent = formatValue(value);
  row.append(cell);
}

function renderRunsTable(runs) {
  clearTable(elements.runsTableBody);

  if (!runs.length) {
    appendTableMessage(elements.runsTableBody, 6, "Nenhuma execução registrada.");
    return;
  }

  for (const run of runs) {
    const row = document.createElement("tr");
    appendTextCell(row, run.id);
    appendTextCell(row, run.status);
    appendTextCell(row, formatDate(run.started_at));
    appendTextCell(row, run.notices_found);
    appendTextCell(row, run.matches_created);
    appendTextCell(row, run.notifications_created);
    elements.runsTableBody.append(row);
  }
}

function renderUsersTable(users) {
  clearTable(elements.usersTableBody);

  if (!users.length) {
    appendTableMessage(elements.usersTableBody, 6, "Nenhum cadastro encontrado.");
    return;
  }

  for (const user of users) {
    const row = document.createElement("tr");
    const approved = Boolean(user.notifications_approved);
    const active = Boolean(user.is_active);
    const status = `${active ? "ativo" : "inativo"} · ${approved ? "aprovado" : "pendente"}`;

    appendTextCell(row, user.id);
    appendTextCell(row, user.name);
    appendTextCell(row, user.phone);
    appendTextCell(row, user.municipality);
    appendTextCell(row, status);

    const actionCell = document.createElement("td");
    if (approved) {
      const label = document.createElement("span");
      label.className = "muted-text";
      label.textContent = "liberado";
      actionCell.append(label);
    } else {
      const button = document.createElement("button");
      button.className = "button button-primary approve-user";
      button.type = "button";
      button.dataset.userId = String(user.id);
      button.textContent = "Aprovar";
      actionCell.append(button);
    }
    row.append(actionCell);
    elements.usersTableBody.append(row);
  }
}

function renderHermesEventsTable(events) {
  clearTable(elements.hermesEventsTableBody);

  if (!events.length) {
    appendTableMessage(elements.hermesEventsTableBody, 8, "Nenhum evento Hermes encontrado.");
    return;
  }

  for (const event of events) {
    const row = document.createElement("tr");
    appendTextCell(row, event.id);
    appendTextCell(row, event.event_type);
    appendTextCell(row, event.status);
    appendTextCell(row, event.channel);
    appendTextCell(row, event.intent);
    appendTextCell(row, event.template_key);
    appendTextCell(row, formatDate(event.created_at));

    const actionCell = document.createElement("td");
    const actionable = ["created", "queued"].includes(event.status);
    if (actionable) {
      const actions = document.createElement("div");
      actions.className = "table-actions";
      for (const [status, label, extraClass] of [
        ["processed", "Processado", "button-secondary"],
        ["escalated", "Escalar", "button-secondary button-danger-soft"],
      ]) {
        const button = document.createElement("button");
        button.className = "button " + extraClass + " mark-hermes-event";
        button.type = "button";
        button.dataset.eventId = String(event.id);
        button.dataset.status = status;
        button.textContent = label;
        actions.append(button);
      }
      actionCell.append(actions);
    } else {
      const label = document.createElement("span");
      label.className = "muted-text";
      label.textContent = "finalizado";
      actionCell.append(label);
    }
    row.append(actionCell);
    elements.hermesEventsTableBody.append(row);
  }
}

async function refreshDashboard() {
  setStatus("Atualizando dados operacionais...");

  const [health, readiness] = await Promise.all([fetchJson("/health"), fetchJson("/ready")]);
  renderHealth(health);
  renderReadiness(readiness);

  const [diagnostics, runs, hermesEvents] = await Promise.all([
    fetchJson("/admin/diagnostics", {}),
    fetchJson("/admin/runs?limit=10", {}),
    fetchJson("/admin/hermes/events?limit=10", {}),
  ]);
  const users = await fetchJson("/admin/users?include_inactive=true");

  renderDiagnostics(diagnostics);
  renderRunsTable(runs);
  renderUsersTable(users);
  renderHermesEventsTable(hermesEvents);
  setStatus("Dashboard atualizado com sucesso.", "success");
}

async function approveUser(userId) {

  await fetchJson(`/admin/users/${userId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ notifications_approved: true }),
  });

  setStatus(`Cadastro #${userId} aprovado para notificações.`, "success");
  await refreshDashboard();
}

async function updateHermesEventStatus(eventId, status) {

  await fetchJson(`/admin/hermes/events/${eventId}/status`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ status }),
  });

  setStatus(`Evento Hermes #${eventId} atualizado para ${status}.`, "success");
  await refreshDashboard();
}

async function triggerManualRun() {

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
    });
    setStatus("Monitoramento manual concluído. Atualizando painel...", "success");
    await refreshDashboard();
  } finally {
    elements.runButton.disabled = false;
  }
}

async function authenticateAdmin(value) {
  await fetchJson("/admin/session", {
    method: "POST",
    headers: {
      "X-Admin-API-Key": value.trim(),
    },
  });
  elements.keyInput.value = "";
  setStatus("Sessao administrativa iniciada. Atualizando painel...", "success");
  await refreshDashboard();
}

function bindEvents() {
  elements.form.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
      await authenticateAdmin(elements.keyInput.value);
    } catch (error) {
      setStatus(error.message, "error");
    }
  });

  elements.clearKeyButton.addEventListener("click", async () => {
    try {
      await fetchJson("/admin/session", { method: "DELETE" });
      elements.keyInput.value = "";
      setStatus("Sessao administrativa encerrada.", "warning");
    } catch (error) {
      setStatus(error.message, "error");
    }
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

  elements.hermesEventsTableBody.addEventListener("click", async (event) => {
    const button = event.target.closest(".mark-hermes-event");

    if (!button) {
      return;
    }

    try {
      await updateHermesEventStatus(button.dataset.eventId, button.dataset.status);
    } catch (error) {
      setStatus(error.message, "error");
    }
  });
}


bindEvents();

refreshDashboard().catch((error) => {
  setStatus(error.message, "error");
});
