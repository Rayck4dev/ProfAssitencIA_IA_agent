/* =========================================================
   ProfAssistenc IA
   Application Logic
   ========================================================= */

/* =========================================================
   CONFIG
   ========================================================= */

const API_BASE = window.PROFASSISTENC_API_URL || "";

/* =========================================================
   DOM
   ========================================================= */

const chatArea = document.getElementById("chat-area");
const input = document.getElementById("message-input");
const sendButton = document.getElementById("btn-send");
const charCount = document.getElementById("char-count");
const historyList = document.getElementById("history-list");
const conversationTitle = document.getElementById("conversation-title");
const saveStatus = document.getElementById("save-status");
const historyPanel = document.getElementById("history-panel");
const renameModal = document.getElementById("rename-modal");
const renameInput = document.getElementById("rename-input");
const backendStatus = document.getElementById("backend-status");
const backendStatusDot = document.getElementById("backend-status-dot");
const backendStatusLabel = document.getElementById("backend-status-label");

const initialChatHTML = chatArea ? chatArea.innerHTML : "";

/* =========================================================
   STATE
   ========================================================= */

let currentConversationId = null;
let messages = [];
let isGenerating = false;
let renameConversationId = null;

/* =========================================================
   INSTALLATION ID
   ========================================================= */

function getInstallationId() {
  const key = "profassistenc_installation_id";

  let id = localStorage.getItem(key);

  if (!id) {
    if (window.crypto && crypto.randomUUID) {
      id = crypto.randomUUID();
    } else {
      id = "local-" + Date.now() + "-" + Math.random().toString(36).slice(2);
    }

    localStorage.setItem(key, id);
  }

  return id;
}

const installationId = getInstallationId();

/* =========================================================
   UTILS
   ========================================================= */

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

function setStatus(text, visible = true) {
  if (!saveStatus) return;

  saveStatus.textContent = text;
  saveStatus.classList.toggle("hidden", !visible);
}

function setBackendStatus(connected) {
  if (!backendStatus || !backendStatusDot || !backendStatusLabel) {
    return;
  }

  backendStatus.classList.toggle("border-emerald-500/20", connected);

  backendStatus.classList.toggle("text-emerald-300", connected);

  backendStatus.classList.toggle("border-rose-500/20", !connected);

  backendStatus.classList.toggle("text-rose-300", !connected);

  backendStatus.style.borderColor = connected
    ? "rgba(16, 185, 129, 0.2)"
    : "rgba(244, 63, 94, 0.2)";

  backendStatus.style.color = connected ? "#6ee7b7" : "#fda4af";

  backendStatusDot.style.backgroundColor = connected ? "#34d399" : "#fb7185";

  backendStatusDot.style.boxShadow = connected
    ? "0 0 8px #34d399"
    : "0 0 8px #fb7185";

  backendStatusLabel.textContent = connected ? "API conectada" : "API offline";
}

function scrollChat() {
  requestAnimationFrame(() => {
    if (chatArea) {
      chatArea.scrollTop = chatArea.scrollHeight;
    }
  });
}

