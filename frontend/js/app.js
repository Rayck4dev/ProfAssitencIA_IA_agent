/* ProfAssistenc — frontend
   Sem frameworks e sem CDN: Markdown (marked), sanitização (DOMPurify) e
   fórmulas (KaTeX) vêm de ./vendor. Fala com a API do mesmo endereço, ou de
   window.PROFASSISTENC_API_URL quando o front roda separado (Live Server). */
(() => {
  "use strict";

  const API_BASE = window.PROFASSISTENC_API_URL || "";
  // Linha que o backend acrescenta ao fim das respostas (documentos consultados).
  const SOURCES_MARKER = "\n\n---\n**Documentos consultados:**";
  // Aviso que o backend acrescenta quando a IA para por limite de tamanho (vira botão "Continuar").
  const TRUNCATED_RE = /\s*\*\(Resposta cortada pelo limite de tamanho[^)]*\)\*\s*$/;
  const CONTINUE_TEXT = "Continue exatamente de onde parou, sem repetir o que já escreveu.";
  const MAX_RECORD_SECONDS = 300;
  const MIN_RECORD_MS = 700;
  const KEYS = {
    installation: "profassistenc_installation_id", // mesma chave da versão anterior
    theme: "profassistenc_theme",
    voice: "profassistenc_voice_mode",
    width: "profassistenc_width",
    sidebar: "profassistenc_sidebar",
  };

  // Exemplos de um clique: mostram que dá para escrever do seu jeito.
  const EXAMPLES = [
    "Plano de aula de frações para o 5º ano",
    "Atividade sobre a Revolução Industrial para o 9º ano",
    "Aula de estatística para o 1º ano do ensino médio",
    "Como trabalhar leitura e escrita no 2º ano?",
  ];

  const TEMPLATES = [
    {
      title: "Plano de aula",
      hint: "Habilidades, objetivos, passo a passo e avaliação.",
      text: "Crie um plano de aula de [componente] para o [ano] sobre [tema], com duração de [50 minutos].",
    },
    {
      title: "Sequência didática",
      hint: "Várias aulas encadeadas, com progressão.",
      text: "Monte uma sequência didática de [4] aulas de [componente] para o [ano] sobre [tema].",
    },
    {
      title: "Atividade avaliativa",
      hint: "Questões e critérios de correção.",
      text: "Elabore uma atividade avaliativa de [componente] para o [ano] sobre [tema], com critérios de correção.",
    },
    {
      title: "Aula de revisão",
      hint: "Retomada do conteúdo com atividades em grupo.",
      text: "Planeje uma aula de revisão de [componente] para o [ano] sobre [tema], com atividades em grupo.",
    },
  ];

  // ----------------------------------------------------------------- utilidades
  const $ = (selector) => document.querySelector(selector);
  const els = {
    app: $("#app"), sidebar: $("#sidebar"), scrim: $("#scrim"),
    history: $("#history"), newChat: $("#newChat"),
    status: $("#status"), statusText: $("#statusText"), kbNote: $("#kbNote"),
    themeToggle: $("#themeToggle"), themeLabel: $("#themeLabel"),
    docTitle: $("#docTitle"), copyChat: $("#copyChat"), renameChat: $("#renameChat"),
    scroll: $("#scroll"), thread: $("#thread"),
    composer: $("#composer"), composerBox: $("#composerBox"), input: $("#input"),
    micBtn: $("#micBtn"), micLabel: $("#micLabel"), recInfo: $("#recInfo"),
    recLevel: $("#recLevel"), recTime: $("#recTime"), voiceMode: $("#voiceMode"),
    sendBtn: $("#sendBtn"), sendLabel: $("#sendLabel"),
    renameDialog: $("#renameDialog"), renameInput: $("#renameInput"),
    deleteDialog: $("#deleteDialog"), deleteText: $("#deleteText"),
    toast: $("#toast"), openMenu: $("#openMenu"), closeMenu: $("#closeMenu"),
    setupDialog: $("#setupDialog"), setupKey: $("#setupKey"), setupShow: $("#setupShow"),
    setupMsg: $("#setupMsg"), setupSave: $("#setupSave"), setupIntro: $("#setupIntro"), openSetup: $("#openSetup"),
    toggleSidebar: $("#toggleSidebar"), toggleWidth: $("#toggleWidth"), widthLabel: $("#widthLabel"),
  };

  const storage = {
    get(key) { try { return localStorage.getItem(key); } catch { return null; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch { /* modo privado */ } },
  };

  function getInstallationId() {
    let id = storage.get(KEYS.installation);
    if (!id) {
      id = window.crypto && crypto.randomUUID
        ? crypto.randomUUID()
        : "local-" + Date.now() + "-" + Math.random().toString(36).slice(2);
      storage.set(KEYS.installation, id);
    }
    return id;
  }

  const state = {
    installationId: getInstallationId(),
    conversations: [],
    currentId: null,
    messages: [],
    busy: false,
    abort: null,
    error: null,
    lastText: "",
    warnedText: "",
    setupOffered: false,
    health: null,
  };

  class ApiError extends Error {
    constructor(message, status) { super(message); this.status = status; }
  }

  async function api(path, { method = "GET", body, form, signal, headers } = {}) {
    let response;
    try {
      response = await fetch(API_BASE + path, {
        method,
        signal,
        headers: body ? { "Content-Type": "application/json", ...headers } : headers,
        body: form || (body ? JSON.stringify(body) : undefined),
      });
    } catch (err) {
      if (err.name === "AbortError") throw err;
      throw new ApiError("Não consegui falar com o servidor. Ele está rodando?", 0);
    }
    if (!response.ok) {
      const text = (await response.text().catch(() => "")).trim();
      throw new ApiError(text || `Erro ${response.status}`, response.status);
    }
    return response.status === 204 ? null : response.json();
  }

  const qs = () => `installation_id=${encodeURIComponent(state.installationId)}`;

  let toastTimer = 0;
  function toast(message, ms = 4500) {
    els.toast.textContent = message;
    els.toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { els.toast.hidden = true; }, ms);
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function icon(name) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "icon");
    svg.setAttribute("aria-hidden", "true");
    const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
    use.setAttribute("href", `#i-${name}`);
    svg.appendChild(use);
    return svg;
  }

  function linkButton(iconName, label, onClick) {
    const button = el("button", "link-btn");
    button.type = "button";
    button.append(icon(iconName), el("span", null, label));
    button.addEventListener("click", () => onClick(button));
    return button;
  }

  // ------------------------------------------------------------------ Markdown
  const MATH_DELIMITERS = [
    { left: "$$", right: "$$", display: true },
    { left: "\\[", right: "\\]", display: true },
    { left: "\\(", right: "\\)", display: false },
    // "$...$" fica de fora de propósito: "R$ 10 e R$ 20" viraria fórmula.
  ];

  if (window.DOMPurify) {
    DOMPurify.addHook("afterSanitizeAttributes", (node) => {
      if (node.tagName === "A" && node.hasAttribute("href")) {
        node.setAttribute("target", "_blank");
        node.setAttribute("rel", "noopener noreferrer");
      }
    });
  }

  const escapeHtml = (s) =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  /** O Markdown "come" as barras de \( \) e mexe em \frac etc. Por isso a matemática
   *  é guardada antes do marked rodar e devolvida (como texto) para o KaTeX. */
  function protectMath(source) {
    const saved = [];
    const keep = (match) => `@@MATH${saved.push(match) - 1}@@`;
    const text = source
      .replace(/\$\$[\s\S]+?\$\$/g, keep)
      .replace(/\\\[[\s\S]+?\\\]/g, keep)
      .replace(/\\\([\s\S]+?\\\)/g, keep);
    return { text, restore: (html) => html.replace(/@@MATH(\d+)@@/g, (_, i) => escapeHtml(saved[i])) };
  }

  function renderMarkdown(source, target) {
    if (!window.marked || !window.DOMPurify) {
      target.textContent = source;
      return;
    }
    const math = protectMath(source);
    const html = math.restore(marked.parse(math.text, { gfm: true, async: false }));
    target.innerHTML = DOMPurify.sanitize(html, { USE_PROFILES: { html: true } });
    target.querySelectorAll("table").forEach((table) => {
      const wrap = el("div", "table-wrap");
      table.replaceWith(wrap);
      wrap.appendChild(table);
    });
    if (window.renderMathInElement) {
      renderMathInElement(target, { delimiters: MATH_DELIMITERS, throwOnError: false });
    }
  }

  /** Separa o texto da resposta da linha "Documentos consultados" + alertas. */
  function splitAnswer(content) {
    const at = content.indexOf(SOURCES_MARKER);
    if (at === -1) return { main: content, sources: "", notes: "" };
    const tail = content.slice(at + SOURCES_MARKER.length);
    const [first, ...rest] = tail.split("\n");
    return { main: content.slice(0, at), sources: first.trim(), notes: rest.join("\n").trim() };
  }

  // ------------------------------------------------------------------ mensagens
  function renderThread() {
    els.thread.replaceChildren();
    if (!state.messages.length && !state.busy && !state.error) {
      els.thread.appendChild(heroNode());
    }
    const last = state.messages.length - 1;
    state.messages.forEach((message, i) => els.thread.appendChild(messageNode(message, i === last)));
    if (state.busy) els.thread.appendChild(pendingNode());
    if (state.error) els.thread.appendChild(errorNode(state.error));
    refreshHeader();
  }

  function logoMark(className) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", className);
    svg.setAttribute("aria-hidden", "true");
    const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
    use.setAttribute("href", "#logo-mark");
    svg.appendChild(use);
    return svg;
  }

  function heroNode() {
    const hero = el("section", "hero");
    const tip = el("p", "tip");
    tip.append(
      el("strong", null, "Do seu jeito: "),
      document.createTextNode(
        "pode abreviar, errar uma letra ou mandar o pedido incompleto. O assistente entende, " +
        "assume o que faltar e avisa o que assumiu."),
    );
    hero.append(
      logoMark("hero-mark"),
      el("h2", null, "O que vamos planejar hoje?"),
      el("p", "lede",
        "Diga o componente, o ano e o tema. Os planos seguem a BNCC e o Referencial " +
        "Curricular de Rondônia, com as habilidades e as páginas citadas."),
      tip,
      el("p", "hero-label", "Experimente (um clique envia)"),
    );

    const chips = el("div", "examples");
    EXAMPLES.forEach((example) => {
      const chip = el("button", "chip", example);
      chip.type = "button";
      chip.addEventListener("click", () => {
        els.input.value = example;
        autosize();
        send(example);
      });
      chips.appendChild(chip);
    });
    hero.appendChild(chips);

    hero.appendChild(el("p", "hero-label", "Ou comece por um modelo"));
    const grid = el("div", "templates");
    TEMPLATES.forEach((template) => {
      const button = el("button", "template");
      button.type = "button";
      button.append(el("strong", null, template.title), el("span", null, template.hint));
      button.addEventListener("click", () => applyTemplate(template.text));
      grid.appendChild(button);
    });
    hero.appendChild(grid);

    const steps = el("ol", "steps");
    [
      ["Você pede", "Do seu jeito, com ou sem ano e componente."],
      ["Eu consulto", "A BNCC e o RCSEERO, e corrijo erros de digitação."],
      ["Você recebe", "Plano com habilidades, códigos conferidos e páginas."],
    ].forEach(([title, text]) => {
      const item = el("li");
      item.append(el("strong", null, title), document.createTextNode(text));
      steps.appendChild(item);
    });
    hero.appendChild(steps);

    const sources = el("p", "hero-sources");
    sources.id = "heroSources";
    sources.textContent = heroSourcesText();
    hero.appendChild(sources);
    return hero;
  }

  function heroSourcesText() {
    const kb = state.health && state.health.knowledgeBase;
    if (!state.health) return "";
    if (kb && kb.available) {
      return `Documentos oficiais consultados a cada pedido: ${kb.names.join(" · ")} ` +
             `(${kb.chunks.toLocaleString("pt-BR")} trechos indexados).`;
    }
    return "A base de documentos não está carregada: as respostas não serão conferidas com a BNCC.";
  }

  function continueBox() {
    const box = el("div", "continue-box");
    box.appendChild(el("p", null, "A resposta foi cortada pelo limite de tamanho. A IA pode seguir de onde parou."));
    const button = el("button", "btn btn-primary");
    button.type = "button";
    button.append(icon("chevrons-right"), document.createTextNode("Continuar a resposta"));
    button.addEventListener("click", () => send(CONTINUE_TEXT));
    box.appendChild(button);
    return box;
  }

  function messageNode(message, isLast = false) {
    const wrapper = el("article", `msg msg-${message.role === "user" ? "user" : "assistant"}`);
    if (message.role === "user") {
      wrapper.append(el("p", "msg-label", "Você"), el("div", "bubble", message.content));
      return wrapper;
    }

    const parts = splitAnswer(message.content);
    const cut = TRUNCATED_RE.test(parts.main);
    const main = parts.main.replace(TRUNCATED_RE, "").trim();
    const { sources, notes } = parts;

    const sheet = el("div", "sheet");
    const head = el("div", "print-head");
    const doc = el("div", "doc");
    renderMarkdown(main, doc);
    sheet.append(head, doc);

    if (sources || notes) {
      const box = el("div", "sources");
      if (sources) {
        const line = el("p");
        line.append(el("strong", null, "Documentos consultados: "), document.createTextNode(sources));
        box.appendChild(line);
      }
      if (notes) {
        const noteBox = el("div");
        renderMarkdown(notes, noteBox);
        box.appendChild(noteBox);
      }
      sheet.appendChild(box);
    }

    const actions = el("div", "msg-actions");
    actions.append(
      linkButton("copy", "Copiar", () => copyText(main, "Resposta copiada.")),
      linkButton("printer", "Imprimir", () => printMessage(wrapper)),
    );
    if (tts.supported) {
      const listen = linkButton("volume-2", "Ouvir", (button) => toggleSpeak(button, message.content));
      listen.setAttribute("aria-pressed", "false");
      actions.appendChild(listen);
    }

    const label = el("p", "msg-label");
    label.append(logoMark("logo-mark"), document.createTextNode("ProfAssistenc"));
    wrapper.append(label, sheet);
    if (cut && isLast && !state.busy) wrapper.appendChild(continueBox());
    wrapper.appendChild(actions);
    return wrapper;
  }

  function pendingNode() {
    const kb = state.health && state.health.knowledgeBase;
    const text = kb && kb.available
      ? `Consultando ${kb.names.join(" e ")} e escrevendo…`
      : "Escrevendo a resposta…";
    const node = el("div", "pending");
    const dots = el("span", "dots");
    dots.append(el("i"), el("i"), el("i"));
    node.append(dots, el("span", null, text));
    return node;
  }

  function errorNode(error) {
    const box = el("div", "error-box");
    box.setAttribute("role", "alert");
    box.appendChild(el("p", null, error.message));
    if (/chave/i.test(error.message)) {
      const configure = el("button", "btn btn-primary");
      configure.type = "button";
      configure.append(icon("key-round"), document.createTextNode("Configurar chave"));
      configure.addEventListener("click", () => openSetup());
      box.appendChild(configure);
    }
    const retry = el("button", "btn");
    retry.type = "button";
    retry.append(icon("rotate-ccw"), document.createTextNode("Tentar de novo"));
    retry.addEventListener("click", retryLast);
    box.appendChild(retry);
    return box;
  }

  function scrollToBottom() {
    els.scroll.scrollTo({ top: els.scroll.scrollHeight, behavior: "auto" });
  }

  function scrollToLastAnswer() {
    const answers = els.thread.querySelectorAll(".msg-assistant");
    const last = answers[answers.length - 1];
    if (last) last.scrollIntoView({ block: "start", behavior: "smooth" });
  }

  // ---------------------------------------------------------------- cabeçalho
  function currentConversation() {
    return state.conversations.find((c) => String(c.id) === String(state.currentId)) || null;
  }

  function currentTitle() {
    const conversation = currentConversation();
    return (conversation && conversation.title) || "Nova conversa";
  }

  function refreshHeader() {
    const title = state.currentId ? currentTitle() : "Nova conversa";
    els.docTitle.textContent = title;
    document.title = state.currentId ? `${title} — ProfAssistenc` : "ProfAssistenc — planejamento de aulas";
    els.copyChat.hidden = !state.messages.length;
    els.renameChat.hidden = !state.currentId;
  }

  // ------------------------------------------------------------------ histórico
  function dayGroup(date) {
    const startOfToday = new Date();
    startOfToday.setHours(0, 0, 0, 0);
    const days = Math.floor((startOfToday - new Date(date).setHours(0, 0, 0, 0)) / 86400000);
    if (days <= 0) return "Hoje";
    if (days === 1) return "Ontem";
    if (days < 7) return "Últimos 7 dias";
    return "Anteriores";
  }

  function shortDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    const sameDay = date.toDateString() === new Date().toDateString();
    return sameDay
      ? date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
      : date.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
  }

  function renderHistory() {
    els.history.replaceChildren();
    if (!state.conversations.length) {
      els.history.appendChild(el("p", "hist-empty", "Suas conversas aparecem aqui."));
      return;
    }
    let lastGroup = "";
    state.conversations.forEach((conversation) => {
      const group = dayGroup(conversation.updatedAt);
      if (group !== lastGroup) {
        els.history.appendChild(el("div", "hist-group", group));
        lastGroup = group;
      }
      const item = el("div", "hist-item");
      if (String(conversation.id) === String(state.currentId)) item.classList.add("active");

      const open = el("button", "hist-open");
      open.type = "button";
      open.title = conversation.title || "Nova conversa";
      open.append(
        el("span", "hist-title", conversation.title || "Nova conversa"),
        el("span", "hist-date", shortDate(conversation.updatedAt)),
      );
      open.addEventListener("click", () => openConversation(conversation.id));

      const actions = el("div", "hist-actions");
      const rename = el("button", "icon-btn");
      rename.type = "button";
      rename.setAttribute("aria-label", `Renomear: ${conversation.title || "Nova conversa"}`);
      rename.appendChild(icon("pencil"));
      rename.addEventListener("click", () => askRename(conversation));
      const remove = el("button", "icon-btn");
      remove.type = "button";
      remove.setAttribute("aria-label", `Excluir: ${conversation.title || "Nova conversa"}`);
      remove.appendChild(icon("trash-2"));
      remove.addEventListener("click", () => askDelete(conversation));
      actions.append(rename, remove);

      item.append(open, actions);
      els.history.appendChild(item);
    });
  }

  async function loadHistory() {
    try {
      const data = await api(`/api/conversations?${qs()}`);
      state.conversations = data.conversations || [];
    } catch (err) {
      if (!state.conversations.length) toast(err.message);
    }
    renderHistory();
    refreshHeader();
  }

  async function openConversation(id) {
    if (state.busy) return;
    stopSpeaking();
    try {
      const data = await api(`/api/conversations/${encodeURIComponent(id)}?${qs()}`);
      state.currentId = String(data.id ?? id);
      state.messages = (data.messages || []).map((m) => ({ role: m.role, content: m.content }));
      state.error = null;
      renderThread();
      renderHistory();
      scrollToBottom();
      closeMenu();
    } catch (err) {
      toast(err.message);
    }
  }

  function newConversation() {
    if (state.abort) state.abort.abort();
    stopSpeaking();
    state.currentId = null;
    state.messages = [];
    state.error = null;
    state.busy = false;
    setBusy(false);
    renderThread();
    renderHistory();
    els.input.focus();
    closeMenu();
  }

  // ---------------------------------------------------------- renomear / excluir
  let dialogTarget = null;

  function askRename(conversation) {
    dialogTarget = conversation;
    els.renameInput.value = conversation.title || "";
    els.renameDialog.returnValue = "";
    els.renameDialog.showModal();
    els.renameInput.select();
  }

  els.renameInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      els.renameDialog.close("ok");
    }
  });

  els.renameDialog.addEventListener("close", async () => {
    const conversation = dialogTarget;
    dialogTarget = null;
    const title = els.renameInput.value.trim().slice(0, 80);
    if (els.renameDialog.returnValue !== "ok" || !conversation || !title) return;
    try {
      await api(`/api/conversations/${encodeURIComponent(conversation.id)}`, {
        method: "PATCH",
        body: { installation_id: state.installationId, title },
      });
      await loadHistory();
    } catch (err) {
      toast(err.message);
    }
  });

  function askDelete(conversation) {
    dialogTarget = conversation;
    els.deleteText.textContent =
      `“${conversation.title || "Nova conversa"}” e todas as suas mensagens serão apagadas. Esta ação não pode ser desfeita.`;
    els.deleteDialog.returnValue = "";
    els.deleteDialog.showModal();
  }

  els.deleteDialog.addEventListener("close", async () => {
    const conversation = dialogTarget;
    dialogTarget = null;
    if (els.deleteDialog.returnValue !== "ok" || !conversation) return;
    try {
      await api(`/api/conversations/${encodeURIComponent(conversation.id)}?${qs()}`, { method: "DELETE" });
      const wasCurrent = String(conversation.id) === String(state.currentId);
      await loadHistory();
      if (wasCurrent) newConversation();
      toast("Conversa excluída.", 2500);
    } catch (err) {
      toast(err.message);
    }
  });

  // --------------------------------------------------------------------- envio
  function setBusy(busy) {
    state.busy = busy;
    els.sendLabel.textContent = busy ? "Cancelar" : "Enviar";
    els.sendBtn.setAttribute("aria-label", busy ? "Cancelar envio" : "Enviar mensagem");
    els.sendBtn.replaceChild(icon(busy ? "x" : "arrow-up"), els.sendBtn.querySelector("svg"));
    els.input.disabled = false;
  }

  function placeholderRange(from = 0) {
    const regex = /\[[^\]\n]+\]/g;
    const text = els.input.value;
    regex.lastIndex = from;
    let match = regex.exec(text);
    if (!match && from > 0) {
      regex.lastIndex = 0; // dá a volta até o primeiro campo
      match = regex.exec(text);
    }
    return match ? [match.index, match.index + match[0].length] : null;
  }

  function selectPlaceholder(from = 0) {
    const range = placeholderRange(from);
    if (!range) return false;
    els.input.focus();
    els.input.setSelectionRange(range[0], range[1]);
    return true;
  }

  function applyTemplate(text) {
    els.input.value = text;
    autosize();
    selectPlaceholder(0);
  }

  async function send(rawText) {
    const text = rawText.trim();
    if (!text || state.busy) return;
    if (/\[[^\]\n]+\]/.test(text) && state.warnedText !== text) {
      // Avisa uma vez; se o professor mandar de novo, envia assim mesmo.
      state.warnedText = text;
      toast("Ainda há campos [entre colchetes]. Preencha-os, ou envie de novo para mandar assim mesmo.");
      selectPlaceholder(0);
      return;
    }
    state.warnedText = "";
    stopSpeaking();
    state.lastText = text;
    state.error = null;
    state.messages.push({ role: "user", content: text });
    els.input.value = "";
    autosize();
    state.abort = new AbortController();
    setBusy(true);
    renderThread();
    scrollToBottom();

    try {
      const data = await api("/api/LessonPlan", {
        method: "POST",
        signal: state.abort.signal,
        body: {
          installation_id: state.installationId,
          conversation_id: state.currentId,
          message: text,
        },
      });
      state.currentId = String(data.conversationId);
      state.messages.push({ role: "assistant", content: data.response });
      setBusy(false);
      await loadHistory();
      renderThread();
      scrollToLastAnswer();
      if (els.voiceMode.checked) speakText(data.response);
    } catch (err) {
      setBusy(false);
      if (err.name === "AbortError") {
        state.messages.pop();
        els.input.value = text;
        autosize();
        renderThread();
      } else {
        state.error = { message: err.message };
        renderThread();
        scrollToBottom();
      }
    } finally {
      state.abort = null;
    }
  }

  function retryLast() {
    state.messages.pop(); // a pergunta que ficou sem resposta
    state.error = null;
    send(state.lastText);
  }

  els.composer.addEventListener("submit", (event) => {
    event.preventDefault();
    if (state.busy) {
      if (state.abort) state.abort.abort();
      return;
    }
    send(els.input.value);
  });

  els.input.addEventListener("keydown", (event) => {
    if (event.isComposing) return;
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      els.composer.requestSubmit();
    } else if (event.key === "Tab" && !event.shiftKey && /\[[^\]\n]+\]/.test(els.input.value)) {
      // Tab pula para o próximo campo [entre colchetes] do modelo.
      if (selectPlaceholder(els.input.selectionEnd)) event.preventDefault();
    }
  });

  function autosize() {
    els.input.style.height = "auto";
    els.input.style.height = Math.min(els.input.scrollHeight, 220) + "px";
  }
  els.input.addEventListener("input", autosize);

  // -------------------------------------------------------- copiar / imprimir
  async function copyText(text, okMessage) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const area = el("textarea");
      area.value = text;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      area.remove();
    }
    toast(okMessage, 2200);
  }

  els.copyChat.addEventListener("click", () => {
    const text = state.messages
      .map((m) => `${m.role === "user" ? "Professor(a)" : "ProfAssistenc"}:\n${splitAnswer(m.content).main.replace(TRUNCATED_RE, "").trim()}`)
      .join("\n\n");
    copyText(text, "Conversa copiada.");
  });

  function printMessage(node) {
    const head = node.querySelector(".print-head");
    head.textContent = `ProfAssistenc · ${currentTitle()} · ${new Date().toLocaleDateString("pt-BR")}`;
    document.body.classList.add("print-one");
    node.classList.add("print-target");
    const cleanup = () => {
      document.body.classList.remove("print-one");
      node.classList.remove("print-target");
      window.removeEventListener("afterprint", cleanup);
    };
    window.addEventListener("afterprint", cleanup);
    window.print();
  }

  els.renameChat.addEventListener("click", () => {
    const conversation = currentConversation();
    if (conversation) askRename(conversation);
  });

  // ----------------------------------------------------------- leitura em voz alta
  const tts = {
    supported: "speechSynthesis" in window && "SpeechSynthesisUtterance" in window,
    voice: null,
    button: null,
  };

  function loadVoices() {
    if (!tts.supported) return;
    const voices = speechSynthesis.getVoices();
    tts.voice =
      voices.find((v) => /^pt[-_]BR/i.test(v.lang)) || voices.find((v) => /^pt/i.test(v.lang)) || null;
  }
  if (tts.supported) {
    loadVoices();
    speechSynthesis.addEventListener("voiceschanged", loadVoices);
  }

  /** Markdown -> texto corrido, sem símbolos e sem a linha de documentos consultados. */
  function plainForSpeech(markdown) {
    const body = splitAnswer(markdown).main.replace(TRUNCATED_RE, "");
    return body
      .replace(/```[\s\S]*?```/g, " ")
      .replace(/!\[[^\]]*\]\([^)]*\)/g, " ")
      .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
      .replace(/^\s{0,3}#{1,6}\s*/gm, "")
      .replace(/^\s*(?:[-*+]|\d+[.)])\s+/gm, "")
      .replace(/^\s*>\s?/gm, "")
      .replace(/[*_`|]/g, " ")
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => (/[.!?:;]$/.test(line) ? line : line + "."))
      .join(" ");
  }

  function sentenceChunks(text, max = 180) {
    const sentences = text.match(/[^.!?;:]+[.!?;:]*\s*/g) || [text];
    const chunks = [];
    let current = "";
    for (const sentence of sentences) {
      if (current && (current + sentence).length > max) {
        chunks.push(current.trim());
        current = "";
      }
      current += sentence;
    }
    if (current.trim()) chunks.push(current.trim());
    return chunks;
  }

  function markListening(button, on) {
    if (!button) return;
    button.setAttribute("aria-pressed", String(on));
    button.querySelector("span").textContent = on ? "Parar" : "Ouvir";
    button.querySelector("use").setAttribute("href", on ? "#i-volume-x" : "#i-volume-2");
  }

  function stopSpeaking() {
    if (!tts.supported) return;
    speechSynthesis.cancel();
    markListening(tts.button, false);
    tts.button = null;
  }

  function speakText(markdown, button = null) {
    if (!tts.supported) return;
    stopSpeaking();
    const chunks = sentenceChunks(plainForSpeech(markdown));
    if (!chunks.length) return;
    tts.button = button;
    markListening(button, true);
    chunks.forEach((chunk, index) => {
      const utterance = new SpeechSynthesisUtterance(chunk);
      utterance.lang = "pt-BR";
      if (tts.voice) utterance.voice = tts.voice;
      if (index === chunks.length - 1) {
        utterance.onend = utterance.onerror = () => {
          markListening(button, false);
          if (tts.button === button) tts.button = null;
        };
      }
      speechSynthesis.speak(utterance);
    });
  }

  function toggleSpeak(button, markdown) {
    if (tts.button === button) stopSpeaking();
    else speakText(markdown, button);
  }

  // ----------------------------------------------------------------------- voz
  const rec = {
    state: "idle", // idle | recording | transcribing
    recorder: null, stream: null, chunks: [], cancelled: false,
    audioContext: null, raf: 0, tick: 0, startedAt: 0,
  };

  const supportsRecording = () =>
    !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);

  function pickMimeType() {
    const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
    return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || "";
  }

  function extensionFor(type) {
    if (type.includes("ogg")) return "ogg";
    if (type.includes("mp4")) return "mp4";
    if (type.includes("wav")) return "wav";
    return "webm";
  }

  function micErrorMessage(err) {
    if (err && (err.name === "NotAllowedError" || err.name === "SecurityError")) {
      return "O navegador bloqueou o microfone. Clique no cadeado, ao lado do endereço, e permita o uso.";
    }
    if (err && err.name === "NotFoundError") return "Nenhum microfone encontrado neste computador.";
    return "Não foi possível acessar o microfone.";
  }

  function setMicUi() {
    const recording = rec.state === "recording";
    const transcribing = rec.state === "transcribing";
    els.micBtn.setAttribute("aria-pressed", String(recording));
    els.micBtn.classList.toggle("busy", transcribing);
    els.micBtn.disabled = transcribing;
    els.micLabel.textContent = recording ? "Parar" : transcribing ? "Transcrevendo…" : "Falar";
    els.micBtn.querySelector("use").setAttribute("href", recording ? "#i-square" : "#i-mic");
    els.recInfo.hidden = !recording;
    els.composerBox.classList.toggle("recording", recording);
  }

  function updateTimer() {
    const seconds = Math.floor((performance.now() - rec.startedAt) / 1000);
    els.recTime.textContent = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
    if (seconds >= MAX_RECORD_SECONDS) stopRecording(false);
  }

  function startMeter(stream) {
    try {
      const Context = window.AudioContext || window.webkitAudioContext;
      rec.audioContext = new Context();
      const source = rec.audioContext.createMediaStreamSource(stream);
      const analyser = rec.audioContext.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);
      const samples = new Uint8Array(analyser.fftSize);
      const loop = () => {
        analyser.getByteTimeDomainData(samples);
        let peak = 0;
        for (const value of samples) peak = Math.max(peak, Math.abs(value - 128));
        els.recLevel.style.setProperty("--level", Math.min(1, peak / 60).toFixed(2));
        rec.raf = requestAnimationFrame(loop);
      };
      loop();
    } catch { /* o medidor é opcional */ }
  }

  function releaseAudio() {
    cancelAnimationFrame(rec.raf);
    clearInterval(rec.tick);
    els.recLevel.style.setProperty("--level", "0");
    if (rec.audioContext) rec.audioContext.close().catch(() => {});
    rec.audioContext = null;
    if (rec.stream) rec.stream.getTracks().forEach((track) => track.stop());
    rec.stream = null;
  }

  async function startRecording() {
    if (!supportsRecording()) {
      toast(window.isSecureContext
        ? "Este navegador não permite gravar áudio."
        : "A gravação só funciona em http://localhost ou em HTTPS.");
      return;
    }
    stopSpeaking();
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
      });
    } catch (err) {
      toast(micErrorMessage(err));
      return;
    }
    const mimeType = pickMimeType();
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType, audioBitsPerSecond: 32000 } : undefined);
    rec.chunks = [];
    rec.cancelled = false;
    rec.recorder = recorder;
    rec.stream = stream;
    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size) rec.chunks.push(event.data);
    };
    recorder.onstop = onRecordingStopped;
    recorder.start(250);
    rec.startedAt = performance.now();
    rec.state = "recording";
    els.recTime.textContent = "0:00";
    setMicUi();
    startMeter(stream);
    rec.tick = setInterval(updateTimer, 250);
  }

  function stopRecording(cancel) {
    if (rec.state !== "recording" || !rec.recorder) return;
    rec.cancelled = cancel;
    clearInterval(rec.tick);
    rec.recorder.stop();
  }

  async function onRecordingStopped() {
    const duration = performance.now() - rec.startedAt;
    const type = (rec.recorder && rec.recorder.mimeType) || (rec.chunks[0] && rec.chunks[0].type) || "audio/webm";
    releaseAudio();

    if (rec.cancelled) {
      rec.state = "idle";
      setMicUi();
      return;
    }
    if (duration < MIN_RECORD_MS || !rec.chunks.length) {
      rec.state = "idle";
      setMicUi();
      toast("Gravação muito curta. Toque em Falar e fale por mais um instante.");
      return;
    }

    rec.state = "transcribing";
    setMicUi();
    try {
      const form = new FormData();
      form.append("audio", new Blob(rec.chunks, { type }), `gravacao.${extensionFor(type)}`);
      const data = await api("/api/transcribe", { method: "POST", form });
      const text = (data.text || "").trim();
      if (!text) {
        toast("Não consegui entender o áudio. Tente de novo, mais perto do microfone.");
      } else {
        els.input.value = els.input.value.trim() ? `${els.input.value.trim()} ${text}` : text;
        autosize();
        els.input.focus();
        if (els.voiceMode.checked) send(els.input.value);
      }
    } catch (err) {
      toast(err.message);
    } finally {
      rec.state = "idle";
      setMicUi();
    }
  }

  els.micBtn.addEventListener("click", () => {
    if (rec.state === "recording") stopRecording(false);
    else if (rec.state === "idle") startRecording();
  });

  els.voiceMode.checked = storage.get(KEYS.voice) === "1";
  els.voiceMode.addEventListener("change", () => {
    storage.set(KEYS.voice, els.voiceMode.checked ? "1" : "0");
    if (!els.voiceMode.checked) stopSpeaking();
  });

  if (!supportsRecording()) {
    els.micBtn.title = window.isSecureContext
      ? "Este navegador não permite gravar áudio."
      : "A gravação só funciona em http://localhost ou em HTTPS.";
  }

  // ------------------------------------------------------- largura e menu lateral
  function applyLayout() {
    const wide = storage.get(KEYS.width) === "wide";
    els.app.dataset.width = wide ? "wide" : "normal";
    els.toggleWidth.setAttribute("aria-pressed", String(wide));
    els.widthLabel.textContent = wide ? "Reduzir" : "Ampliar";
    els.toggleWidth.querySelector("use").setAttribute("href", wide ? "#i-minimize-2" : "#i-maximize-2");

    const collapsed = storage.get(KEYS.sidebar) === "1";
    els.app.classList.toggle("sidebar-collapsed", collapsed);
    els.toggleSidebar.setAttribute("aria-pressed", String(collapsed));
    const sidebarLabel = collapsed ? "Mostrar o menu lateral" : "Recolher o menu lateral";
    els.toggleSidebar.setAttribute("aria-label", sidebarLabel);
    els.toggleSidebar.title = sidebarLabel;
    els.toggleSidebar.querySelector("use").setAttribute("href", collapsed ? "#i-panel-left-open" : "#i-panel-left-close");
  }
  els.toggleWidth.addEventListener("click", () => {
    storage.set(KEYS.width, storage.get(KEYS.width) === "wide" ? "normal" : "wide");
    applyLayout();
  });
  els.toggleSidebar.addEventListener("click", () => {
    storage.set(KEYS.sidebar, storage.get(KEYS.sidebar) === "1" ? "0" : "1");
    applyLayout();
  });
  applyLayout();

  // ------------------------------------------------------------ tema, menu, status
  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    const dark = theme === "dark";
    els.themeLabel.textContent = dark ? "Tema claro" : "Tema escuro";
    els.themeToggle.querySelector("use").setAttribute("href", dark ? "#i-sun" : "#i-moon");
  }
  els.themeToggle.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    storage.set(KEYS.theme, next);
    applyTheme(next);
  });
  applyTheme(document.documentElement.dataset.theme || "light");

  function openMenu() { els.app.classList.add("menu-open"); els.scrim.hidden = false; }
  function closeMenu() { els.app.classList.remove("menu-open"); els.scrim.hidden = true; }
  els.openMenu.addEventListener("click", openMenu);
  els.closeMenu.addEventListener("click", closeMenu);
  els.scrim.addEventListener("click", closeMenu);
  els.newChat.addEventListener("click", newConversation);

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (rec.state === "recording") {
      stopRecording(true);
      toast("Gravação cancelada.", 1800);
    } else {
      closeMenu();
    }
  });

  function setStatus(stateName, text) {
    els.status.dataset.state = stateName;
    els.statusText.textContent = text;
  }

  async function checkHealth() {
    try {
      const health = await api("/api/health");
      state.health = health;
      if (!health.aiConfigured) {
        setStatus("warn", "IA sem chave. Clique para configurar");
        if (!state.setupOffered) {  // oferece uma vez por abertura, sem insistir
          state.setupOffered = true;
          openSetup("Falta só um passo: informe a sua chave gratuita da Groq para a IA responder.");
        }
      }
      else setStatus("ok", `IA conectada · ${health.model}`);
      const kb = health.knowledgeBase;
      els.kbNote.hidden = false;
      els.kbNote.textContent = kb.available
        ? `Documentos oficiais ativos: ${kb.names.join(" · ")}`
        : "Sem base de documentos: respostas não são conferidas com a BNCC.";
    } catch {
      state.health = null;
      setStatus("error", "Servidor offline");
      els.kbNote.hidden = true;
    }
    const hero = $("#heroSources");
    if (hero) hero.textContent = heroSourcesText();
  }
  window.addEventListener("focus", checkHealth);

  // ----------------------------------------------------------- chave da IA (configuração)
  function setSetupMessage(text, kind = "") {
    els.setupMsg.textContent = text;
    els.setupMsg.dataset.kind = kind;
  }

  function openSetup(intro) {
    const configured = state.health && state.health.aiConfigured;
    els.setupIntro.textContent = intro ||
      (configured
        ? "A IA já está configurada. Se quiser trocar a chave, siga os passos:"
        : "Para usar a IA, o programa precisa da sua chave gratuita da Groq. Leva uns 2 minutos:");
    els.setupKey.value = "";
    els.setupKey.type = "password";
    els.setupShow.textContent = "Mostrar";
    els.setupShow.setAttribute("aria-pressed", "false");
    setSetupMessage("");
    if (!els.setupDialog.open) els.setupDialog.showModal();
    els.setupKey.focus();
  }

  async function saveKey() {
    const key = els.setupKey.value.trim();
    if (!key) {
      setSetupMessage("Cole a sua chave no campo acima.", "error");
      els.setupKey.focus();
      return;
    }
    els.setupSave.disabled = true;
    els.setupSave.textContent = "Testando…";
    setSetupMessage("Testando a chave na Groq…");
    try {
      await api("/api/setup/key", {
        method: "POST",
        headers: { "X-ProfAssistenc": "1" },
        body: { api_key: key },
      });
      els.setupDialog.close("ok");
      toast("Chave salva. Tudo pronto: já pode pedir o seu plano de aula!", 5000);
      await checkHealth();
      if (state.error && /chave/i.test(state.error.message)) {
        state.error = null;
        renderThread();
      }
    } catch (err) {
      setSetupMessage(err.message, "error");
    } finally {
      els.setupSave.disabled = false;
      els.setupSave.textContent = "Salvar e testar";
    }
  }

  els.setupSave.addEventListener("click", saveKey);
  els.setupKey.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      saveKey();
    }
  });
  els.setupShow.addEventListener("click", () => {
    const show = els.setupKey.type === "password";
    els.setupKey.type = show ? "text" : "password";
    els.setupShow.textContent = show ? "Ocultar" : "Mostrar";
    els.setupShow.setAttribute("aria-pressed", String(show));
  });
  els.openSetup.addEventListener("click", () => openSetup());
  els.status.addEventListener("click", () => {
    if (els.status.dataset.state === "warn") openSetup();
  });

  // ------------------------------------------------------------------ inicializar
  if (window.matchMedia("(max-width: 820px)").matches) {
    els.input.placeholder = "Ex.: aula de frações para o 5º ano"; // cabe em uma linha no celular
  }
  renderThread();
  renderHistory();
  checkHealth();
  loadHistory();
  if (window.matchMedia("(min-width: 821px)").matches) els.input.focus();
})();
