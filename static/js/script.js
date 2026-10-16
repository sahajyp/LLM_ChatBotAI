/* MyChat front-end logic */
(function () {
  "use strict";

  const chat = document.getElementById("chat");
  const messagesEl = document.getElementById("messages");
  const welcome = document.getElementById("welcome");
  const form = document.getElementById("composer");
  const input = document.getElementById("input");
  const sendBtn = document.getElementById("send-btn");
  const clearBtn = document.getElementById("clear-btn");
  const themeBtn = document.getElementById("theme-btn");

  const BOT_AVATAR = "/static/img/bot.svg";
  const USER_AVATAR = "/static/img/user.svg";

  // Conversation history sent to the server with every request.
  let history = [];
  let busy = false;

  /* ---------- Helpers ---------- */
  function escapeHtml(text) {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  // Very small, safe formatter: ```code blocks```, `inline code`, **bold**.
  function formatMessage(text) {
    return text
      .split("```")
      .map(function (part, i) {
        if (i % 2 === 1) {
          // Code block: drop an optional language label on the first line.
          const nl = part.indexOf("\n");
          const code = nl >= 0 ? part.slice(nl + 1) : part;
          return "<pre><code>" + escapeHtml(code.replace(/\n$/, "")) + "</code></pre>";
        }
        return escapeHtml(part)
          .replace(/`([^`\n]+)`/g, "<code>$1</code>")
          .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
      })
      .join("");
  }

  function scrollToBottom() {
    chat.scrollTop = chat.scrollHeight;
  }

  function addMessage(role, content, options) {
    options = options || {};
    welcome.classList.add("hidden");

    const row = document.createElement("div");
    row.className = "msg " + (role === "user" ? "user" : "bot") + (options.error ? " error" : "");

    const avatar = document.createElement("img");
    avatar.className = "avatar";
    avatar.alt = "";
    avatar.src = role === "user" ? USER_AVATAR : BOT_AVATAR;

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    if (options.html) {
      bubble.innerHTML = content;
    } else if (role === "user") {
      bubble.textContent = content;
    } else {
      bubble.innerHTML = formatMessage(content);
    }

    row.appendChild(avatar);
    row.appendChild(bubble);
    messagesEl.appendChild(row);
    scrollToBottom();
    return row;
  }

  function showTyping() {
    return addMessage("bot", '<div class="typing"><span></span><span></span><span></span></div>', { html: true });
  }

  function setBusy(state) {
    busy = state;
    input.disabled = state;
    updateSendState();
  }

  function updateSendState() {
    sendBtn.disabled = busy || input.value.trim().length === 0;
  }

  function autoResize() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 180) + "px";
  }

  /* ---------- Sending ---------- */
  async function sendMessage(text) {
    text = text.trim();
    if (!text || busy) return;

    addMessage("user", text);
    history.push({ role: "user", content: text });

    input.value = "";
    autoResize();
    setBusy(true);
    const typingRow = showTyping();

    try {
      const res = await fetch("/chatbot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history }),
      });
      const data = await res.json().catch(function () { return {}; });

      typingRow.remove();

      if (!res.ok || data.error) {
        throw new Error(data.error || "The server returned an error (" + res.status + ").");
      }

      history.push({ role: "assistant", content: data.response });
      addMessage("bot", data.response);
    } catch (err) {
      typingRow.remove();
      // Remove the failed user turn from history so the next try is clean.
      history.pop();
      addMessage("bot", "Sorry, something went wrong: " + err.message, { error: true });
    } finally {
      setBusy(false);
      input.focus();
    }
  }

  /* ---------- Events ---------- */
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    sendMessage(input.value);
  });

  input.addEventListener("input", function () {
    autoResize();
    updateSendState();
  });

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      sendMessage(input.value);
    }
  });

  document.querySelectorAll(".chip").forEach(function (chip) {
    chip.addEventListener("click", function () {
      sendMessage(chip.getAttribute("data-prompt"));
    });
  });

  clearBtn.addEventListener("click", function () {
    if (busy) return;
    history = [];
    messagesEl.innerHTML = "";
    welcome.classList.remove("hidden");
    input.focus();
  });

  themeBtn.addEventListener("click", function () {
    const root = document.documentElement;
    const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("mychat-theme", next); } catch (e) { /* ignore */ }
  });

  input.focus();
  updateSendState();
})();