function formatConversationDate(dateString) {
  if (!dateString) {
    return "";
  }

  const date = new Date(dateString);

  if (Number.isNaN(date.getTime())) {
    return dateString;
  }

  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/* =========================================================
   MESSAGES
   ========================================================= */

function addMessage(role, content, temporary = false) {
  const welcome = document.getElementById("welcome-state");

  if (welcome) {
    welcome.remove();
  }

  const wrapper = document.createElement("div");

  const isUser = role === "user";

  wrapper.className = isUser ? "flex justify-end" : "flex justify-start";

  wrapper.innerHTML = `
    <div
      class="${
        isUser ? "message-user" : "message-ai"
      } max-w-[88%] sm:max-w-[78%] rounded-2xl px-4 py-3"
    >

      <div class="flex items-center gap-2 mb-1.5">

        <div
          class="
            w-6
            h-6
            rounded-lg
            ${
              isUser
                ? "bg-indigo-500/15 text-indigo-300"
                : "bg-purple-500/15 text-purple-300"
            }
            flex
            items-center
            justify-center
          "
        >
          <i
            data-lucide="${isUser ? "user-round" : "sparkles"}"
            class="w-3.5 h-3.5"
          ></i>
        </div>

        <span
          class="
            text-[9px]
            uppercase
            tracking-wider
            font-bold
            ${isUser ? "text-indigo-300" : "text-purple-300"}
          "
        >
          ${isUser ? "Você" : "ProfAssistenc_IA"}
        </span>

      </div>

      <div
        class="
          text-xs
          sm:text-sm
          text-slate-300
          leading-relaxed
          message-content
        "
      >
        ${isUser ? escapeHtml(content) : renderMarkdown(content)}
      </div>

    </div>
  `;

  if (temporary) {
    wrapper.dataset.temporary = "true";
  }

  chatArea.appendChild(wrapper);

  if (window.lucide) {
    lucide.createIcons();
  }

  scrollChat();

  return wrapper;
}

/* =========================================================
   LOADING
   ========================================================= */

function addLoading() {
  const wrapper = document.createElement("div");

  wrapper.className = "flex justify-start";
  wrapper.dataset.temporary = "true";

  wrapper.innerHTML = `
    <div
      class="
        message-ai
        max-w-[88%]
        sm:max-w-[78%]
        rounded-2xl
        px-4
        py-3
      "
    >

      <div class="flex items-center gap-2 mb-1.5">

        <div
          class="
            w-6
            h-6
            rounded-lg
            bg-purple-500/15
            text-purple-300
            flex
            items-center
            justify-center
          "
        >
          <i
            data-lucide="sparkles"
            class="w-3.5 h-3.5"
          ></i>
        </div>

        <span
          class="
            text-[9px]
            uppercase
            tracking-wider
            font-bold
            text-purple-300
          "
        >
          ProfAssistenc_IA
        </span>

      </div>

      <div
        class="
          flex
          items-center
          gap-2
          text-xs
          text-slate-500
        "
      >
        Preparando seu planejamento

        <span class="typing-dots">
          <span></span>
          <span></span>
          <span></span>
        </span>
      </div>

    </div>
  `;

  chatArea.appendChild(wrapper);

  if (window.lucide) {
    lucide.createIcons();
  }

  scrollChat();

  return wrapper;
}

/* =========================================================
   CONVERSATION TITLE
   ========================================================= */

function updateConversationTitle(firstMessage) {
  if (!firstMessage || !conversationTitle) {
    return;
  }

  const clean = firstMessage.replace(/\s+/g, " ").trim();

  conversationTitle.textContent =
    clean.length > 48 ? clean.slice(0, 48) + "…" : clean;
}

/* =========================================================
   WELCOME
   ========================================================= */

function getWelcomeHTML() {
  return `
    <div
      id="welcome-state"
      class="
        min-h-full
        flex
        items-center
        justify-center
        py-10
      "
    >

      <div class="max-w-2xl text-center">

        <div
          class="
            mx-auto
            w-14
            h-14
            rounded-2xl
            bg-gradient-to-br
            from-indigo-500/20
            to-purple-500/20
            border
            border-indigo-400/15
            flex
            items-center
            justify-center
            mb-5
            shadow-glow
          "
        >
          <i
            data-lucide="sparkles"
            class="w-7 h-7 text-indigo-300"
          ></i>
        </div>

        <p
          class="
            text-[10px]
            uppercase
            tracking-[.2em]
            font-bold
            text-indigo-400
            mb-2
          "
        >
          Assistente de Planejamento Docente
        </p>

        <h3
          class="
            text-2xl
            sm:text-3xl
            font-black
            tracking-tight
            text-white
          "
        >
          Vamos planejar sua aula?
        </h3>

        <p
          class="
            text-xs
            sm:text-sm
            text-slate-500
            mt-3
            max-w-lg
            mx-auto
            leading-relaxed
          "
        >
          Descreva o que você precisa para sua aula.
          O ProfAssistenc IA ajuda a transformar sua ideia
          em um planejamento claro, organizado e adequado
          à sua turma.
        </p>

        <div
          class="
            grid
            grid-cols-1
            sm:grid-cols-3
            gap-2.5
            mt-7
          "
        >

          <!-- SUGESTÃO 1 -->

          <button
            type="button"
            class="
              suggestion
              rounded-xl
              border
              border-slate-800
              bg-slate-900/50
              p-3
              text-left
              hover:border-indigo-400/30
              hover:bg-indigo-500/5
              transition
            "
            data-suggestion="Crie um plano de aula de Matemática sobre equações do 2º grau para o 1º ano do Ensino Médio, com objetivo, habilidades, conteúdos, metodologia, recursos, desenvolvimento e avaliação."
          >

            <i
              data-lucide="calculator"
              class="w-4 h-4 text-indigo-400 mb-2"
            ></i>

            <p
              class="
                text-[11px]
                font-semibold
                text-slate-300
              "
            >
              Plano completo
            </p>

            <p
              class="
                text-[9px]
                text-slate-600
                mt-1
              "
            >
              Estrutura detalhada
            </p>

          </button>

          <!-- SUGESTÃO 2 -->

          <button
            type="button"
            class="
              suggestion
              rounded-xl
              border
              border-slate-800
              bg-slate-900/50
              p-3
              text-left
              hover:border-indigo-400/30
              hover:bg-indigo-500/5
              transition
            "
            data-suggestion="Crie um plano de aula de Ciências sobre fotossíntese para uma turma do Ensino Fundamental II, incluindo uma atividade prática, os materiais necessários, o passo a passo e uma forma de avaliação."
          >

            <i
              data-lucide="flask-conical"
              class="w-4 h-4 text-indigo-400 mb-2"
            ></i>

            <p
              class="
                text-[11px]
                font-semibold
                text-slate-300
              "
            >
              Aula prática
            </p>

            <p
              class="
                text-[9px]
                text-slate-600
                mt-1
              "
            >
              Aprender fazendo
            </p>

          </button>

          <!-- SUGESTÃO 3 -->

          <button
            type="button"
            class="
              suggestion
              rounded-xl
              border
              border-slate-800
              bg-slate-900/50
              p-3
              text-left
              hover:border-indigo-400/30
              hover:bg-indigo-500/5
              transition
            "
            data-suggestion="Crie um plano de aula de História sobre a Revolução Industrial para uma aula de 50 minutos, utilizando uma abordagem dinâmica e participativa, com objetivos, conteúdos, desenvolvimento, recursos e avaliação."
          >

            <i
              data-lucide="landmark"
              class="w-4 h-4 text-indigo-400 mb-2"
            ></i>

            <p
              class="
                text-[11px]
                font-semibold
                text-slate-300
              "
            >
              Aula dinâmica
            </p>

            <p
              class="
                text-[9px]
                text-slate-600
                mt-1
              "
            >
              Participação e interação
            </p>

          </button>

        </div>

      </div>

    </div>
  `;
}

/* =========================================================
   MARKDOWN
   ========================================================= */

function renderMarkdown(content) {
  if (!content) {
    return "";
  }

  let normalized = String(content);

  /*
    Remove escapes desnecessários do Markdown.
    Mantém a estrutura original da resposta.
  */

  normalized = normalized
    .replace(/\\([*_#>\-])/g, "$1")
    .replace(/\\\[/g, "[")
    .replace(/\\\]/g, "]");

  if (typeof marked === "undefined" || typeof DOMPurify === "undefined") {
    return escapeHtml(normalized).replace(/\n/g, "<br>");
  }

  const html = marked.parse(normalized);

  const container = document.createElement("div");

  container.innerHTML = DOMPurify.sanitize(html);

  /*
    Renderização de fórmulas matemáticas.
  */

  if (typeof renderMathInElement === "function") {
    try {
      renderMathInElement(container, {
        delimiters: [
          {
            left: "$$",
            right: "$$",
            display: true,
          },
          {
            left: "\\(",
            right: "\\)",
            display: false,
          },
          {
            left: "\\[",
            right: "\\]",
            display: true,
          },
          {
            left: "$",
            right: "$",
            display: false,
          },
        ],
        throwOnError: false,
      });
    } catch (error) {
      console.warn("Não foi possível renderizar matemática:", error);
    }
  }

  return container.innerHTML;
}

/* =========================================================
   RESET CHAT
   ========================================================= */

function resetChat() {
  currentConversationId = null;
  messages = [];

  if (conversationTitle) {
    conversationTitle.textContent = "Nova conversa";
  }

  setStatus("Pronto");

  if (chatArea) {
    chatArea.innerHTML = initialChatHTML;
    chatArea.scrollTop = 0;
  }

  document.querySelectorAll(".history-item").forEach((item) => {
    item.classList.remove("active");
  });

  if (input) {
    input.value = "";
    input.disabled = false;
  }

  if (charCount) {
    charCount.textContent = "0";
  }

  if (sendButton) {
    sendButton.disabled = true;
  }

  if (window.lucide) {
    lucide.createIcons();
  }

  attachSuggestionEvents();

  if (input) {
    input.focus();
  }
}
/* =========================================================
   SUGGESTIONS
   ========================================================= */

function attachSuggestionEvents() {
  document.querySelectorAll(".suggestion").forEach((button) => {
    button.addEventListener("click", () => {
      input.value = button.dataset.suggestion || "";

      input.dispatchEvent(
        new Event("input", {
          bubbles: true,
        }),
      );

      input.focus();
    });
  });
}

/* =========================================================
   INPUT
   ========================================================= */

input.addEventListener("input", () => {
  if (input.value.length > 2000) {
    input.value = input.value.slice(0, 2000);
  }

  charCount.textContent = input.value.length;

  sendButton.disabled = !input.value.trim() || isGenerating;
  
});


/* =========================================================
   KEYBOARD
   ========================================================= */

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();

    if (!sendButton.disabled) {
      sendMessage();
    }
  }
});
   

/* =========================================================
   SEND MESSAGE
   ========================================================= */

async function sendMessage() {
  console.trace("SENDMESSAGE FOI CHAMADA");
  const content = input.value.trim();

  if (!content || isGenerating) {
    return;
  }

  isGenerating = true;

  sendButton.disabled = true;
  input.disabled = true;
  
  /* USER MESSAGE */

  addMessage("user", content);

  messages.push({
    role: "user",
    content,
  });

  if (messages.length === 1) {
    updateConversationTitle(content);
  }

  setStatus("Gerando…");

  /* LOADING */

  const loading = addLoading();

  try {
    console.log("Conversation ID enviado:", currentConversationId);

    console.log("Mensagens enviadas:", messages);

    const response = await fetch(`${API_BASE}/api/LessonPlan`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        installation_id: installationId,
        conversation_id: currentConversationId,
        message: content,
        messages,
      }),
    });

    if (!response.ok) {
      const errorBody = await response.text();

      throw new Error(
        errorBody || `Backend respondeu com HTTP ${response.status}.`,
      );
    }

    const data = await response.json();

    input.value = "";

    console.log("Resposta da API:", data);

    console.log("Conversation ID recebido:", data.conversationId);

    loading.remove();

    const result = data.response || "Não foi possível gerar uma resposta.";

    /* AI MESSAGE */

    addMessage("assistant", result);

    messages.push({
      role: "assistant",
      content: result,
    });

    if (data.conversationId) {
      currentConversationId = data.conversationId;
    }

    setStatus("Salvo");

    await loadHistory();
  } catch (error) {
    console.error("Erro ao enviar mensagem:", error);

    loading.remove();

    messages.pop();

    const fallback = `
    Não foi possível gerar o planejamento agora.

    Verifique sua conexão e tente novamente em alguns instantes.
  `.trim();

    addMessage("assistant", fallback);

    setBackendStatus(false);
    setStatus("Não foi possível conectar");
  } finally {
    isGenerating = false;

    input.disabled = false;

    input.focus();

    
    sendButton.disabled = !input.value.trim();
  }
}

