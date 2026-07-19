/* =========================================================================
   CookWithMe — script.js
   Handles: chat sending/receiving, sidebar/session management, dark mode,
   voice input, typing indicator, auto-scroll, and message action buttons
   (copy / print / PDF / share).
   ========================================================================= */

(() => {
  "use strict";

  // ----------------------------- State -----------------------------
  let currentSessionId = null;
  let isSending = false;
  let recognition = null;
  let isRecording = false;

  // ----------------------------- DOM refs -----------------------------
  const chatWindow = document.getElementById("chatWindow");
  const landing = document.getElementById("landing");
  const messageInput = document.getElementById("messageInput");
  const sendBtn = document.getElementById("sendBtn");
  const typingIndicator = document.getElementById("typingIndicator");
  const chatHistoryList = document.getElementById("chatHistoryList");
  const newChatBtn = document.getElementById("newChatBtn");
  const clearChatBtn = document.getElementById("clearChatBtn");
  const micBtn = document.getElementById("micBtn");
  const themeToggle = document.getElementById("themeToggle");
  const themeIcon = document.getElementById("themeIcon");
  const themeLabel = document.getElementById("themeLabel");
  const sidebar = document.getElementById("sidebar");
  const sidebarOpen = document.getElementById("sidebarOpen");
  const sidebarClose = document.getElementById("sidebarClose");
  const sidebarOverlay = document.getElementById("sidebarOverlay");
  const actionsTemplate = document.getElementById("messageActionsTemplate");

  // ----------------------------- Init -----------------------------
  document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initVoiceRecognition();
    loadSessions();
    autoResizeTextarea();
    bindEvents();
  });

  function bindEvents() {
    sendBtn.addEventListener("click", handleSend);
    messageInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    });
    messageInput.addEventListener("input", autoResizeTextarea);

    newChatBtn.addEventListener("click", startNewChat);
    clearChatBtn.addEventListener("click", clearCurrentChat);
    micBtn.addEventListener("click", toggleVoiceInput);
    themeToggle.addEventListener("click", toggleTheme);

    sidebarOpen.addEventListener("click", () => toggleSidebar(true));
    sidebarClose.addEventListener("click", () => toggleSidebar(false));
    sidebarOverlay.addEventListener("click", () => toggleSidebar(false));

    document.querySelectorAll(".chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        messageInput.value = chip.dataset.prompt;
        handleSend();
      });
    });
  }

  // ----------------------------- Sidebar (mobile) -----------------------------
  function toggleSidebar(open) {
    sidebar.classList.toggle("open", open);
    sidebarOverlay.classList.toggle("active", open);
  }

  // ----------------------------- Theme -----------------------------
  function initTheme() {
    const saved = getStoredTheme();
    applyTheme(saved);
  }

  function getStoredTheme() {
    // No localStorage available in this environment reliably across contexts,
    // so we fall back to the OS preference each load; toggle still works live.
    return window.__cookwithme_theme || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    window.__cookwithme_theme = theme;
    themeIcon.textContent = theme === "dark" ? "☀️" : "🌙";
    themeLabel.textContent = theme === "dark" ? "Light Mode" : "Dark Mode";
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "light";
    applyTheme(current === "dark" ? "light" : "dark");
  }

  // ----------------------------- Textarea auto-resize -----------------------------
  function autoResizeTextarea() {
    messageInput.style.height = "auto";
    messageInput.style.height = Math.min(messageInput.scrollHeight, 140) + "px";
  }

  // ----------------------------- Sessions (sidebar history) -----------------------------
  async function loadSessions() {
    try {
      const res = await fetch("/api/sessions");
      const data = await res.json();
      if (data.success) {
        renderSessionList(data.sessions);
      }
    } catch (err) {
      console.error("Failed to load sessions:", err);
    }
  }

  function renderSessionList(sessions) {
    chatHistoryList.innerHTML = "";
    if (!sessions.length) {
      const empty = document.createElement("div");
      empty.className = "chat-history-item";
      empty.style.color = "var(--text-secondary)";
      empty.textContent = "No chats yet";
      chatHistoryList.appendChild(empty);
      return;
    }

    sessions.forEach((session) => {
      const item = document.createElement("div");
      item.className = "chat-history-item" + (session.id === currentSessionId ? " active" : "");
      item.dataset.sessionId = session.id;

      const titleSpan = document.createElement("span");
      titleSpan.textContent = session.title;
      titleSpan.style.overflow = "hidden";
      titleSpan.style.textOverflow = "ellipsis";

      const delBtn = document.createElement("button");
      delBtn.className = "del-btn";
      delBtn.textContent = "✕";
      delBtn.title = "Delete chat";
      delBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        deleteSession(session.id);
      });

      item.appendChild(titleSpan);
      item.appendChild(delBtn);
      item.addEventListener("click", () => openSession(session.id));
      chatHistoryList.appendChild(item);
    });
  }

  async function openSession(sessionId) {
    currentSessionId = sessionId;
    toggleSidebar(false);
    chatWindow.innerHTML = "";
    showLoadingSpinner(true);

    try {
      const res = await fetch(`/api/sessions/${sessionId}`);
      const data = await res.json();
      showLoadingSpinner(false);

      if (data.success && data.messages.length) {
        landing.style.display = "none";
        chatWindow.style.display = "flex";
        data.messages.forEach((m) => appendMessage(m.role, m.content, false));
        scrollToBottom();
      } else {
        landing.style.display = "flex";
        chatWindow.style.display = "none";
      }
    } catch (err) {
      showLoadingSpinner(false);
      console.error("Failed to open session:", err);
    }

    highlightActiveSession();
  }

  function showLoadingSpinner(show) {
    let spinner = document.getElementById("loadingSpinner");
    if (show) {
      if (!spinner) {
        spinner = document.createElement("div");
        spinner.id = "loadingSpinner";
        spinner.className = "loading-spinner";
        chatWindow.appendChild(spinner);
      }
      chatWindow.style.display = "flex";
      landing.style.display = "none";
    } else if (spinner) {
      spinner.remove();
    }
  }

  function highlightActiveSession() {
    document.querySelectorAll(".chat-history-item").forEach((el) => {
      el.classList.toggle("active", el.dataset.sessionId === currentSessionId);
    });
  }

  async function deleteSession(sessionId) {
    try {
      await fetch(`/api/sessions/${sessionId}`, { method: "DELETE" });
      if (sessionId === currentSessionId) {
        startNewChat();
      }
      loadSessions();
    } catch (err) {
      console.error("Failed to delete session:", err);
    }
  }

  function startNewChat() {
    currentSessionId = null;
    chatWindow.innerHTML = "";
    chatWindow.style.display = "none";
    landing.style.display = "flex";
    toggleSidebar(false);
    highlightActiveSession();
  }

  function clearCurrentChat() {
    if (!currentSessionId) {
      startNewChat();
      return;
    }
    if (confirm("Clear this entire chat? This cannot be undone.")) {
      deleteSession(currentSessionId);
    }
  }

  // ----------------------------- Sending messages -----------------------------
  async function handleSend() {
    const text = messageInput.value.trim();
    if (!text || isSending) return;

    isSending = true;
    sendBtn.disabled = true;

    landing.style.display = "none";
    chatWindow.style.display = "flex";

    appendMessage("user", text, false);
    messageInput.value = "";
    autoResizeTextarea();
    scrollToBottom();
    showTyping(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: currentSessionId, message: text }),
      });
      const data = await res.json();

      showTyping(false);

      if (data.success) {
        currentSessionId = data.session_id;
        appendMessage("assistant", data.reply, true);
        loadSessions();
      } else {
        appendMessage("assistant", `⚠️ ${data.error || "Something went wrong. Please try again."}`, true);
      }
    } catch (err) {
      showTyping(false);
      appendMessage("assistant", "⚠️ Couldn't reach the server. Please check your connection and try again.", true);
      console.error(err);
    } finally {
      isSending = false;
      sendBtn.disabled = false;
      scrollToBottom();
    }
  }

  function showTyping(show) {
    typingIndicator.style.display = show ? "flex" : "none";
    if (show) scrollToBottom();
  }

  // ----------------------------- Rendering messages -----------------------------
  function appendMessage(role, content, animate) {
    const row = document.createElement("div");
    row.className = `message-row ${role === "user" ? "user" : "bot"}`;

    const avatar = document.createElement("div");
    avatar.className = `msg-avatar ${role === "user" ? "user-avatar" : "bot-avatar"}`;
    avatar.textContent = role === "user" ? "🙂" : "👨‍🍳";

    const col = document.createElement("div");
    col.className = "message-col";

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.innerHTML = formatContent(content);

    col.appendChild(bubble);

    if (role === "assistant") {
      const actions = actionsTemplate.content.cloneNode(true);
      const actionsEl = actions.querySelector(".msg-actions");
      wireMessageActions(actionsEl, content);
      col.appendChild(actionsEl);
    }

    row.appendChild(avatar);
    row.appendChild(col);
    chatWindow.appendChild(row);

    if (!animate) row.style.animation = "none";
  }

  function formatContent(text) {
    // Minimal, safe Markdown-ish rendering: escape HTML first, then apply
    // a small set of formatting rules (bold, bullet lists, numbered lists).
    const escaped = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    let html = escaped
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/^-\s+(.*)$/gm, "<li>$1</li>")
      .replace(/(<li>.*<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`);

    return html.replace(/\n/g, "<br>");
  }

  function scrollToBottom() {
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  // ----------------------------- Message actions -----------------------------
  function wireMessageActions(actionsEl, rawText) {
    actionsEl.querySelector(".copy-btn").addEventListener("click", () => copyText(rawText));
    actionsEl.querySelector(".print-btn").addEventListener("click", () => printText(rawText));
    actionsEl.querySelector(".pdf-btn").addEventListener("click", () => downloadAsPdf(rawText));
    actionsEl.querySelector(".share-btn").addEventListener("click", () => shareText(rawText));
  }

  function copyText(text) {
    navigator.clipboard.writeText(text).then(() => {
      flashFeedback("Copied to clipboard!");
    }).catch(() => {
      flashFeedback("Couldn't copy — please copy manually.");
    });
  }

  function printText(text) {
    const win = window.open("", "_blank");
    win.document.write(`
      <html>
        <head><title>CookWithMe Recipe</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 32px; white-space: pre-wrap; line-height: 1.6; color: #2B2118; }
          h1 { color: #FF914D; }
        </style>
        </head>
        <body>
          <h1>🍳 CookWithMe Recipe</h1>
          <div>${formatContent(text)}</div>
        </body>
      </html>
    `);
    win.document.close();
    win.focus();
    win.print();
  }

  function downloadAsPdf(text) {
    // Uses the browser's print-to-PDF via a print dialog, which requires
    // no extra dependencies and works offline. The user selects
    // "Save as PDF" as the destination.
    flashFeedback("Opening print dialog — choose 'Save as PDF' as the destination.");
    printText(text);
  }

  function shareText(text) {
    if (navigator.share) {
      navigator.share({ title: "CookWithMe Recipe", text }).catch(() => {});
    } else {
      copyText(text);
      flashFeedback("Sharing isn't supported here — copied instead!");
    }
  }

  function flashFeedback(message) {
    const toast = document.createElement("div");
    toast.textContent = message;
    toast.style.cssText = `
      position: fixed; bottom: 90px; left: 50%; transform: translateX(-50%);
      background: var(--color-primary); color: #fff; padding: 10px 18px;
      border-radius: 999px; font-size: 13px; z-index: 999; box-shadow: var(--shadow-medium);
      transition: opacity 0.3s ease;
    `;
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 1800);
  }

  // ----------------------------- Voice input -----------------------------
  function initVoiceRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      micBtn.style.display = "none";
      return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      messageInput.value = (messageInput.value + " " + transcript).trim();
      autoResizeTextarea();
    };

    recognition.onend = () => {
      isRecording = false;
      micBtn.classList.remove("recording");
    };

    recognition.onerror = () => {
      isRecording = false;
      micBtn.classList.remove("recording");
    };
  }

  function toggleVoiceInput() {
    if (!recognition) return;
    if (isRecording) {
      recognition.stop();
    } else {
      recognition.start();
      isRecording = true;
      micBtn.classList.add("recording");
    }
  }

})();
