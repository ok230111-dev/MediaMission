document.addEventListener("DOMContentLoaded", function() {
  loadAdminMissions();

  // Створюємо екземпляр Tab для кожної кнопки
  const triggerTabList = document.querySelectorAll('.btn-admin-header .btn');
  triggerTabList.forEach(triggerEl => {
    const tabTrigger = new bootstrap.Tab(triggerEl);
    
    triggerEl.addEventListener('click', function(event) {
      event.preventDefault();
      tabTrigger.show();
    });
  });

  // Відновлюємо збережену вкладку
  const savedTab = localStorage.getItem('activeAdminTab');
  if (savedTab) {
    const targetButton = document.querySelector(`[data-bs-target="#${savedTab}"]`);
    if (targetButton) {
      const tab = new bootstrap.Tab(targetButton);
      tab.show();
    }
  }

  // Зберігаємо активну вкладку
  document.querySelectorAll('.btn-admin-header .btn').forEach(btn => {
    btn.addEventListener('shown.bs.tab', function(event) {
      const targetId = event.target.getAttribute('data-bs-target');
      if (targetId) {
        localStorage.setItem('activeAdminTab', targetId.replace('#', ''));
      }
    });
  });

  // --- ОБРОБНИК ЗМІНИ ТИПУ АБЗАЦУ ---
  document.addEventListener("change", (e) => {
    if (e.target.classList.contains("paragraph-type")) {
      const row = e.target.closest(".paragraph-row");
      if (!row) return;
      
      const fileInput = row.querySelector(".paragraph-file");
      const urlInput = row.querySelector(".paragraph-url");
      const textInput = row.querySelector(".paragraph-text");
      const type = e.target.value;

      // Ховаємо всі поля
      if (fileInput) fileInput.classList.add("d-none");
      if (urlInput) urlInput.classList.add("d-none");
      if (textInput) textInput.classList.remove("d-none");

      // Показуємо потрібне поле
      if (type === "image" || type === "video") {
        if (fileInput) fileInput.classList.remove("d-none");
        if (textInput) textInput.classList.add("d-none");
      } else if (type === "website") {
        if (urlInput) urlInput.classList.remove("d-none");
        if (textInput) textInput.classList.add("d-none");
      } else {
        // Для тексту показуємо textarea
        if (textInput) textInput.classList.remove("d-none");
      }
    }
  });

  // Автоматично додаємо перше питання при завантаженні
  addQuestion();

  const saveBtn = document.getElementById("saveMissionBtn");
  if (saveBtn) {
    saveBtn.addEventListener("click", saveMission);
  }

  // Ініціалізація першого абзацу
  const firstParagraph = document.querySelector(".paragraph-row");
  if (firstParagraph) {
    const select = firstParagraph.querySelector(".paragraph-type");
    if (select) {
      // Тригер зміни для налаштування початкового стану
      const event = new Event("change");
      select.dispatchEvent(event);
    }
  }

  // Завантаження звернень підтримки та фільтр
  loadSupportTickets();
  const filterEl = document.getElementById("ticketStatusFilter");
  if (filterEl) {
    filterEl.addEventListener("change", renderTickets);
  }

  // Фільтр ідей
  document.getElementById("ideaStatusFilter")?.addEventListener("change", renderIdeas);
  document
    .getElementById("support_idea-tab")
    ?.addEventListener("shown.bs.tab", loadIdeas);

  // Відгуки: фільтри + завантаження при відкритті вкладки
  document.querySelectorAll('[data-filter]').forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll('[data-filter]').forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentReviewFilter = btn.dataset.filter;
      renderReviews();
    });
  });

  document
    .getElementById("reviews-tab")
    ?.addEventListener("shown.bs.tab", loadReviews);

  // Якщо кнопки табів мають інші id/атрибути — підвантажуємо відгуки одразу як запасний варіант
  loadReviews();
});