/* =========================================================
   SEND BUTTON
   ========================================================= */

sendButton.addEventListener("click", sendMessage);

/* =========================================================
   NEW CONVERSATION
   ========================================================= */

const newConversationButton = document.getElementById("btn-sidebar-new");

if (newConversationButton) {
  newConversationButton.addEventListener("click", () => {
    resetChat();
    closeHistory();
  });
}

/* =========================================================
   COPY CONVERSATION
   ========================================================= */

const copyButton = document.getElementById("btn-copy");

if (copyButton) {
  copyButton.addEventListener("click", async () => {
    const text = messages
      .map(
        (message) =>
          `${
            message.role === "user" ? "Você" : "ProfAssistenc_IA"
          }:\n${message.content}`,
      )
      .join("\n\n");

    if (!text) {
      setStatus("Nada para copiar");

      setTimeout(() => {
        setStatus("Pronto");
      }, 1800);

      return;
    }

    try {
      await navigator.clipboard.writeText(text);

      setStatus("Conversa copiada");

      setTimeout(() => {
        setStatus("Pronto");
      }, 1800);
    } catch (error) {
      console.error(error);

      setStatus("Não foi possível copiar");
    }
  });
}

/* =========================================================
   LOAD HISTORY
   ========================================================= */

async function loadHistory() {
  try {
    const response = await fetch(
      `${API_BASE}/api/conversations?installation_id=${encodeURIComponent(
        installationId,
      )}`,
    );

    if (!response.ok) {
      setBackendStatus(false);
      return;
    }

    const data = await response.json();

    setBackendStatus(true);

    renderHistory(data.conversations || []);
  } catch (error) {
    console.error("Erro ao carregar histórico:", error);

    setBackendStatus(false);

    /*
      chat offline.
      O chat continua funcionando.
    */
  }
}

