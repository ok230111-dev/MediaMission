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

    if (options.some(opt => !opt)) {
      alert("Будь ласка, заповніть всі варіанти відповідей.");
      return;
    }

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
      alert("Місію успішно створено!");
      window.location.reload();
    } else {
      alert("Помилка при збереженні: " + (result.error || "Невідома помилка"));
    }
  } catch (err) {
    console.error(err);
    alert("Сталася мережева помилка при збереженні місії.");
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
  
  fetch(`/api/admin/delete_user/${userId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json'
    }
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      alert('Користувача видалено!');
      location.reload();
    } else {
      alert('Помилка: ' + (data.error || 'Невідома помилка'));
    }
  })
  .catch(error => {
    console.error('Error:', error);
    alert('Сталася помилка при видаленні користувача');
  });
}

// 1. Завантаження та вивід списку місій
async function loadAdminMissions() {
  const tbody = document.getElementById("adminMissionsTableBody");
  if (!tbody) return;

  try {
    const response = await fetch("/api/admin/missions");
    const data = await response.json();

    if (!data.success) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger py-3">Помилка: ${data.error}</td></tr>`;
      return;
    }

    if (data.missions.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted">Місій поки немає. Створіть першу!</td></tr>`;
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
        <td class="text-end pe-3">
          <div class="btn-group btn-group-sm">
            <a href="/mission/${m.id}" target="_blank" class="btn btn-outline-secondary" title="Переглянути">
              👁️
            </a>
            <button class="btn btn-outline-danger" onclick="deleteMission(${m.id})" title="Видалити">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `).join('');

  } catch (err) {
    console.error("Помилка завантаження місій:", err);
    tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger py-3">Мережева помилка при завантаженні.</td></tr>`;
  }
}

// 2. Видалення місії
async function deleteMission(missionId) {
  if (!confirm(`Ви дійсно бажаєте видалити місію #${missionId}? Цю дію неможливо скасувати!`)) {
    return;
  }

  try {
    const response = await fetch(`/api/admin/delete_mission/${missionId}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" }
    });

    const result = await response.json();

    if (result.success) {
      alert(`Місію #${missionId} успішно видалено!`);
      loadAdminMissions(); // Оновлюємо список
    } else {
      alert("Помилка видалення: " + (result.error || "Невідома помилка"));
    }
  } catch (err) {
    console.error(err);
    alert("Сталася помилка при відправці запиту.");
  }
}

// Допоміжна функція для захисту від XSS
function escapeHtml(text) {
  if (!text) return '';
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}