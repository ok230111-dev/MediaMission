import { auth } from "./firebase-config.js";
import { onAuthStateChanged } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-auth.js";

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