/* =========================================================
   RENDER HISTORY
   ========================================================= */

function renderHistory(conversations) {
  if (!historyList) {
    return;
  }

  if (!conversations.length) {
    historyList.innerHTML = `
      <div
        class="
          empty-history
          rounded-xl
          p-4
          text-center
          mt-1
        "
      >

        <i
          data-lucide="messages-square"
          class="
            w-6
            h-6
            text-slate-600
            mx-auto
            mb-2
          "
        ></i>

        <p
          class="
            text-[11px]
            text-slate-500
          "
        >
          Nenhuma conversa ainda.
        </p>

        <p
          class="
            text-[10px]
            text-slate-600
            mt-1
          "
        >
          A primeira aparecerá aqui.
        </p>

      </div>
    `;

    if (window.lucide) {
      lucide.createIcons();
    }

    return;
  }

  historyList.innerHTML = conversations
    .map((conversation) => {
      const id = String(conversation.id);

      return `
          <div
            class="
              history-item
              rounded-xl
              p-3
              ${id === String(currentConversationId) ? "active" : ""}
            "
            data-id="${escapeHtml(id)}"
          >

            <button
              type="button"
              class="
                history-open
                w-full
                text-left
                pr-14
              "
            >

              <div
                class="
                  flex
                  items-start
                  gap-2.5
                "
              >

                <i
                  data-lucide="message-square"
                  class="
                    w-4
                    h-4
                    text-slate-500
                    mt-0.5
                    shrink-0
                  "
                ></i>

                <div
                  class="min-w-0"
                >

                  <p
                    class="
                      text-[11px]
                      font-semibold
                      text-slate-300
                      truncate
                    "
                  >
                    ${escapeHtml(conversation.title || "Nova conversa")}
                  </p>

                  <p
                    class="
                      text-[9px]
                      text-slate-600
                      mt-1
                    "
                  >
                    ${escapeHtml(
                      formatConversationDate(conversation.updatedAt),
                    )}
                  </p>

                </div>

              </div>

            </button>

            <div
              class="history-actions"
            >

              <button
                type="button"
                class="
                  history-action
                  rename
                "
                title="Renomear"
                aria-label="Renomear conversa"
              >
                <i
                  data-lucide="pencil"
                  class="w-3.5 h-3.5"
                ></i>
              </button>

              <button
                type="button"
                class="
                  history-action
                  delete
                "
                title="Excluir"
                aria-label="Excluir conversa"
              >
                <i
                  data-lucide="trash-2"
                  class="w-3.5 h-3.5"
                ></i>
              </button>

            </div>

          </div>
        `;
    })
    .join("");

  if (window.lucide) {
    lucide.createIcons();
  }

  /* EVENTS */

  historyList.querySelectorAll(".history-item").forEach((item) => {
    const id = item.dataset.id;

    const openButton = item.querySelector(".history-open");

    const renameButton = item.querySelector(".rename");

    const deleteButton = item.querySelector(".delete");

    openButton.addEventListener("click", () => {
      loadConversation(id);
    });

    renameButton.addEventListener("click", (event) => {
      event.stopPropagation();

      const titleElement = item.querySelector(".history-open p");

      const title = titleElement?.textContent || "Nova conversa";

      openRenameModal(id, title);
    });

    deleteButton.addEventListener("click", async (event) => {
      event.stopPropagation();

      await deleteConversation(id);
    });
  });
}