// --- РОБОТА З АБЗАЦАМИ ---
function addParagraph() {
  const container = document.getElementById("paragraphs-container");
  if (!container) return;

  const paragraphDiv = document.createElement("div");
  paragraphDiv.className = "mb-3 paragraph-row border rounded-3 p-3";
  paragraphDiv.innerHTML = `
    <select class="form-select mb-2 paragraph-type">
      <option value="text">📝 Текст</option>
      <option value="image">🖼️ Фото</option>
      <option value="video">🎬 Відео</option>
      <option value="website">🌐 Посилання на сайт</option>
    </select>

    <textarea class="form-control mb-2 paragraph-text" rows="3" placeholder="Текст абзацу / підпис"></textarea>
    <input type="file" class="form-control mb-2 paragraph-file d-none" accept="image/*,video/*" />
    <input type="url" class="form-control mb-2 paragraph-url d-none" placeholder="https://..." />

    <button type="button" class="btn btn-outline-danger btn-sm" onclick="removeParagraph(this)">Видалити</button>
  `;

  container.appendChild(paragraphDiv);
  reindexParagraphs();
}

function removeParagraph(btn) {
  const row = btn.closest(".paragraph-row");
  if (row) {
    row.remove();
    reindexParagraphs();
  }
}

function reindexParagraphs() {
  document.querySelectorAll("#paragraphs-container .paragraph-row").forEach((row, index) => {
    const textarea = row.querySelector(".paragraph-text");
    if (textarea) {
      textarea.placeholder = `Абзац ${index + 1}`;
    }
  });
}

// --- РОБОТА З ПИТАННЯМИ ---
function addQuestion() {
  const container = document.getElementById("questions-container");
  if (!container) return;
  
  const qIndex = Date.now();

  const questionCard = document.createElement("div");
  questionCard.className = "card shadow-sm mb-4 question-card";
  questionCard.innerHTML = `
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h4 class="m-0 question-title">Питання</h4>
        <button type="button" class="btn btn-outline-danger btn-sm" onclick="removeQuestion(this)">
          Видалити питання
        </button>
      </div>

      <input
        class="form-control mb-3 question-text"
        placeholder="Текст питання"
        required
      />

      <select class="form-select mb-3 question-type" onchange="toggleOptionInputType(this, '${qIndex}')">
        <option value="single_choice">Одна відповідь (Single Choice)</option>
        <option value="multiple_choice">Кілька відповідей (Multiple Choice)</option>
      </select>

      <label class="form-label fw-bold mb-2">Варіанти відповідей (позначте правильні):</label>

      ${[1, 2, 3, 4]
        .map(
          (i) => `
        <div class="input-group mb-2 option-row">
          <div class="input-group-text">
            <input
              class="form-check-input mt-0 correct"
              type="radio"
              name="q_correct_${qIndex}"
              value="${i - 1}"
              title="Позначити як правильну"
            />
          </div>
          <input
            type="text"
            class="form-control option"
            placeholder="Варіант ${i}"
          />
        </div>
      `
        )
        .join("")}
    </div>
  `;

  container.appendChild(questionCard);
  reindexQuestions();
}

function removeQuestion(btn) {
  const card = btn.closest(".question-card");
  if (card) {
    card.remove();
    reindexQuestions();
  }
}

function reindexQuestions() {
  document.querySelectorAll(".question-card").forEach((card, index) => {
    const title = card.querySelector(".question-title");
    if (title) {
      title.textContent = `Питання ${index + 1}`;
    }
  });
}

function toggleOptionInputType(selectElem, qIndex) {
  const card = selectElem.closest(".question-card");
  if (!card) return;
  
  const inputs = card.querySelectorAll(".correct");
  const isMultiple = selectElem.value === "multiple_choice";

  inputs.forEach((input) => {
    input.type = isMultiple ? "checkbox" : "radio";
    input.name = isMultiple ? `q_correct_multi_${qIndex}` : `q_correct_${qIndex}`;
  });
}

