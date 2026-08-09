document.addEventListener("DOMContentLoaded", () => {
  let currentStep = 1;
  let selectedPage = null;
  let selectedPageLabel = "";
  let selectedCategory = null;
  let selectedCategoryLabel = "";

  const steps = document.querySelectorAll(".wizard-step");
  const panels = document.querySelectorAll(".wizard-panel");
  const backBtn = document.getElementById("ideaBackBtn");
  const submitBtn = document.getElementById("ideaSubmitBtn");

  const pageButtons = document.querySelectorAll(".page-btn");
  const categoryButtons = document.querySelectorAll(".category-btn");

  const titleInput = document.getElementById("ideaTitleInput");
  const descInput = document.getElementById("ideaDescriptionInput");
  const charCount = document.getElementById("ideaCharCount");
  const summaryBox = document.getElementById("ideaSummary");

  function goToStep(step) {
    currentStep = step;

    panels.forEach((p) => {
      p.classList.toggle("d-none", Number(p.dataset.panel) !== step);
    });

    steps.forEach((s) => {
      const n = Number(s.dataset.step);
      s.classList.remove("active", "done");
      if (n === step) s.classList.add("active");
      else if (n < step) s.classList.add("done");
    });

    backBtn.disabled = step === 1;
    submitBtn.classList.toggle("d-none", step !== 3);

    if (step === 3) {
      summaryBox.innerHTML = `
        <strong>${window.ideaTranslations.summaryPage}:</strong> ${selectedPageLabel}<br>
        <strong>${window.ideaTranslations.summaryCategory}:</strong> ${selectedCategoryLabel}
      `;
    }
  }

  pageButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      pageButtons.forEach((b) => b.classList.remove("selected"));
      btn.classList.add("selected");
      selectedPage = btn.dataset.page;
      selectedPageLabel = btn.dataset.label;
      setTimeout(() => goToStep(2), 200);
    });
  });

  categoryButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      categoryButtons.forEach((b) => b.classList.remove("selected"));
      btn.classList.add("selected");
      selectedCategory = btn.dataset.category;
      selectedCategoryLabel = btn.dataset.label;
      setTimeout(() => goToStep(3), 200);
    });
  });

  backBtn.addEventListener("click", () => {
    if (currentStep > 1) goToStep(currentStep - 1);
  });

  descInput.addEventListener("input", () => {
    charCount.textContent = descInput.value.length;
  });

  titleInput.addEventListener("input", () => {
    titleInput.classList.remove("is-invalid");
  });

  descInput.addEventListener("input", () => {
    descInput.classList.remove("is-invalid");
  });

  submitBtn.addEventListener("click", async () => {
    if (!titleInput.value.trim() || !descInput.value.trim()) {
      titleInput.classList.toggle("is-invalid", !titleInput.value.trim());
      descInput.classList.toggle("is-invalid", !descInput.value.trim());
      return;
    }

    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${window.ideaTranslations.sending}`;

    try {
      const formData = new FormData();
      formData.append("page", selectedPage);
      formData.append("page_label", selectedPageLabel);
      formData.append("category", selectedCategory);
      formData.append("category_label", selectedCategoryLabel);
      formData.append("title", titleInput.value.trim());
      formData.append("description", descInput.value.trim());

      const fileInput = document.getElementById("ideaAttachmentInput");
      if (fileInput.files[0]) {
        formData.append("attachment", fileInput.files[0]);
      }

      const response = await fetch("/api/ideas", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Submit failed");

      goToStep(4);
    } catch (err) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<i class="bi bi-send-fill me-1"></i>${window.ideaTranslations.submit}`;
      alert(window.ideaTranslations.error);
    }
  });
});