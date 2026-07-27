document.addEventListener("DOMContentLoaded", () => {
  // Автоматично додаємо перше питання при завантаженні
  addQuestion();

  document
    .getElementById("saveMissionBtn")
    .addEventListener("click", saveMission);
});

// --- РОБОТА З АБЗАЦАМИ ---
function addParagraph() {
  const container = document.getElementById("paragraphs-container");
  const count = container.querySelectorAll(".paragraph-row").length + 1;

  const paragraphDiv = document.createElement("div");
  paragraphDiv.className = "mb-3 position-relative paragraph-row";
  paragraphDiv.innerHTML = `
    <div class="d-flex align-items-start gap-2">
      <textarea class="form-control" rows="3" name="paragraph" placeholder="Абзац ${count}"></textarea>
      <button type="button" class="btn btn-outline-danger btn-sm" onclick="removeParagraph(this)" title="Видалити">
        &times;
      </button>
    </div>
  `;

  container.appendChild(paragraphDiv);
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

  // 1. Проста валідація
  const title = document.getElementById("missionTitle").value.trim();
  const subtitle = document.getElementById("missionSubTitle").value.trim();

  if (!title || !subtitle) {
    alert("Будь ласка, заповніть назву та підзаголовок місії.");
    return;
  }

  // 2. Збираємо абзаци
  const contentsArray = [];
  document.querySelectorAll("[name='paragraph']").forEach((textarea, index) => {
    const text = textarea.value.trim();
    if (text) {
      contentsArray.push({
        order: index + 1,
        text: text,
      });
    }
  });

  // 3. Збираємо питання
  const questionsArray = [];
  let validQuestions = true;

  document.querySelectorAll(".question-card").forEach((card, index) => {
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
        correct.push(optIndex); // Індекс правильної відповіді (0, 1, 2, 3)
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

  // 4. Формуємо FormData
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

  formData.append("contents", JSON.stringify(contentsArray));
  formData.append("questions", JSON.stringify(questionsArray));

  // 5. Відправка на сервер
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

// Додайте цю функцію у ваш admin.js
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