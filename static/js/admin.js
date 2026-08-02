document.addEventListener("DOMContentLoaded", () => {
  // --- ОБРОБНИК ЗМІНИ ТИПУ АБЗАЦУ (ФРАГМЕНТ) ---
  document.addEventListener("change", (e) => {
    if (e.target.classList.contains("paragraph-type")) {
      const row = e.target.closest(".paragraph-row");
      const fileInput = row.querySelector(".paragraph-file");
      const urlInput = row.querySelector(".paragraph-url");

      fileInput.classList.add("d-none");
      urlInput.classList.add("d-none");

      if (e.target.value === "image" || e.target.value === "video") {
        fileInput.classList.remove("d-none");
      } else if (e.target.value === "website") {
        urlInput.classList.remove("d-none");
      }
    }
  });

  // Автоматично додаємо перше питання при завантаженні
  addQuestion();

  const saveBtn = document.getElementById("saveMissionBtn");
  if (saveBtn) {
    saveBtn.addEventListener("click", saveMission);
  }
});

// --- РОБОТА З АБЗАЦАМИ ---
function addParagraph() {
  const container = document.getElementById("paragraphs-container");

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
  btn.closest(".paragraph-row").remove();
  reindexParagraphs();
}

function reindexParagraphs() {
  document.querySelectorAll("#paragraphs-container .paragraph-row").forEach((row, index) => {
    const textarea = row.querySelector("textarea");
    textarea.placeholder = `Абзац ${index + 1}`;
  });
}

// --- РОБОТА З ПИТАННЯМИ ---
function addQuestion() {
  const container = document.getElementById("questions-container");
  const qIndex = Date.now(); // Унікальний ID для групування radio/checkbox

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
  btn.closest(".question-card").remove();
  reindexQuestions();
}

function reindexQuestions() {
  document.querySelectorAll(".question-card").forEach((card, index) => {
    card.querySelector(".question-title").textContent = `Питання ${index + 1}`;
  });
}

// Перемикач типом між Radio (одна) та Checkbox (кілька)
function toggleOptionInputType(selectElem, qIndex) {
  const card = selectElem.closest(".question-card");
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

  const title = document.getElementById("missionTitle").value.trim();
  const subtitle = document.getElementById("missionSubTitle").value.trim();

  if (!title || !subtitle) {
    alert("Будь ласка, заповніть назву та підзаголовок місії.");
    return;
  }

  const contentsArray = [];
  const filesToUpload = [];

  document.querySelectorAll('.paragraph-row').forEach((row, index) => {
    const type = row.querySelector('.paragraph-type').value;
    const textInput = row.querySelector('.paragraph-text').value;
    const fileInput = row.querySelector('.paragraph-file');
    const urlInput = row.querySelector('.paragraph-url');

    if (type === 'website') {
      contentsArray.push({
        order: index + 1,
        text: `[WEBSITE]${urlInput.value}${textInput ? '\n' + textInput : ''}`
      });
    } else if ((type === 'image' || type === 'video') && fileInput.files[0]) {
      const marker = type === 'image' ? '[IMAGE]' : '[VIDEO]';
      filesToUpload.push({ key: `content_file_${index + 1}`, file: fileInput.files[0] });
      contentsArray.push({
        order: index + 1,
        text: `${marker}PENDING_UPLOAD_${index + 1}${textInput ? '\n' + textInput : ''}`
      });
    } else {
      contentsArray.push({ order: index + 1, text: textInput });
    }
  });

  const questionsArray = [];
  let validQuestions = true;

  document.querySelectorAll(".question-card").forEach((card) => {
    const qText = card.querySelector(".question-text").value.trim();
    const qType = card.querySelector(".question-type").value;

    if (!qText) {
      validQuestions = false;
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
      type: qType,
      options: options,
      correct_answer: correct,
    });
  });

  if (!validQuestions || questionsArray.length === 0) {
    alert("Будь ласка, заповніть текст для всіх питань.");
    return;
  }

  const formData = new FormData();
  formData.append("title", title);
  formData.append("subtitle", subtitle);
  formData.append("exercise", document.getElementById("missionExercise").value.trim());
  formData.append("type", document.getElementById("missionType").value);
  formData.append("difficulty", document.getElementById("missionDifficulty").value);
  formData.append("xp", document.getElementById("missionXP").value);
  formData.append("time", document.getElementById("missionTime").value);

  const imageInput = document.getElementById("image");
  if (imageInput && imageInput.files[0]) {
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