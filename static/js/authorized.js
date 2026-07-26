import { auth } from "./firebase-config.js";
import { onAuthStateChanged, signOut } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-auth.js";

const ADMIN_EMAIL = "admin.230111@gmail.com";

onAuthStateChanged(auth, async (user) => {
  const heroTitle = document.querySelector(".hero h1");
  const navbarNav = document.getElementById("navbarNav");
  const body = document.body;

  // Дістаємо переклади з data-атрибутів на <body>
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

  if (user) {
    const isAdmin = user.email === ADMIN_EMAIL;

    navbarNav.innerHTML = `
      <ul class="navbar-nav ms-auto align-items-lg-center gap-lg-3 mt-3 mt-lg-0">
        ${isAdmin ? `<li class="nav-item"><a class="nav-link" href="/admin">${t.adminPanel}</a></li>` : ''}
        <li class="nav-item"><a class="nav-link" href="/profile">${t.profile}</a></li>
        <li class="nav-item"><a class="nav-link" href="/">${t.home}</a></li>
        <li class="nav-item"><a class="nav-link" href="/missions-overview">${t.missions}</a></li>
        <li class="nav-item"><a class="nav-link" href="#" id="logoutBtn">${t.logout}</a></li>
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
      <ul class="navbar-nav ms-auto align-items-lg-center gap-lg-3 mt-3 mt-lg-0">
        <li class="nav-item"><a class="nav-link" href="/">${t.home}</a></li>
        <li class="nav-item"><a class="nav-link" href="/missions-overview">${t.missions}</a></li>
        <li class="nav-item"><a class="nav-link" href="/register">${t.register}</a></li>
        <li class="nav-item"><a class="nav-link" href="/login">${t.login}</a></li>
      </ul>
    `;
  }

  if (user) {
  // Перевіряємо актуальний статус верифікації і синхронізуємо з бекендом
  await user.reload();  // підтягує свіжі дані з Firebase (важливо, бо user.emailVerified міг застаріти)

  if (user.emailVerified) {
    fetch("/api/update_verification_status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ uid: user.uid, email_verified: true })
    });
  }
  }
});