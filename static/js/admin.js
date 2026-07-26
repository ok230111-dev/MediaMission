let paragraphCount = 1;
let questionCount = 3;

function addParagraph() {
  paragraphCount++;
  const container = document.getElementById('paragraphs-container');

  const paragraphDiv = document.createElement('div');
  paragraphDiv.className = 'mb-3 position-relative';
  paragraphDiv.innerHTML = `
    <div class="d-flex align-items-center gap-2 mb-2">
      <textarea class="form-control" rows="4" name="paragraph" placeholder="Абзац ${paragraphCount}"></textarea>
      <button type="button" class="btn btn-outline-danger btn-sm" onclick="this.parentElement.parentElement.remove()" title="Видалити абзац">
        &times;
      </button>
    </div>
  `;

  container.appendChild(paragraphDiv);
}

function addQuestion() {
  questionCount++;
  const container = document.getElementById('questions-container');

  const questionCard = document.createElement('div');
  questionCard.className = 'card shadow-sm mb-4 question-card';  // ← додано клас
  questionCard.innerHTML = `
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h3 class="m-0">Питання ${questionCount}</h3>
        <button type="button" class="btn btn-outline-danger btn-sm" onclick="this.closest('.card').remove()">
          Видалити питання
        </button>
      </div>

      <input
        class="form-control mb-3 question-text"
        placeholder="Текст питання"
        name="question${questionCount}"
        required
      />

      <select class="form-select mb-3 question-type" name="question${questionCount}_type">
        <option value="single_choice">Одна відповідь</option>
        <option value="multiple_choice">Кілька відповідей</option>
      </select>

      <label class="form-label fw-bold mb-2">Варіанти відповідей (позначте правильні):</label>

      ${[1, 2, 3, 4].map(i => `
        <div class="input-group mb-2">
          <div class="input-group-text">
            <input
              class="form-check-input mt-0 correct"
              type="checkbox"
              name="q${questionCount}_correct"
              value="${i}"
              title="Позначити як правильну"
            />
          </div>
          <input
            type="text"
            class="form-control option"
            placeholder="Варіант ${i}"
            name="q${questionCount}_option${i}"
          />
        </div>
      `).join('')}
    </div>
  `;

  container.appendChild(questionCard);
}

document
    .getElementById("saveMissionBtn")
    .addEventListener("click", saveMission);

async function saveMission() {
  // 1. Збираємо абзаци
  const contentsArray = [];
  document.querySelectorAll("[name='paragraph']").forEach((textarea, index) => {
    contentsArray.push({
      order: index + 1,
      text: textarea.value
    });
  });

  // 2. Збираємо питання
  const questionsArray = [];
  document.querySelectorAll(".question-card").forEach((card) => {
    const question = {};

    question.question = card.querySelector(".question-text").value;
    question.type = card.querySelector(".question-type").value;
    question.options = [];

    card.querySelectorAll(".option").forEach((input) => {
      question.options.push(input.value);
    });

    const correct = [];
    card.querySelectorAll(".correct").forEach((checkbox) => {
      if (checkbox.checked) {
        correct.push(Number(checkbox.value) - 1);
      }
    });
    question.correct_answer = correct;

    questionsArray.push(question);
  });

  // 3. Збираємо все у FormData (потрібно для файлу зображення)
  const formData = new FormData();

  formData.append("title", document.getElementById("missionTitle").value);
  formData.append("subtitle", document.getElementById("missionSubTitle").value);
  formData.append("exercise", document.getElementById("missionExercise").value);
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

  // 4. Один, єдиний запит
  const response = await fetch("/api/admin/add_mission", {
    method: "POST",
    body: formData
    // Content-Type НЕ вказуємо вручну — браузер сам додасть multipart/form-data з boundary
  });

  const result = await response.json();

  if (result.success) {
    alert("Місія успішно створена!");
  } else {
    alert("Помилка: " + (result.error || "невідома"));
  }
}