// --- ЗБЕРЕЖЕННЯ ---
async function saveMission() {
  const saveBtn = document.getElementById("saveMissionBtn");

  const title = document.getElementById("missionTitle")?.value.trim();
  const subtitle = document.getElementById("missionSubTitle")?.value.trim();

  if (!title || !subtitle) {
    alert("Будь ласка, заповніть назву та підзаголовок місії.");
    return;
  }

  const contentsArray = [];
  const filesToUpload = [];

  // Перевірка абзаців
  const paragraphRows = document.querySelectorAll('.paragraph-row');
  for (let index = 0; index < paragraphRows.length; index++) {
    const row = paragraphRows[index];
    const pNum = index + 1;

    const type = row.querySelector('.paragraph-type')?.value;
    const textInput = row.querySelector('.paragraph-text')?.value.trim();
    const fileInput = row.querySelector('.paragraph-file');
    const urlInput = row.querySelector('.paragraph-url')?.value.trim();

    if (!type) {
      alert(`Помилка в абзаці №${pNum}: Не вибрано тип абзацу.`);
      return;
    }

    if (type === 'text' && !textInput) {
      alert(`Будь ласка, введіть текст для абзацу №${pNum} або видаліть порожній блок.`);
      return;
    }

    if ((type === 'image' || type === 'video') && (!fileInput || !fileInput.files || !fileInput.files[0])) {
      const fileTypeName = type === 'image' ? 'фотографію' : 'відео';
      alert(`Будь ласка, виберіть ${fileTypeName} для абзацу №${pNum}.`);
      return;
    }

    if (type === 'website' && !urlInput) {
      alert(`Будь ласка, вкажіть URL-адресу сайту для абзацу №${pNum}.`);
      return;
    }

    // Формуємо контент
    if (type === 'website') {
      contentsArray.push({
        order: index + 1,
        text: `[WEBSITE]${urlInput}${textInput ? '\n' + textInput : ''}`
      });
    } else if ((type === 'image' || type === 'video') && fileInput && fileInput.files && fileInput.files[0]) {
      const marker = type === 'image' ? '[IMAGE]' : '[VIDEO]';
      filesToUpload.push({ key: `content_file_${index + 1}`, file: fileInput.files[0] });
      contentsArray.push({
        order: index + 1,
        text: `${marker}PENDING_UPLOAD_${index + 1}${textInput ? '\n' + textInput : ''}`
      });
    } else {
      contentsArray.push({ order: index + 1, text: textInput || '' });
    }
  }

  // Збір питань
  const questionsArray = [];
  const questionCards = document.querySelectorAll(".question-card");

  for (const card of questionCards) {
    const qText = card.querySelector(".question-text")?.value.trim();
    const qType = card.querySelector(".question-type")?.value;

    if (!qText) {
      alert("Будь ласка, заповніть текст для всіх питань.");
      return;
    }

    const options = [];
    card.querySelectorAll(".option").forEach((input) => {
      options.push(input.value.trim());
    });

    const correct = [];
    card.querySelectorAll(".correct").forEach((input, optIndex) => {
      if (input.checked) {
        correct.push(optIndex);
      }
    });

    questionsArray.push({
      question: qText,
      type: qType || 'single_choice',
      options: options,
      correct_answer: correct,
    });
  }

  if (questionsArray.length === 0) {
    alert("Будь ласка, додайте хоча б одне питання.");
    return;
  }

  // Підготовка FormData
  const formData = new FormData();
  formData.append("title", title);
  formData.append("subtitle", subtitle);
  formData.append("exercise", document.getElementById("missionExercise")?.value.trim() || "");
  formData.append("type", document.getElementById("missionType")?.value || "news");
  formData.append("difficulty", document.getElementById("missionDifficulty")?.value || "1");
  formData.append("xp", document.getElementById("missionXP")?.value || "20");
  formData.append("time", document.getElementById("missionTime")?.value || "5");

  const imageInput = document.getElementById("image");
  if (imageInput && imageInput.files && imageInput.files[0]) {
    formData.append("image", imageInput.files[0]);
  }

  filesToUpload.forEach(({ key, file }) => {
    formData.append(key, file);
  });

  formData.append("contents", JSON.stringify(contentsArray));
  formData.append("questions", JSON.stringify(questionsArray));

  try {
    saveBtn.disabled = true;
    saveBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Збереження...`;

    const response = await fetch("/api/admin/add_mission", {
      method: "POST",
      body: formData,
    });

    const result = await response.json();

    if (result.success) {
      showToast('✅ Успіх', 'Місію успішно створено!', 'success');
      setTimeout(() => window.location.reload(), 1500);
    } else {
      showToast('❌ Помилка', result.error || 'Невідома помилка при збереженні', 'danger');
    }
  } catch (err) {
    console.error(err);
    showToast('❌ Помилка', 'Сталася мережева помилка при збереженні місії.', 'danger');
  } finally {
    saveBtn.disabled = false;
    saveBtn.innerHTML = `<i class="bi bi-check-circle-fill me-2"></i>Зберегти місію`;
  }
}

// --- ВИДАЛЕННЯ КОРИСТУВАЧА ---
function deleteUser(userId) {
  if (!confirm('Ви впевнені, що хочете видалити цього користувача?')) {
    return;
  }
  
  const buttons = document.querySelectorAll(`[onclick*="deleteUser(${userId}"]`);
  buttons.forEach(btn => {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span>`;
  });
  
  fetch(`/api/admin/delete_user/${userId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json'
    }
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      showToast('✅ Успіх', 'Користувача успішно видалено!', 'success');
      setTimeout(() => location.reload(), 1500);
    } else {
      showToast('❌ Помилка', data.error || 'Не вдалося видалити користувача', 'danger');
    }
  })
  .catch(error => {
    console.error('Error:', error);
    showToast('❌ Помилка', 'Сталася помилка при видаленні користувача', 'danger');
  })
  .finally(() => {
    buttons.forEach(btn => {
      btn.disabled = false;
      btn.innerHTML = `<i class="bi bi-trash"></i>`;
    });
  });
}

// --- ВИДАЛЕННЯ МІСІЇ ---
async function deleteMission(missionId, missionTitle, hasNotifications, notificationsCount) {
    let confirmMessage = `Ви дійсно бажаєте видалити місію "${missionTitle || '#' + missionId}"?`;
    
    if (hasNotifications) {
        confirmMessage = `⚠️ УВАГА!\n\nМісія "${missionTitle || '#' + missionId}" має ${notificationsCount} пов'язаних сповіщень.\n\nПри видаленні місії всі ці сповіщення та їх отримувачі будуть видалені.\n\nПродовжити?`;
    }

    if (!confirm(confirmMessage)) {
        return;
    }

    const buttons = document.querySelectorAll(`[onclick*="deleteMission(${missionId}"]`);
    buttons.forEach(btn => {
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span>`;
    });

    try {
        const response = await fetch(`/api/admin/delete_mission/${missionId}`, {
            method: "DELETE",
            headers: { "Content-Type": "application/json" }
        });

        const result = await response.json();

        if (result.success) {
            showToast('✅ Успіх', result.message || `Місію #${missionId} успішно видалено!`, 'success');
            loadAdminMissions(); // Оновлюємо список
        } else {
            showToast('❌ Помилка', result.error || 'Не вдалося видалити місію', 'danger');
        }
    } catch (err) {
        console.error(err);
        showToast('❌ Помилка', 'Сталася помилка при відправці запиту', 'danger');
    } finally {
        buttons.forEach(btn => {
            btn.disabled = false;
            btn.innerHTML = `<i class="bi bi-trash"></i>`;
        });
    }
}

