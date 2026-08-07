const toggleBtn = document.getElementById("aiChatToggle");
const closeBtn = document.getElementById("aiChatClose");
const panel = document.getElementById("aiChatPanel");
const messagesEl = document.getElementById("aiChatMessages");
const input = document.getElementById("aiChatInput");
const sendBtn = document.getElementById("aiChatSend");

let history = JSON.parse(sessionStorage.getItem("aiChatHistory") || "[]");

// Відновлюємо історію у вигляді на екрані
history.forEach(msg => appendMessage(msg.role === "user" ? "user" : "bot", msg.content));

toggleBtn.addEventListener("click", () => {
  panel.classList.toggle("d-none");
  if (!panel.classList.contains("d-none")) input.focus();
});
closeBtn.addEventListener("click", () => panel.classList.add("d-none"));

function appendMessage(role, text) {
  const div = document.createElement("div");
  div.className = `ai-msg ai-msg-${role}`;
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;

  appendMessage("user", text);
  input.value = "";
  sendBtn.disabled = true;

  const typingEl = document.createElement("div");
  typingEl.className = "ai-msg ai-msg-bot";
  typingEl.textContent = "...";
  messagesEl.appendChild(typingEl);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  // Контекст місії, якщо ми на сторінці місії
  const missionTitleEl = document.querySelector("[data-mission-title]");
  const missionExerciseEl = document.querySelector("[data-mission-exercise]");
  const missionContext = missionTitleEl ? {
    title: missionTitleEl.dataset.missionTitle,
    exercise: missionExerciseEl?.dataset.missionExercise || ""
  } : null;

  try {
    const response = await fetch("/api/ai/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, history, mission_context: missionContext })
    });
    const data = await response.json();

    typingEl.remove();

    if (data.success) {
      appendMessage("bot", data.reply);
      history.push({ role: "user", content: text });
      history.push({ role: "assistant", content: data.reply });
      sessionStorage.setItem("aiChatHistory", JSON.stringify(history));
    } else {
      appendMessage("bot", data.error || "Помилка. Спробуйте ще раз.");
    }
  } catch (err) {
    typingEl.remove();
    appendMessage("bot", "Мережева помилка. Спробуйте пізніше.");
  } finally {
    sendBtn.disabled = false;
  }
}

sendBtn.addEventListener("click", sendMessage);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendMessage();
});