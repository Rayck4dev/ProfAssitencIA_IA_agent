/* =========================================================
   ProfAssistenc IA
   Application Logic
   ========================================================= */

/* =========================================================
   CONFIG
   ========================================================= */

const API_BASE = "https://localhost:7142";

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
  saveStatus.textContent = text;

  saveStatus.classList.toggle("hidden", !visible);
}

function scrollChat() {
  requestAnimationFrame(() => {
    chatArea.scrollTop = chatArea.scrollHeight;
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

  wrapper.className =
    role === "user" ? "flex justify-end" : "flex justify-start";

  const isUser = role === "user";

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
          ${isUser ? "Você" : "ProfAssistenc IA"}
        </span>

      </div>


      <div
        class="text-xs sm:text-sm text-slate-300 leading-relaxed message-content"
      >
         ${isUser ? escapeHtml(content) : renderMarkdown(content)}
      </div>

    </div>
  `;

  if (temporary) {
    wrapper.dataset.temporary = "true";
  }

  chatArea.appendChild(wrapper);

  lucide.createIcons();

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
      class="message-ai max-w-[88%] sm:max-w-[78%] rounded-2xl px-4 py-3"
    >

      <div
        class="flex items-center gap-2 mb-1.5"
      >

        <div
          class="w-6 h-6 rounded-lg bg-purple-500/15 text-purple-300 flex items-center justify-center"
        >

          <i
            data-lucide="sparkles"
            class="w-3.5 h-3.5"
          ></i>

        </div>


        <span
          class="text-[9px] uppercase tracking-wider font-bold text-purple-300"
        >
          ProfAssistenc IA
        </span>

      </div>


      <div
        class="flex items-center gap-2 text-xs text-slate-500"
      >

        Gerando seu planejamento

        <span class="typing-dots">
          <span></span>
          <span></span>
          <span></span>
        </span>

      </div>

    </div>
  `;

  chatArea.appendChild(wrapper);

  lucide.createIcons();

  scrollChat();

  return wrapper;
}

/* =========================================================
   CONVERSATION TITLE
   ========================================================= */

function updateConversationTitle(firstMessage) {
  if (!firstMessage) {
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
      class="min-h-full flex items-center justify-center py-10"
    >

      <div class="max-w-2xl text-center">

        <div
          class="mx-auto w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-400/15 flex items-center justify-center mb-5 shadow-glow"
        >

          <i
            data-lucide="sparkles"
            class="w-7 h-7 text-indigo-300"
          ></i>

        </div>


        <p
          class="text-[10px] uppercase tracking-[.2em] font-bold text-indigo-400 mb-2"
        >
          Seu assistente pedagógico
        </p>


        <h3
          class="text-2xl sm:text-3xl font-black tracking-tight text-white"
        >
          O que você quer planejar hoje?
        </h3>


        <p
          class="text-xs sm:text-sm text-slate-500 mt-3 max-w-lg mx-auto leading-relaxed"
        >
          Peça um plano de aula, uma atividade,
          uma sequência didática ou adapte
          uma ideia que você já tenha.
        </p>


        <div
          class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 mt-7"
        >

          <button
            class="suggestion rounded-xl border border-slate-800 bg-slate-900/50 p-3 text-left hover:border-indigo-400/30 hover:bg-indigo-500/5 transition"
            data-suggestion="Me gere um plano de aula de Matemática sobre equações do 2º grau para o 1º ano do Ensino Médio."
          >

            <i
              data-lucide="calculator"
              class="w-4 h-4 text-indigo-400 mb-2"
            ></i>

            <p
              class="text-[11px] font-semibold text-slate-300"
            >
              Plano de aula
            </p>

            <p
              class="text-[9px] text-slate-600 mt-1"
            >
              Estrutura completa
            </p>

          </button>


          <button
            class="suggestion rounded-xl border border-slate-800 bg-slate-900/50 p-3 text-left hover:border-indigo-400/30 hover:bg-indigo-500/5 transition"
            data-suggestion="Crie uma atividade prática de Ciências sobre fotossíntese para uma turma do Ensino Fundamental II."
          >

            <i
              data-lucide="flask-conical"
              class="w-4 h-4 text-indigo-400 mb-2"
            ></i>

            <p
              class="text-[11px] font-semibold text-slate-300"
            >
              Atividade
            </p>

            <p
              class="text-[9px] text-slate-600 mt-1"
            >
              Prática e dinâmica
            </p>

          </button>


          <button
            class="suggestion rounded-xl border border-slate-800 bg-slate-900/50 p-3 text-left hover:border-indigo-400/30 hover:bg-indigo-500/5 transition"
            data-suggestion="Monte uma sequência didática de História sobre a Revolução Industrial para três aulas de 50 minutos."
          >

            <i
              data-lucide="landmark"
              class="w-4 h-4 text-indigo-400 mb-2"
            ></i>

            <p
              class="text-[11px] font-semibold text-slate-300"
            >
              Sequência didática
            </p>

            <p
              class="text-[9px] text-slate-600 mt-1"
            >
              Várias aulas
            </p>

          </button>

        </div>

      </div>

    </div>
  `;
}

// FUNCTION FORMAT CHARACTERS

function renderMarkdown(content) {
  if (!content) {
    return "";
  }

  // Remove escapes desnecessários do Markdown
  const normalized = content
    .replace(/\\([*_#>\-])/g, "$1")
    .replace(/\\\[/g, "[")
    .replace(/\\\]/g, "]");

  // Converte Markdown para HTML
  const html = marked.parse(normalized);

  // Cria um container temporário
  const container = document.createElement("div");
  container.innerHTML = DOMPurify.sanitize(html);

  // Renderiza fórmulas matemáticas com KaTeX
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

  return container.innerHTML;
}

/* =========================================================
   RESET CHAT
   ========================================================= */

function resetChat() {
  currentConversationId = null;

  messages = [];

  conversationTitle.textContent = "Nova conversa";

  setStatus("Pronto");

  chatArea.innerHTML = getWelcomeHTML();

  document.querySelectorAll(".history-item").forEach((item) => {
    item.classList.remove("active");
  });

  input.value = "";

  charCount.textContent = "0";

  sendButton.disabled = true;

  lucide.createIcons();

  attachSuggestionEvents();

  input.focus();
}

/* =========================================================
   SUGGESTIONS
   ========================================================= */

function attachSuggestionEvents() {
  document.querySelectorAll(".suggestion").forEach((button) => {
    button.addEventListener("click", () => {
      input.value = button.dataset.suggestion || "";

      input.dispatchEvent(new Event("input"));

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

  input.value = "";

  charCount.textContent = "0";

  setStatus("Gerando…");

  /* LOADING */

  const loading = addLoading();

  try {
    console.log("Conversation ID enviado:", currentConversationId);
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
      throw new Error("Backend indisponível.");
    }

    const data = await response.json();
    console.log("Resposta da API:", data);
    console.log("Conversation ID recebido:", data.conversationId);
    loading.remove();
    const result = data.response || "Não foi possível gerar uma resposta.";;

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
    loading.remove();

    const fallback = `
Não foi possível conectar ao backend local.

Verifique se o Flask está rodando em:

http://127.0.0.1:5000

Detalhe: ${error.message}
    `.trim();

    addMessage("assistant", fallback);

    setStatus("Backend offline");
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

document.getElementById("btn-sidebar-new").addEventListener("click", () => {
  resetChat();

  closeHistory();
});

/* =========================================================
   COPY
   ========================================================= */

document.getElementById("btn-copy").addEventListener("click", async () => {
  const text = messages
    .map(
      (message) =>
        `${
          message.role === "user" ? "Você" : "ProfAssistenc IA"
        }:\n${message.content}`,
    )
    .join("\n\n");

  if (!text) {
    setStatus("Nada para copiar");

    setTimeout(() => setStatus("Pronto"), 1800);

    return;
  }

  try {
    await navigator.clipboard.writeText(text);

    setStatus("Conversa copiada");

    setTimeout(() => setStatus("Pronto"), 1800);
  } catch {
    setStatus("Não foi possível copiar");
  }
});

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
      return;
    }

    const data = await response.json();

    renderHistory(data.conversations || []);
  } catch {
    /*
      Backend offline.
      O chat continua funcionando.
    */
  }
}

/* =========================================================
   RENDER HISTORY
   ========================================================= */

function renderHistory(conversations) {
  if (!conversations.length) {
    historyList.innerHTML = `
      <div
        class="empty-history rounded-xl p-4 text-center mt-1"
      >

        <i
          data-lucide="messages-square"
          class="w-6 h-6 text-slate-600 mx-auto mb-2"
        ></i>

        <p
          class="text-[11px] text-slate-500"
        >
          Nenhuma conversa ainda.
        </p>

        <p
          class="text-[10px] text-slate-600 mt-1"
        >
          A primeira aparecerá aqui.
        </p>

      </div>
    `;

    lucide.createIcons();

    return;
  }

  historyList.innerHTML = conversations
    .map((conversation) => {
      const id = String(conversation.id);

      return `
            <div
              class="history-item rounded-xl p-3 ${
                id === String(currentConversationId) ? "active" : ""
              }"
              data-id="${escapeHtml(id)}"
            >

              <button
                type="button"
                class="history-open w-full text-left pr-14"
              >

                <div
                  class="flex items-start gap-2.5"
                >

                  <i
                    data-lucide="message-square"
                    class="w-4 h-4 text-slate-500 mt-0.5 shrink-0"
                  ></i>


                  <div
                    class="min-w-0"
                  >

                    <p
                      class="text-[11px] font-semibold text-slate-300 truncate"
                    >
                      ${escapeHtml(conversation.title || "Nova conversa")}
                    </p>


                    <p
                      class="text-[9px] text-slate-600 mt-1"
                    >
                      ${escapeHtml(
                        formatConversationDate(conversation.updated_at),
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
                  class="history-action rename"
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
                  class="history-action delete"
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

  lucide.createIcons();

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

    setTimeout(() => setStatus("Pronto"), 1800);
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

    setTimeout(() => setStatus("Pronto"), 1800);
  } catch (error) {
    console.error(error);

    setStatus("Erro ao excluir");
  }
}

/* =========================================================
   RENAME EVENTS
   ========================================================= */

document
  .getElementById("rename-confirm")
  .addEventListener("click", renameConversation);

document
  .getElementById("rename-cancel")
  .addEventListener("click", closeRenameModal);

document
  .getElementById("rename-close")
  .addEventListener("click", closeRenameModal);

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
  historyPanel.classList.remove("-translate-x-full");
}

function closeHistory() {
  if (window.innerWidth < 1024) {
    historyPanel.classList.add("-translate-x-full");
  }
}

document
  .getElementById("btn-history-mobile")
  .addEventListener("click", openHistory);

document
  .getElementById("btn-close-history")
  .addEventListener("click", closeHistory);

/* =========================================================
   ESCAPE
   ========================================================= */

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") {
    return;
  }

  if (!renameModal.classList.contains("hidden")) {
    closeRenameModal();
  }
});

/* =========================================================
   INITIALIZATION
   ========================================================= */

lucide.createIcons();

attachSuggestionEvents();

loadHistory();