/* =========================================================
   LOAD CONVERSATION
   ========================================================= */

async function loadConversation(id) {
  try {
    setStatus("Carregando conversa…");

    const response = await fetch(
      `${API_BASE}/api/conversations/${encodeURIComponent(
        id,
      )}?installation_id=${encodeURIComponent(installationId)}`,
    );

    if (!response.ok) {
      throw new Error("Não foi possível carregar a conversa.");
    }

    const data = await response.json();

    currentConversationId = data.conversationId || id;

    messages = data.messages || [];

    conversationTitle.textContent = data.title || "Conversa";

    chatArea.innerHTML = "";

    messages.forEach((message) => {
      addMessage(message.role, message.content);
    });

    document.querySelectorAll(".history-item").forEach((item) => {
      item.classList.toggle("active", item.dataset.id === String(id));
    });

    setStatus("Histórico restaurado");

    closeHistory();

    input.focus();
  } catch (error) {
    console.error(error);

    setStatus("Não foi possível restaurar");
  }
}

/* =========================================================
   RENAME MODAL
   ========================================================= */

function openRenameModal(id, title) {
  renameConversationId = id;

  renameInput.value = title || "";

  renameModal.classList.remove("hidden");

  setTimeout(() => {
    renameInput.focus();
    renameInput.select();
  }, 50);
}

