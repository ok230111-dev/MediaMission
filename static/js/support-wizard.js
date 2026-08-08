const body = document.body;

const ISSUE_TYPES = {
  bug: ["wont_open", "freezes", "button_not_working", "other"],
  account: ["cant_login", "cant_register", "wrong_data", "other"],
  mission: ["xp_not_credited", "wont_open", "wrong_answer_check", "button_not_working", "other"],
  translation: ["missing_translation", "wrong_translation", "other"],
  avatar: ["upload_failed", "not_showing", "other"],
  notifications: ["not_receiving", "wrong_language", "other"],
  leaderboard: ["wrong_position", "not_updating", "other"],
  ai_assistant: ["ai_wrong_answer", "ai_not_responding", "ai_rate_limited", "ai_gives_test_answers", "other"],
  other: ["other"]
};

const ISSUE_LABELS = {
  wont_open: body.dataset.tIssueWontOpen,
  freezes: body.dataset.tIssueFreezes,
  button_not_working: body.dataset.tIssueButtonNotWorking,
  cant_login: body.dataset.tIssueCantLogin,
  cant_register: body.dataset.tIssueCantRegister,
  wrong_data: body.dataset.tIssueWrongData,
  xp_not_credited: body.dataset.tIssueXpNotCredited,
  wrong_answer_check: body.dataset.tIssueWrongAnswerCheck,
  missing_translation: body.dataset.tIssueMissingTranslation,
  wrong_translation: body.dataset.tIssueWrongTranslation,
  upload_failed: body.dataset.tIssueUploadFailed,
  not_showing: body.dataset.tIssueNotShowing,
  not_receiving: body.dataset.tIssueNotReceiving,
  wrong_language: body.dataset.tIssueWrongLanguage,
  wrong_position: body.dataset.tIssueWrongPosition,
  not_updating: body.dataset.tIssueNotUpdating,
  ai_wrong_answer: body.dataset.tIssueAiWrongAnswer,
  ai_not_responding: body.dataset.tIssueAiNotResponding,
  ai_rate_limited: body.dataset.tIssueAiRateLimited,
  ai_gives_test_answers: body.dataset.tIssueAiGivesTestAnswers,
  other: body.dataset.tIssueOther
};

let state = {
  step: 1,
  category: null,
  categoryLabel: null,
  missionId: null,
  missionTitle: null,
  issueType: null,
  issueTypeLabel: null,
};

const panels = document.querySelectorAll(".wizard-panel");
const steps = document.querySelectorAll(".wizard-step");
const backBtn = document.getElementById("backBtn");
const submitBtn = document.getElementById("submitBtn");

function goToStep(n) {
  state.step = n;
  panels.forEach(p => p.classList.toggle("d-none", p.dataset.panel != n));
  steps.forEach(s => {
    const stepNum = parseInt(s.dataset.step);
    s.classList.toggle("active", stepNum === n);
    s.classList.toggle("done", stepNum < n);
  });
  backBtn.disabled = n === 1;
  submitBtn.classList.toggle("d-none", n !== 3);
  document.getElementById("wizardNav").classList.toggle("d-none", n === 4);

  if (n === 3) buildSummary();
}

// --- Крок 1: вибір категорії ---
document.querySelectorAll(".category-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".category-btn").forEach(b => b.classList.remove("selected"));
    btn.classList.add("selected");
    state.category = btn.dataset.category;
    state.categoryLabel = btn.dataset.label;

    buildIssueTypeOptions();
    document.getElementById("missionSelectBlock").classList.toggle("d-none", state.category !== "mission");

    setTimeout(() => goToStep(2), 200);
  });
});

// --- Крок 2: побудова опцій типу проблеми ---
function buildIssueTypeOptions() {
  const container = document.getElementById("issueTypeOptions");
  container.innerHTML = "";
  const types = ISSUE_TYPES[state.category] || ["other"];

  types.forEach(type => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-outline-primary text-start issue-type-btn";
    btn.dataset.type = type;
    btn.textContent = ISSUE_LABELS[type] || type;
    btn.addEventListener("click", () => {
      document.querySelectorAll(".issue-type-btn").forEach(b => b.classList.remove("selected"));
      btn.classList.add("selected");
      state.issueType = type;
      state.issueTypeLabel = ISSUE_LABELS[type] || type;
      setTimeout(() => goToStep(3), 200);
    });
    container.appendChild(btn);
  });
}

document.getElementById("missionSelect").addEventListener("change", (e) => {
  state.missionId = e.target.value || null;
  const selected = e.target.options[e.target.selectedIndex];
  state.missionTitle = e.target.value ? selected.textContent : null;
});

// --- Крок 3: підсумок ---
function buildSummary() {
  const categoryLabel = body.dataset.tSupportCategoryLabel || "Category";
  const missionLabel = body.dataset.tSupportMissionLabel || "Mission";
  const typeLabel = body.dataset.tSupportTypeLabel || "Type";

  const lines = [`<strong>${categoryLabel}:</strong> ${state.categoryLabel}`];
  if (state.missionTitle) lines.push(`<strong>${missionLabel}:</strong> ${state.missionTitle}`);
  if (state.issueTypeLabel) lines.push(`<strong>${typeLabel}:</strong> ${state.issueTypeLabel}`);
  document.getElementById("ticketSummary").innerHTML = lines.join("<br>");
}

// --- Кнопка "Назад" ---
backBtn.addEventListener("click", () => {
  if (state.step > 1) goToStep(state.step - 1);
});

// --- Збір технічної інформації ---
function collectBrowserInfo() {
  return {
    browser: navigator.userAgent,
    language: document.documentElement.getAttribute("lang") || navigator.language,
    theme: document.documentElement.getAttribute("data-theme") || "light",
    screen: `${window.screen.width}x${window.screen.height}`,
    url: window.location.href,
    timestamp: new Date().toISOString()
  };
}

// --- Відправка ---
submitBtn.addEventListener("click", async () => {
  const sendingText = body.dataset.tSupportSending || "Sending...";
  const submitErrorText = body.dataset.tSupportSubmitError || "Failed to submit ticket";
  const networkErrorText = body.dataset.tSupportNetworkError || "Network error";
  const originalBtnHtml = submitBtn.innerHTML;

  submitBtn.disabled = true;
  submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${sendingText}`;

  const formData = new FormData();
  formData.append("category", state.category);
  formData.append("category_label", state.categoryLabel || "");
  if (state.missionId) formData.append("mission_id", state.missionId);
  formData.append("issue_type", state.issueType || "");
  formData.append("issue_type_label", state.issueTypeLabel || "");
  formData.append("description", document.getElementById("descriptionInput").value.trim());
  formData.append("browser_info", JSON.stringify(collectBrowserInfo()));

  const screenshotFile = document.getElementById("screenshotInput").files[0];
  if (screenshotFile) formData.append("screenshot", screenshotFile);

  try {
    const response = await fetch("/api/support/submit_ticket", {
      method: "POST",
      body: formData
    });
    const data = await response.json();

    if (data.success) {
      document.getElementById("ticketIdDisplay").textContent = `#${data.ticket_id}`;
      goToStep(4);
    } else {
      alert(data.error || submitErrorText);
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalBtnHtml;
    }
  } catch (err) {
    console.error(err);
    alert(networkErrorText);
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalBtnHtml;
  }
});