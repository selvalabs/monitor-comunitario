const accessForm = document.querySelector("#member-access-form");
const memberStatus = document.querySelector("#member-status");
const memberPanel = document.querySelector("#member-panel");
const clearSessionButton = document.querySelector("#clear-member-session");
const memberNotifications = document.querySelector("#member-notifications");
const openDeleteButton = document.querySelector("#open-delete-member");
const deleteConfirmation = document.querySelector("#delete-member-confirmation");
const deleteAccessCode = document.querySelector("#delete-access-code");
const deleteCheck = document.querySelector("#delete-member-check");
const confirmDeleteButton = document.querySelector("#confirm-delete-member");
const cancelDeleteButton = document.querySelector("#cancel-delete-member");

const memberSessionKey = "monitor-comunitario:member-session";

function setMemberStatus(message, isError = false) {
  memberStatus.textContent = message;
  memberStatus.classList.toggle("error", isError);
}

function saveMemberSession(data) {
  window.sessionStorage.setItem(memberSessionKey, JSON.stringify(data));
}

function getMemberSession() {
  const rawValue = window.sessionStorage.getItem(memberSessionKey);

  if (!rawValue) {
    return null;
  }

  try {
    return JSON.parse(rawValue);
  } catch {
    return null;
  }
}

function clearMemberSession() {
  window.sessionStorage.removeItem(memberSessionKey);
  memberPanel.hidden = true;
  setMemberStatus("Você saiu desta sessão.");
}

function resetDeleteConfirmation() {
  deleteConfirmation.hidden = true;
  deleteAccessCode.value = "";
  deleteCheck.checked = false;
  confirmDeleteButton.disabled = true;
}

function updateDeleteButtonState() {
  confirmDeleteButton.disabled = !deleteCheck.checked || !deleteAccessCode.value.trim();
}
function buildNotificationSummary(notification) {
  const message = String(notification.message || "").trim();

  if (!message) {
    return "Aviso registrado para este endereço.";
  }

  const firstSentence = message.split(/(?<=[.!?])\s+/)[0];
  const summary = firstSentence.length <= 180 ? firstSentence : `${firstSentence.slice(0, 177)}...`;

  return summary || "Aviso registrado para este endereço.";
}

function renderNotifications(notifications) {
  memberNotifications.innerHTML = "";

  if (!notifications.length) {
    memberNotifications.innerHTML = "<div class=\"empty-state\">Não encontramos avisos para seu endereço.</div>";
    return;
  }

  for (const notification of notifications) {
    const card = document.createElement("article");
    card.className = "notification-card";

    const title = document.createElement("strong");
    title.textContent = notification.title;

    const date = document.createElement("small");
    date.textContent = new Date(notification.created_at).toLocaleString("pt-BR");

    const summary = document.createElement("p");
    summary.className = "notification-summary";
    summary.textContent = buildNotificationSummary(notification);

    const details = document.createElement("details");
    details.className = "notification-original";

    const detailsSummary = document.createElement("summary");
    detailsSummary.textContent = "Ver aviso original da Celesc";

    const message = document.createElement("p");
    message.textContent = notification.message || "Texto original indisponível.";

    details.append(detailsSummary, message);
    card.append(title, date, summary, details);
    memberNotifications.appendChild(card);
  }
}

function renderMemberSession(data) {
  const { user, notifications } = data;

  document.querySelector("#member-name").textContent = user.name;
  document.querySelector("#member-id").textContent = `#${user.id}`;
  document.querySelector("#member-municipality").textContent = user.municipality || "—";
  document.querySelector("#member-neighborhood").textContent = user.neighborhood || "—";
  document.querySelector("#member-street").textContent = user.street || "—";

  renderNotifications(notifications || []);
  memberPanel.hidden = false;
}

async function accessMemberArea(payload) {
  const response = await fetch("/member/access", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const body = await response.json();

  if (!response.ok) {
    throw new Error(body.detail || "Não foi possível acessar a área do morador.");
  }

  return body;
}

accessForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(accessForm);
  const payload = {
    phone: String(formData.get("phone") || "").trim(),
    access_code: String(formData.get("access_code") || "").trim(),
  };

  if (!payload.phone || !payload.access_code) {
    setMemberStatus("Informe telefone e código privado.", true);
    return;
  }

  setMemberStatus("Validando acesso...");

  try {
    const data = await accessMemberArea(payload);
    saveMemberSession(data);
    renderMemberSession(data);
    setMemberStatus("Acesso liberado para esta sessão do navegador.");
  } catch (error) {
    setMemberStatus(error.message, true);
    memberPanel.hidden = true;
  }
});

clearSessionButton.addEventListener("click", clearMemberSession);

openDeleteButton.addEventListener("click", () => {
  deleteConfirmation.hidden = false;
  deleteAccessCode.focus();
});

cancelDeleteButton.addEventListener("click", resetDeleteConfirmation);
deleteAccessCode.addEventListener("input", updateDeleteButtonState);
deleteCheck.addEventListener("change", updateDeleteButtonState);

confirmDeleteButton.addEventListener("click", async () => {
  const session = getMemberSession();
  if (!session?.user?.phone) {
    setMemberStatus("A sessão do morador expirou. Acesse novamente.", true);
    return;
  }

  confirmDeleteButton.disabled = true;
  setMemberStatus("Excluindo seus dados...");
  try {
    const response = await fetch("/member/account", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        phone: session.user.phone,
        access_code: deleteAccessCode.value.trim(),
      }),
    });
    if (!response.ok) {
      const body = await response.json();
      throw new Error(body.detail || "Não foi possível excluir o cadastro.");
    }
    clearMemberSession();
    resetDeleteConfirmation();
    setMemberStatus("Seu cadastro e seus dados foram excluídos.");
  } catch (error) {
    confirmDeleteButton.disabled = false;
    setMemberStatus(error.message, true);
  }
});

const storedSession = getMemberSession();

if (storedSession) {
  renderMemberSession(storedSession);
  setMemberStatus("Sessão restaurada neste navegador.");
} else {
  setMemberStatus("Informe telefone e código para acessar seus alertas.");
}
