import { auth } from "./firebase-config.js";
import { onAuthStateChanged, signOut } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-auth.js";

const ADMIN_EMAIL = "admin.230111@gmail.com";

onAuthStateChanged(auth, async (user) => {
  const heroTitle = document.querySelector(".hero h1");
  const navbarNav = document.getElementById("navbarNav");
  const body = document.body;

  // Дістаємо переклади та поточну мову з data-атрибутів <body>
  const t = {
    hello: body.dataset.tHello,
    learnCritical: body.dataset.tLearnCritical,
    learn: body.dataset.tLearn,
    critical: body.dataset.tCritical,
    adminPanel: body.dataset.tAdminPanel,
    profile: body.dataset.tProfile,
    home: body.dataset.tHome,
    missions: body.dataset.tMissions,
    logout: body.dataset.tLogout,
    register: body.dataset.tRegister,
    login: body.dataset.tLogin,
    leaderboard: body.dataset.tLeaderboard,
    about: body.dataset.tAbout,
    lang: body.dataset.tLang ? body.dataset.tLang.toLowerCase() : 'uk', // поточна мова (uk, de, en)
    notifications: body.dataset.tNotifications,
    theme: body.dataset.tTheme || "Тема"
  };

  // 1. Оновлюємо заголовок ЛИШЕ якщо він є на цій сторінці
  if (heroTitle) {
    if (user) {
      const name = user.displayName || "Користувач";
      heroTitle.innerHTML = `
        ${t.hello}, ${name} 👋<br>
        <span class="fs-4 d-block mt-2">${t.learnCritical}</span>
      `;
    } else {
      heroTitle.innerHTML = `
        ${t.learn}<br>
        <span>${t.critical}</span>
      `;
    }
  }

  // 2. Оновлюємо navbar ОДИН РАЗ, незалежно від наявності heroTitle
  if (!navbarNav) {
    return;
  }

  // Шаблон перемикача мови для JavaScript
  const languageSwitcherHTML = `
    <li class="nav-item dropdown language-dropdown lang-switcher-inner pt-2 mt-2 border-top">
      <a
        class="nav-link dropdown-toggle d-flex align-items-center gap-2"
        href="#"
        role="button"
        id="languageDropdownBtnInner"
        data-bs-toggle="dropdown"
        aria-expanded="false"
      >
        <i class="bi bi-globe2"></i>
        <span><strong>${t.lang.toUpperCase()}</strong></span>
      </a>

      <ul class="dropdown-menu language-dropdown-menu" aria-labelledby="languageDropdownBtnInner">
        <li>
          <a class="dropdown-item ${t.lang === 'uk' ? 'active' : ''}" href="/set_language/uk">Українська</a>
        </li>
        <li>
          <a class="dropdown-item ${t.lang === 'de' ? 'active' : ''}" href="/set_language/de">Deutsch</a>
        </li>
        <li>
          <a class="dropdown-item ${t.lang === 'en' ? 'active' : ''}" href="/set_language/en">English</a>
        </li>
      </ul>
    </li>
  `;

  const unreadTotal = parseInt(document.body.dataset.unreadTotal || "0", 10);
  const notificationBadgeHTML = unreadTotal > 0
    ? `<span class="badge bg-danger rounded-pill ms-1">${unreadTotal < 10 ? unreadTotal : '9+'}</span>`
    : '';

  // Шаблон теми для вирівнювання з іншими пунктами
  const themeToggleHTML = `
    <li class="nav-item">
      <button id="themeToggleBtn" class="nav-link btn btn-link text-start d-flex align-items-center gap-2 w-100 px-0 border-0">
        <i id="themeIcon" class="bi bi-moon-stars-fill"></i>
        <span>${t.theme}</span>
      </button>
    </li>
  `;

  if (user) {
    const isAdmin = user.email === ADMIN_EMAIL;

    navbarNav.innerHTML = `
      <ul class="navbar-nav ms-auto align-items-lg-center gap-lg-4">
        ${isAdmin ? `
          <li class="nav-item">
            <a class="nav-link" href="/admin">
              <i class="bi bi-shield-lock-fill"></i>
              ${t.adminPanel}
            </a>
          </li>` : ''}

        ${languageSwitcherHTML}

        <li class="nav-item">
          <a class="nav-link d-flex align-items-center gap-2" href="/profile">
            <i class="bi bi-person-circle"></i>
            ${t.profile}
          </a>
        </li>

        <li class="nav-item">
          <a class="nav-link d-flex align-items-center gap-2" href="/leaderboard">
            <i class="bi bi-trophy-fill"></i>
            ${t.leaderboard}
          </a>
        </li>

        <li class="nav-item">
          <a class="nav-link d-flex align-items-center gap-2" href="/missions-overview">
            <i class="bi bi-journal-check"></i>
            ${t.missions}
          </a>
        </li>

        <li class="nav-item">
          <a class="nav-link d-flex align-items-center gap-2" href="/about">
            <i class="bi bi-info-circle me-1"></i>
            ${t.about}
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link d-flex align-items-center gap-2 burger-menu-bell" href="/notifications">
            <i class="bi bi-bell-fill fs-5"></i>
            ${t.notifications}
            ${notificationBadgeHTML}
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link d-flex align-items-center gap-2" href="#" id="logoutBtn">
            <i class="bi bi-box-arrow-right"></i>
            ${t.logout}
          </a>
        </li>
      </ul>
    `;

    document.getElementById("logoutBtn")?.addEventListener("click", async (e) => {
      e.preventDefault();
      await signOut(auth);
      await fetch("/logout", { method: "POST" });
      window.location.href = "/";
    });
  } else {
    navbarNav.innerHTML = `
      <ul class="navbar-nav ms-auto align-items-lg-center gap-lg-4">
        ${languageSwitcherHTML}

        <li class="nav-item">
          <a class="nav-link d-flex align-items-center gap-2" href="/">
            <i class="bi bi-house-door"></i>
            ${t.home}
          </a>
        </li>

        <li class="nav-item">
          <a class="nav-link d-flex align-items-center gap-2" href="/leaderboard">
            <i class="bi bi-trophy-fill"></i>
            ${t.leaderboard}
          </a>
        </li>

        <li class="nav-item">
          <a class="nav-link d-flex align-items-center gap-2" href="/missions-overview">
            <i class="bi bi-journal-check"></i>
            ${t.missions}
          </a>
        </li>

        <li class="nav-item">
          <a class="nav-link d-flex align-items-center gap-2" href="/about">
            <i class="bi bi-info-circle me-1"></i>
            ${t.about}
          </a>
        </li>
        
        <li class="nav-item">
          <a class="nav-link d-flex align-items-center gap-2" href="/register">
            <i class="bi bi-person-plus"></i>
            ${t.register}
          </a>
        </li>

        <li class="nav-item">
          <a class="nav-link d-flex align-items-center gap-2" href="/login">
            <i class="bi bi-box-arrow-in-right"></i>
            ${t.login}
          </a>
        </li>
      </ul>
    `;
  }

  // Ініціалізація логіки перемикання теми
  initThemeToggle();

  // Перевіряємо актуальний статус верифікації
  if (user) {
    await user.reload();
    if (user.emailVerified) {
      fetch("/api/update_verification_status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ uid: user.uid, email_verified: true })
      });
    }
  }
});

// Допоміжна функція для управління темою та іконкою (сонце / місяць)
function initThemeToggle() {
  const themeToggleBtn = document.getElementById("themeToggleBtn");
  const themeIcon = document.getElementById("themeIcon");
  const htmlElement = document.documentElement;

  if (!themeToggleBtn || !themeIcon) return;

  function updateThemeUI(theme) {
    if (theme === "dark") {
      themeIcon.className = "bi bi-sun-fill";
    } else {
      themeIcon.className = "bi bi-moon-stars-fill";
    }
  }

  const currentTheme = localStorage.getItem("theme") || "light";
  htmlElement.setAttribute("data-bs-theme", currentTheme);
  updateThemeUI(currentTheme);

  themeToggleBtn.addEventListener("click", () => {
    const activeTheme = htmlElement.getAttribute("data-bs-theme");
    const newTheme = activeTheme === "dark" ? "light" : "dark";

    htmlElement.setAttribute("data-bs-theme", newTheme);
    localStorage.setItem("theme", newTheme);
    updateThemeUI(newTheme);
  });
}