async function sendXpAdjustment(userId, amount) {
  if (!amount || amount === 0) {
    alert("Введіть ненульове значення XP");
    return;
  }

  try {
    const response = await fetch(`/api/admin/adjust_xp/${userId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount })
    });
    const data = await response.json();

    if (data.success) {
      const el = document.getElementById(`xp-value-${userId}`);
      if (el) el.textContent = data.new_total_xp;

      // очищуємо поле вводу, якщо воно є
      const input = document.getElementById(`xp-input-${userId}`);
      if (input) input.value = "";
    } else {
      alert(data.error || "Помилка зміни XP");
    }
  } catch (err) {
    console.error("Помилка запиту:", err);
    alert("Сталася помилка при зверненні до сервера");
  }
}

function adjustXp(userId) {
  const input = document.getElementById(`xp-input-${userId}`);
  const amount = parseInt(input.value, 10);
  sendXpAdjustment(userId, amount);
}

function quickAdjustXp(userId, amount) {
  sendXpAdjustment(userId, amount);
}

// --- ФУНКЦІЯ ДЛЯ ПОКАЗУ TOAST ПОВІДОМЛЕНЬ ---
function showToast(title, message, type = 'info') {
  // Перевіряємо чи існує контейнер
  let toastContainer = document.getElementById('toastContainer');
  
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toastContainer';
    toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    toastContainer.style.zIndex = '1050';
    document.body.appendChild(toastContainer);
  }
  
  const toastId = 'toast-' + Date.now();
  const iconMap = {
    'success': 'bi-check-circle-fill text-white',
    'danger': 'bi-x-circle-fill text-white',
    'warning': 'bi-exclamation-triangle-fill text-white',
    'info': 'bi-info-circle-fill text-white'
  };
  
  const iconClass = iconMap[type] || iconMap.info;
  const bgClass = `bg-${type}`;
  
  const toastEl = document.createElement('div');
  toastEl.id = toastId;
  toastEl.className = `toast align-items-center text-white ${bgClass} border-0`;
  toastEl.role = 'alert';
  toastEl.ariaLive = 'assertive';
  toastEl.ariaAtomic = 'true';
  
  toastEl.innerHTML = `
    <div class="d-flex">
      <div class="toast-body d-flex align-items-center">
        <i class="bi ${iconClass} me-2 fs-5"></i>
        <div>
          <strong>${title}</strong>
          ${message ? `<br><small>${message}</small>` : ''}
        </div>
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;
  
  toastContainer.appendChild(toastEl);
  
  // Ініціалізуємо Bootstrap Toast
  const bsToast = new bootstrap.Toast(toastEl, { 
    delay: 5000,
    autohide: true
  });
  
  bsToast.show();
  
  // Видаляємо елемент після закриття
  toastEl.addEventListener('hidden.bs.toast', () => {
    toastEl.remove();
  });
}

// --- ЗАВАНТАЖЕННЯ СПИСКУ МІСІЙ ---
async function loadAdminMissions() {
  const tbody = document.getElementById("adminMissionsTableBody");
  if (!tbody) return;

  try {
    const response = await fetch("/api/admin/missions");
    const data = await response.json();

    if (!data.success) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger py-3">Помилка: ${data.error}</td></tr>`;
      return;
    }

    if (data.missions.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">Місій поки немає. Створіть першу!</td></tr>`;
      return;
    }

    tbody.innerHTML = data.missions.map(m => `
      <tr>
        <td class="ps-3 fw-bold">#${m.id}</td>
        <td>
          <div class="fw-bold">${escapeHtml(m.title)}</div>
          <div class="small text-muted">${escapeHtml(m.subtitle || '')}</div>
        </td>
        <td><span class="badge bg-secondary-subtle text-secondary">${m.type || '—'}</span></td>
        <td>
          ${m.difficulty === '1' ? '🟢 Легка' : (m.difficulty === '2' ? '🟡 Середня' : '🔴 Складна')}
        </td>
        <td><span class="fw-bold text-warning-emphasis">${m.xp} XP</span></td>
        <td>
          ${m.has_notifications ? `<span class="badge bg-warning text-dark" title="Має ${m.notifications_count} сповіщень">
            <i class="bi bi-bell"></i> ${m.notifications_count}
          </span>` : '<span class="badge bg-secondary">Немає сповіщень</span>'}
        </td>
        <td class="text-end pe-3">
          <div class="btn-group btn-group-sm">
            <a href="/mission/${m.id}" target="_blank" class="btn btn-outline-secondary" title="Переглянути">
              👁️
            </a>
            <button class="btn btn-outline-danger" onclick="deleteMission(${m.id}, '${escapeHtml(m.title)}', ${m.has_notifications || false}, ${m.notifications_count || 0})" title="Видалити">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `).join('');

  } catch (err) {
    console.error("Помилка завантаження місій:", err);
    tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger py-3">Мережева помилка при завантаженні.</td></tr>`;
  }
}

// --- ДОДАТКОВА ФУНКЦІЯ ДЛЯ ОНОВЛЕННЯ СПИСКУ ---
function refreshMissions() {
  loadAdminMissions();
  showToast('🔄 Оновлення', 'Список місій оновлено', 'info');
}

const TICKET_STATUS_CONFIG = {
  open:     { emoji: "🟡", label: "Відкрито",    class: "bg-warning-subtle text-warning-emphasis" },
  answered: { emoji: "🔵", label: "Відповідано",  class: "bg-info-subtle text-info-emphasis" },
  solved:   { emoji: "🟢", label: "Вирішено",     class: "bg-success-subtle text-success-emphasis" },
  closed:   { emoji: "🔴", label: "Закрито",      class: "bg-danger-subtle text-danger-emphasis" }
};

let allTickets = [];

async function loadSupportTickets() {
  const container = document.getElementById("supportTicketsContainer");
  if (!container) return;

  container.innerHTML = `<div class="text-center text-muted py-4">Завантаження...</div>`;

  try {
    const response = await fetch("/api/admin/support_tickets");
    const data = await response.json();

    if (!data.success) {
      container.innerHTML = `<div class="text-center text-danger py-4">Помилка: ${data.error}</div>`;
      return;
    }

    allTickets = data.tickets;
    renderTickets();
  } catch (err) {
    console.error("Помилка завантаження звернень:", err);
    container.innerHTML = `<div class="text-center text-danger py-4">Мережева помилка</div>`;
  }
}

function renderTickets() {
  const container = document.getElementById("supportTicketsContainer");
  const filter = document.getElementById("ticketStatusFilter")?.value || "all";

  const filtered = filter === "all" ? allTickets : allTickets.filter(t => t.status === filter);

  if (filtered.length === 0) {
    container.innerHTML = `<div class="text-center text-muted py-4">Звернень немає</div>`;
    return;
  }

  container.innerHTML = filtered.map(tk => {
    const status = TICKET_STATUS_CONFIG[tk.status] || TICKET_STATUS_CONFIG.open;
    const browser = tk.browser_info || {};

    return `
      <div class="border rounded-3 p-3 mb-3" id="ticket-${tk.id}">
        <div class="d-flex justify-content-between align-items-start mb-2 flex-wrap gap-2">
          <div>
            <span class="fw-bold">#${tk.id}</span>
            <span class="badge bg-secondary-subtle text-secondary ms-2">${escapeHtml(tk.category)}</span>
            ${tk.issue_type ? `<span class="badge bg-secondary-subtle text-secondary ms-1">${escapeHtml(tk.issue_type)}</span>` : ''}
          </div>
          <span class="badge status-badge ${status.class}">${status.emoji} ${status.label}</span>
        </div>

        <div class="small text-muted mb-2">
          Від: <strong>${escapeHtml(tk.user_email)}</strong> · ${tk.created_at}
          ${tk.mission_title ? ` · Місія: <strong>${escapeHtml(tk.mission_title)}</strong>` : ''}
        </div>

        ${tk.description ? `<div class="mb-2">${escapeHtml(tk.description)}</div>` : ''}

        ${tk.screenshot_url ? `
          <a href="${tk.screenshot_url}" target="_blank" class="d-inline-block mb-2">
            <img src="${tk.screenshot_url}" style="max-width: 200px; border-radius: 8px; border: 1px solid rgba(0,0,0,0.1);">
          </a>
        ` : ''}

        <details class="small text-muted mb-2">
          <summary style="cursor: pointer;">Технічна інформація</summary>
          <div class="mt-2">
            Браузер: ${escapeHtml(browser.browser || '—')}<br>
            Мова: ${escapeHtml(browser.language || '—')}<br>
            Тема: ${escapeHtml(browser.theme || '—')}<br>
            Екран: ${escapeHtml(browser.screen || '—')}<br>
            URL: ${escapeHtml(browser.url || '—')}
          </div>
        </details>

        <div class="d-flex gap-2 flex-wrap align-items-center mt-3 pt-3 border-top">
          <select class="form-select form-select-sm" style="width: auto" id="status-select-${tk.id}">
            ${Object.entries(TICKET_STATUS_CONFIG).map(([key, cfg]) =>
              `<option value="${key}" ${tk.status === key ? 'selected' : ''}>${cfg.emoji} ${cfg.label}</option>`
            ).join('')}
          </select>
          <button class="btn btn-sm btn-success" onclick="saveTicketUpdate(${tk.id})">
            <i class="bi bi-check-lg me-1"></i> (1) Зберегти статус
          </button>
          <button class="btn btn-sm btn-primary" onclick="toggleReplyBox(${tk.id})">
            <i class="bi bi-reply-fill me-1"></i>Відповісти
          </button>
        </div>

        <div class="d-none mt-2" id="reply-box-${tk.id}">
          <textarea class="form-control form-control-sm mb-2" id="reply-text-${tk.id}" rows="2" placeholder="Ваша відповідь...">${tk.admin_reply || ''}</textarea>
          <button class="btn btn-sm btn-success" onclick="saveTicketUpdate(${tk.id})">
            <i class="bi bi-check-lg me-1"></i> (2) Зберегти
          </button>
        </div>

        ${tk.admin_reply ? `
          <div class="small bg-light rounded p-2 mt-2">
            <strong>Ваша відповідь:</strong> ${escapeHtml(tk.admin_reply)}
          </div>
        ` : ''}
      </div>
    `;
  }).join('');
}

function toggleReplyBox(ticketId) {
  document.getElementById(`reply-box-${ticketId}`)?.classList.toggle("d-none");
}

async function saveTicketUpdate(ticketId) {
  const statusSelect = document.getElementById(`status-select-${ticketId}`);
  const replyText = document.getElementById(`reply-text-${ticketId}`);

  try {
    const response = await fetch(`/api/admin/support_tickets/${ticketId}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: statusSelect.value,
        admin_reply: replyText.value.trim()
      })
    });
    const data = await response.json();

    if (data.success) {
      showToast('✅ Збережено', `Звернення #${ticketId} оновлено`, 'success');
      loadSupportTickets();
    } else {
      showToast('❌ Помилка', data.error || 'Не вдалося оновити', 'danger');
    }
  } catch (err) {
    console.error(err);
    showToast('❌ Помилка', 'Мережева помилка', 'danger');
  }
}

const IDEA_STATUS_LABELS = {
  new: { label: "На розгляді", badge: "badge-idea-new", icon: "🆕" },
  good: { label: "Добре", badge: "badge-idea-good", icon: "✅" },
  must_have: { label: "Обов'язково", badge: "badge-idea-must_have", icon: "🔥" },
  not_needed: { label: "Не потрібно", badge: "badge-idea-not_needed", icon: "🚫" },
  not_now: { label: "Не на часі", badge: "badge-idea-not_now", icon: "⏳" },
};

let allIdeas = [];

async function loadIdeas() {
  const container = document.getElementById("ideasContainer");
  if (!container) return;

  container.innerHTML = `<div class="text-center text-muted py-4">Завантаження...</div>`;

  try {
    const res = await fetch("/api/admin/ideas");
    const data = await res.json();

    if (!data.success) {
      container.innerHTML = `<div class="text-center text-danger py-4">Помилка завантаження</div>`;
      return;
    }

    allIdeas = data.ideas;
    renderIdeas();
  } catch (err) {
    container.innerHTML = `<div class="text-center text-danger py-4">Помилка мережі</div>`;
  }
}

function renderIdeas() {
  const container = document.getElementById("ideasContainer");
  const filter = document.getElementById("ideaStatusFilter")?.value || "all";

  const filtered =
    filter === "all" ? allIdeas : allIdeas.filter((i) => i.status === filter);

  if (filtered.length === 0) {
    container.innerHTML = `<div class="text-center text-muted py-4">Немає ідей за цим фільтром</div>`;
    return;
  }

  container.innerHTML = filtered
    .map((idea) => {
      const statusInfo = IDEA_STATUS_LABELS[idea.status] || IDEA_STATUS_LABELS.new;

      const statusButtons = Object.entries(IDEA_STATUS_LABELS)
        .map(
          ([key, info]) => `
          <button
            type="button"
            class="btn btn-sm ${idea.status === key ? "btn-primary" : "btn-outline-secondary"}"
            onclick="setIdeaStatus(${idea.id}, '${key}')"
          >
            ${info.icon} ${info.label}
          </button>
        `
        )
        .join("");

      return `
        <div class="idea-card">
          <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
            <div>
              <h5 class="fw-bold mb-1">${escapeHtml(idea.title)}</h5>
              <div class="text-muted small mb-2">
                ${escapeHtml(idea.user_name)} (${escapeHtml(idea.user_email)}) ·
                ${idea.created_at} ·
                <span class="fw-semibold">${escapeHtml(idea.page)}</span> /
                ${escapeHtml(idea.category)}
              </div>
            </div>
            <span class="badge ${statusInfo.badge} status-badge">
              ${statusInfo.icon} ${statusInfo.label}
            </span>
          </div>

          <p class="mb-2">${escapeHtml(idea.description)}</p>

          ${
            idea.attachment_url
              ? `<img src="${idea.attachment_url}" class="idea-image-preview mb-2" onclick="window.open('${idea.attachment_url}', '_blank')" />`
              : ""
          }

          <div class="d-flex gap-2 flex-wrap mt-2">
            ${statusButtons}
          </div>
        </div>
      `;
    })
    .join("");
}

async function setIdeaStatus(ideaId, status) {
  try {
    const res = await fetch(`/api/admin/ideas/${ideaId}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });

    const data = await res.json();
    if (data.success) {
      const idea = allIdeas.find((i) => i.id === ideaId);
      if (idea) idea.status = status;
      renderIdeas();
    } else {
      alert(data.error || "Не вдалося оновити статус");
    }
  } catch (err) {
    alert("Помилка мережі");
  }
}

// --- ВІДГУКИ ---
let allReviews = [];
let currentReviewFilter = "all";

async function loadReviews() {
  const container = document.getElementById("reviewsList");
  if (!container) return;

  try {
    const res = await fetch("/api/admin/reviews");
    const data = await res.json();
    if (data.success) {
      allReviews = data.reviews;
      renderReviews();
      updatePendingBadge();
    }
  } catch (err) {
    console.error("Помилка завантаження відгуків:", err);
  }
}

function updatePendingBadge() {
  const badge = document.getElementById("reviewsPendingBadge");
  if (!badge) return;

  const pendingCount = allReviews.filter(r => !r.is_approved).length;
  if (pendingCount > 0) {
    badge.textContent = pendingCount;
    badge.style.display = "inline-block";
  } else {
    badge.style.display = "none";
  }
}

function renderReviews() {
  const container = document.getElementById("reviewsList");
  if (!container) return;

  let filtered = allReviews;

  if (currentReviewFilter === "pending") {
    filtered = allReviews.filter(r => !r.is_approved);
  } else if (currentReviewFilter === "approved") {
    filtered = allReviews.filter(r => r.is_approved);
  }

  if (filtered.length === 0) {
    container.innerHTML = `<p class="text-muted text-center py-4">Немає відгуків у цій категорії</p>`;
    return;
  }

  container.innerHTML = filtered.map(r => `
    <div class="card border-0 shadow-sm">
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-start mb-2">
          <div>
            <h6 class="fw-bold mb-0">${escapeHtml(r.display_name)}</h6>
            <span class="text-muted small">${escapeHtml(r.user_email || "Гість")} · ${r.created_at}</span>
          </div>
          <span class="badge ${r.is_approved ? "bg-success" : "bg-warning text-dark"}">
            ${r.is_approved ? "Схвалено" : "На модерації"}
          </span>
        </div>
        <div class="mb-2">
          ${Array.from({length: 5}, (_, i) =>
            `<i class="bi ${i < r.rating ? "bi-star-fill text-warning" : "bi-star text-muted"}"></i>`
          ).join("")}
        </div>
        <p class="mb-3">${escapeHtml(r.text)}</p>
        <div class="d-flex gap-2">
          ${r.is_approved
            ? `<button class="btn btn-sm btn-outline-warning" onclick="toggleReviewApproval(${r.id}, false)">Прибрати з головної</button>`
            : `<button class="btn btn-sm btn-success" onclick="toggleReviewApproval(${r.id}, true)">Схвалити</button>`
          }
          <button class="btn btn-sm btn-outline-danger" onclick="deleteReviewItem(${r.id})">Видалити</button>
        </div>
      </div>
    </div>
  `).join("");
}

async function toggleReviewApproval(id, approve) {
  const endpoint = approve
    ? `/api/admin/reviews/${id}/approve`
    : `/api/admin/reviews/${id}/unapprove`;

  const res = await fetch(endpoint, { method: "POST" });
  const data = await res.json();
  if (data.success) {
    await loadReviews();
  } else {
    alert(data.error || "Помилка");
  }
}

async function deleteReviewItem(id) {
  if (!confirm("Видалити цей відгук назавжди?")) return;

  const res = await fetch(`/api/admin/reviews/${id}`, { method: "DELETE" });
  const data = await res.json();
  if (data.success) {
    await loadReviews();
  } else {
    alert(data.error || "Помилка");
  }
}

// --- ДОПОМІЖНА ФУНКЦІЯ ДЛЯ ЗАХИСТУ ВІД XSS (єдине визначення) ---
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}