function closeRenameModal() {
  renameConversationId = null;

  renameModal.classList.add("hidden");

  renameInput.value = "";
}

/* =========================================================
   RENAME CONVERSATION
   ========================================================= */

async function renameConversation() {
  const title = renameInput.value.trim();

  if (!renameConversationId) {
    return;
  }

  if (!title) {
    renameInput.focus();
    return;
  }

  try {
    const response = await fetch(
      `${API_BASE}/api/conversations/${encodeURIComponent(
        renameConversationId,
      )}`,
      {
        method: "PATCH",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          installation_id: installationId,

          title: title.slice(0, 80),
        }),
      },
    );

    if (!response.ok) {
      throw new Error("Não foi possível renomear.");
    }

    const data = await response.json();

    if (String(renameConversationId) === String(currentConversationId)) {
      conversationTitle.textContent = data.title || title;
    }

    closeRenameModal();

    setStatus("Conversa renomeada");

    await loadHistory();

    setTimeout(() => {
      setStatus("Pronto");
    }, 1800);
  } catch (error) {
    console.error(error);

    setStatus("Erro ao renomear");
  }
}

/* =========================================================
   DELETE CONVERSATION
   ========================================================= */

async function deleteConversation(id) {
  const confirmed = window.confirm(
    "Excluir esta conversa?\n\nEssa ação não poderá ser desfeita.",
  );

  if (!confirmed) {
    return;
  }

  try {
    const response = await fetch(
      `${API_BASE}/api/conversations/${encodeURIComponent(
        id,
      )}?installation_id=${encodeURIComponent(installationId)}`,
      {
        method: "DELETE",
      },
    );

    if (!response.ok) {
      throw new Error("Não foi possível excluir.");
    }

    if (String(id) === String(currentConversationId)) {
      resetChat();
    }

    setStatus("Conversa excluída");

    await loadHistory();

    setTimeout(() => {
      setStatus("Pronto");
    }, 1800);
  } catch (error) {
    console.error(error);

    setStatus("Erro ao excluir");
  }
}

/* =========================================================
   RENAME EVENTS
   ========================================================= */

const renameConfirm = document.getElementById("rename-confirm");

const renameCancel = document.getElementById("rename-cancel");

const renameClose = document.getElementById("rename-close");

if (renameConfirm) {
  renameConfirm.addEventListener("click", renameConversation);
}

if (renameCancel) {
  renameCancel.addEventListener("click", closeRenameModal);
}

if (renameClose) {
  renameClose.addEventListener("click", closeRenameModal);
}

renameInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    renameConversation();
  }

  if (event.key === "Escape") {
    closeRenameModal();
  }
});

/* =========================================================
   MODAL OUTSIDE CLICK
   ========================================================= */

renameModal.addEventListener("click", (event) => {
  if (event.target === renameModal) {
    closeRenameModal();
  }
});

/* =========================================================
   MOBILE HISTORY
   ========================================================= */

function openHistory() {
  if (!historyPanel) {
    return;
  }

  historyPanel.classList.remove("-translate-x-full");
}

function closeHistory() {
  if (!historyPanel || window.innerWidth >= 1024) {
    return;
  }

  historyPanel.classList.add("-translate-x-full");
}

const mobileHistoryButton = document.getElementById("btn-history-mobile");

const closeHistoryButton = document.getElementById("btn-close-history");

if (mobileHistoryButton) {
  mobileHistoryButton.addEventListener("click", openHistory);
}

if (closeHistoryButton) {
  closeHistoryButton.addEventListener("click", closeHistory);
}

/* =========================================================
   ESCAPE
   ========================================================= */

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") {
    return;
  }

  if (renameModal && !renameModal.classList.contains("hidden")) {
    closeRenameModal();
  }
});

/* =========================================================
   INITIALIZATION
   ========================================================= */

function initializeApp() {
  if (window.lucide) {
    lucide.createIcons();
  }

  attachSuggestionEvents();

  loadHistory();

  if (input) {
    input.focus();
  }
}

initializeApp();
