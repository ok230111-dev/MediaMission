import { auth } from "./firebase-config.js";
import { sendEmailVerification, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-auth.js";

onAuthStateChanged(auth, (user) => {
  if (user) {
    const displayName = user.displayName || "Користувач";
    const email = user.email || "";

    const nameElem = document.getElementById("profileName");
    const emailElem = document.getElementById("profileEmail");
    const avatarElem = document.getElementById("avatarPlaceholder");

    if (nameElem) nameElem.textContent = displayName;
    if (emailElem) emailElem.textContent = email;
    if (avatarElem) avatarElem.textContent = displayName.charAt(0).toUpperCase();

    // Дістаємо переклади з data-атрибутів на <section>
    const section = document.querySelector("section[data-t-level]");
    const tLevel = section?.dataset.tLevel || "Level";
    const tXpLeft = section?.dataset.tXpLeft || "";
    const tXpToNext = section?.dataset.tXpToNext || "";

    const xpTextElem = document.getElementById("totalXp");
    const currentXP = xpTextElem ? parseInt(xpTextElem.textContent.trim(), 10) || 0 : 0;

    const xpPerLevel = 500;
    const level = Math.floor(currentXP / xpPerLevel) + 1;
    const currentLevelXP = currentXP % xpPerLevel;
    const xpNeeded = xpPerLevel - currentLevelXP;
    const progressPercent = Math.min((currentLevelXP / xpPerLevel) * 100, 100);

    document.getElementById("currentLevel").textContent = `${tLevel} ${level}`;
    document.getElementById("xpText").textContent = `${currentLevelXP} / ${xpPerLevel} XP`;
    document.getElementById("xpNeeded").textContent = `${xpNeeded} XP`;

    // Оновлюємо текст навколо xpNeeded, якщо він теж має бути перекладений
    const xpNeededParent = document.getElementById("xpNeeded")?.parentElement;
    if (xpNeededParent && tXpLeft && tXpToNext) {
      xpNeededParent.innerHTML = `${tXpLeft} <strong id="xpNeeded">${xpNeeded} XP</strong> ${tXpToNext}`;
    }

    const progressBar = document.getElementById("xpProgressBar");
    if (progressBar) {
      progressBar.style.width = `${progressPercent}%`;
      progressBar.setAttribute("aria-valuenow", progressPercent);
    }

  } else {
    window.location.href = "/login";
  }
});

document.getElementById("verifyEmailBtn")?.addEventListener("click", async () => {
  const btn = document.getElementById("verifyEmailBtn");
  const statusEl = document.getElementById("verifyStatus");

  if (!auth.currentUser) {
    return;
  }

  btn.disabled = true;
  btn.textContent = "Sending..."

  try {
    await sendEmailVerification(auth.currentUser);
    statusEl.textContent = "Лист надіслано! Перевірте пошту (і папку «Спам»).";
    statusEl.className = "text-success small mt-2";
  } catch (error) {
    console.error(error);
    if (error.code === "auth/too-many-requests") {
      statusEl.textContent = "Забагато спроб. Спробуйте пізніше.";
    } else {
      statusEl.textContent = "Помилка надсилання листа.";
    }
    statusEl.className = "text-danger small mt-2";
  } finally {
    btn.disabled = false;
    btn.textContent = "Надіслати лист підтвердження";
  }

  // у profile.js, після завантаження сторінки
setInterval(async () => {
  if (auth.currentUser) {
    await auth.currentUser.reload();
    if (auth.currentUser.emailVerified) {
      const verifyBtn = document.getElementById("verifyEmailBtn");
      if (verifyBtn) {
        // Синхронізуємо з бекендом і перезавантажуємо, щоб Jinja показав badge замість кнопки
        await fetch("/api/update_verification_status", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ uid: auth.currentUser.uid, email_verified: true })
        });
        window.location.reload();
      }
    }
  }
}, 5000); // перевірка кожні 5 секунд, поки кнопка видима
});

// у profile.js, після завантаження сторінки
setInterval(async () => {
  if (auth.currentUser) {
    await auth.currentUser.reload();
    if (auth.currentUser.emailVerified) {
      const verifyBtn = document.getElementById("verifyEmailBtn");
      if (verifyBtn) {
        // Синхронізуємо з бекендом і перезавантажуємо, щоб Jinja показав badge замість кнопки
        await fetch("/api/update_verification_status", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ uid: auth.currentUser.uid, email_verified: true })
        });
        window.location.reload();
      }
    }
  }
}, 5000); // перевірка кожні 5 секунд, поки кнопка