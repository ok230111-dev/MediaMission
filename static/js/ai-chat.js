const toggleBtn = document.getElementById("aiChatToggle");
const closeBtn = document.getElementById("aiChatClose");
const clearBtn = document.getElementById("aiChatClear");
const panel = document.getElementById("aiChatPanel");
const messagesEl = document.getElementById("aiChatMessages");
const input = document.getElementById("aiChatInput");
const sendBtn = document.getElementById("aiChatSend");

// Отримуємо ID користувача та створюємо унікальний ключ для localStorage
const currentUserId = panel?.dataset.userId || "guest";
const storageKey = `aiChatHistory_${currentUserId}`;

// Завантажуємо історію саме поточного користувача
let history = JSON.parse(localStorage.getItem(storageKey) || "[]");

// Відновлюємо збережені повідомлення під час завантаження
history.forEach(msg => appendMessage(msg.role === "user" ? "user" : "bot", msg.content));

toggleBtn.addEventListener("click", () => {
  panel.classList.toggle("d-none");
  if (!panel.classList.contains("d-none")) input.focus();
});
closeBtn.addEventListener("click", () => panel.classList.add("d-none"));

// Обробник для кнопки очищення чату
if (clearBtn) {
  clearBtn.addEventListener("click", () => {
    history = [];
    localStorage.removeItem(storageKey);
    
    // Скидаємо вікно чату до початкового привітання
    messagesEl.innerHTML = '';
    const greetingText = panel.dataset.greeting || "Привіт! Чим я можу допомогти?";
    appendMessage("bot", greetingText);
  });
}

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
      
      // Зберігаємо в історію та залишаємо тільки останні 10 повідомлень
      history.push({ role: "user", content: text });
      history.push({ role: "assistant", content: data.reply });
      if (history.length > 10) history = history.slice(-10);
      
      localStorage.setItem(storageKey, JSON.stringify(history));

      updateQuotaDisplay(data.rate_limit);
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

function updateQuotaDisplay(rateLimit) {
  const quotaEl = document.getElementById("aiChatQuota");
  if (!quotaEl || !rateLimit) return;

  const remainingReq = rateLimit.remaining_requests;
  const limitReq = rateLimit.limit_requests;
  const remainingTok = rateLimit.remaining_tokens;
  const limitTok = rateLimit.limit_tokens;

  if (remainingReq === null || remainingReq === undefined) {
    quotaEl.textContent = "";
    return;
  }

  quotaEl.innerHTML = `Запитів: ${remainingReq}/${limitReq} · Токенів (хв): ${remainingTok}/${limitTok}`;

  const reqPercent = limitReq ? (parseInt(remainingReq) / parseInt(limitReq)) * 100 : 100;
  const tokPercent = limitTok ? (parseInt(remainingTok) / parseInt(limitTok)) * 100 : 100;
  const lowest = Math.min(reqPercent, tokPercent);

  quotaEl.classList.toggle("low", lowest < 15);
}

sendBtn.addEventListener("click", sendMessage);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendMessage();
});