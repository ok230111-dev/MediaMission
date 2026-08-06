import { auth } from "./firebase-config.js";
import { onAuthStateChanged } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-auth.js";

// ============================================
// ОБРОБКА СТАНУ АВТОРИЗАЦІЇ
// ============================================
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

    // Оновлюємо XP та рівень
    updateXPProgress();

  } else {
    window.location.href = "/login";
  }
});

// ============================================
// ОНОВЛЕННЯ XP ТА РІВНЯ
// ============================================
function updateXPProgress() {
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

    const currentLevelEl = document.getElementById("currentLevel");
    const xpTextEl = document.getElementById("xpText");
    const xpNeededEl = document.getElementById("xpNeeded");
    const progressBar = document.getElementById("xpProgressBar");

    if (currentLevelEl) currentLevelEl.textContent = `${tLevel} ${level}`;
    if (xpTextEl) xpTextEl.textContent = `${currentLevelXP} / ${xpPerLevel} XP`;
    if (xpNeededEl) xpNeededEl.textContent = `${xpNeeded} XP`;

    // Оновлюємо текст навколо xpNeeded
    const xpNeededParent = xpNeededEl?.parentElement;
    if (xpNeededParent && tXpLeft && tXpToNext) {
      xpNeededParent.innerHTML = `${tXpLeft} <strong id="xpNeeded">${xpNeeded} XP</strong> ${tXpToNext}`;
    }

    if (progressBar) {
      progressBar.style.width = `${progressPercent}%`;
      progressBar.setAttribute("aria-valuenow", progressPercent);
    }
}

// ============================================
// ВЕРИФІКАЦІЯ EMAIL ЧЕРЕЗ FLASK (CUSTOM)
// ============================================
document.getElementById("verifyEmailBtn")?.addEventListener("click", async () => {
  const btn = document.getElementById("verifyEmailBtn");
  const statusEl = document.getElementById("verifyStatus");

  if (!auth.currentUser || !auth.currentUser.email) {
    if (statusEl) {
      statusEl.textContent = "Користувач не авторизований або email відсутній.";
      statusEl.className = "text-danger small mt-2";
    }
    return;
  }

  btn.disabled = true;
  btn.textContent = "Надсилання...";

  try {
    // Надсилаємо запит на кастомний Flask API ендпоінт
    const response = await fetch('/api/auth/custom_verify_email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: auth.currentUser.email })
    });

    const result = await response.json();

    if (result.success) {
      if (statusEl) {
        statusEl.textContent = "Лист надіслано! Перевірте пошту.";
        statusEl.className = "alert alert-success small mt-2"; // Стандартні класи Bootstrap
      }
    } else {
      if (statusEl) {
        statusEl.textContent = "Помилка: " + (result.error || "Не вдалося надіслати лист.");
        statusEl.className = "alert alert-danger small mt-2";
      }
    }
  } catch (error) {
    console.error("Помилка при відправці запиту на верифікацію:", error);
    if (statusEl) {
      statusEl.textContent = "Помилка з'єднання з сервером.";
      statusEl.className = "alert alert-danger small mt-2";
    }
  } finally {
    btn.disabled = false;
    btn.textContent = "Надіслати лист підтвердження";
  }
});

// ============================================
// ПЕРЕВІРКА СТАТУСУ ВЕРИФІКАЦІЇ (ОДИН РАЗ / ІНТЕРВАЛ)
// ============================================
setInterval(async () => {
  if (auth.currentUser) {
    await auth.currentUser.reload();
    if (auth.currentUser.emailVerified) {
      const verifyBtn = document.getElementById("verifyEmailBtn");
      if (verifyBtn) {
        // Синхронізуємо з бекендом
        await fetch("/api/update_verification_status", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            uid: auth.currentUser.uid, 
            email_verified: true 
          })
        });
        window.location.reload();
      }
    }
  }
}, 5000); // перевірка кожні 5 секунд

// ============================================
// TOGGLE ДОДАТКОВОЇ СТАТИСТИКИ
// ============================================
function toggleStatsSmooth() {
    const statsContainer = document.querySelector('.other-stats');
    const toggleIcon = document.getElementById('toggleIcon');
    const toggleBtn = document.getElementById('toggleStatsBtn');
    const section = document.querySelector("section[data-t-level]");
    const tClickMore = section?.dataset.tClickMore || "Натисніть щоб показати більше";
    const tClickLess = section?.dataset.tClickLess || "Натисність щоб сховати";

    if (!statsContainer) return;

    if (statsContainer.classList.contains('show')) {
        statsContainer.style.transition = 'all 0.3s ease';
        statsContainer.style.opacity = '0';
        statsContainer.style.transform = 'translateY(-10px)';

        setTimeout(() => {
            statsContainer.classList.remove('show');
            statsContainer.style.display = 'none';
            if (toggleIcon) toggleIcon.textContent = '...';
            if (toggleBtn) {
                const label = toggleBtn.querySelector('.text-muted.small');
                if (label) label.textContent = tClickMore;
            }
        }, 300);
    } else {
        statsContainer.style.display = 'flex';
        statsContainer.style.opacity = '0';
        statsContainer.style.transform = 'translateY(-10px)';

        setTimeout(() => {
            statsContainer.classList.add('show');
            statsContainer.style.transition = 'all 0.3s ease';
            statsContainer.style.opacity = '1';
            statsContainer.style.transform = 'translateY(0)';
            if (toggleIcon) toggleIcon.textContent = '▼';
            if (toggleBtn) {
                const label = toggleBtn.querySelector('.text-muted.small');
                if (label) label.textContent = tClickLess;
            }
        }, 50);
    }
}

// ============================================
// ПРИВ'ЯЗКА КНОПКИ ДО ФУНКЦІЇ (після завантаження DOM)
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    const toggleBtn = document.getElementById('toggleStatsBtn');
    
    if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleStatsSmooth);
    }
    
    // Відновлюємо стан при завантаженні
    const savedState = localStorage.getItem('showExtraStats');
    const statsContainer = document.querySelector('.other-stats');
    const toggleIcon = document.getElementById('toggleIcon');
    const toggleBtn2 = document.getElementById('toggleStatsBtn');
    
    if (savedState === 'true' && statsContainer) {
        statsContainer.style.display = 'flex';
        setTimeout(() => {
            statsContainer.classList.add('show');
            statsContainer.style.opacity = '1';
            statsContainer.style.transform = 'translateY(0)';
            if (toggleIcon) toggleIcon.textContent = '▼';
            if (toggleBtn2) {
                const label = toggleBtn2.querySelector('.text-muted.small');
                if (label) label.textContent = 'Натисніть щоб сховати';
            }
        }, 100);
    }
});



const body = document.body;

const STATUS_CONFIG = {
  open:     { emoji: "🟡", label: body.dataset.tStatusOpen || "Open",         class: "bg-warning-subtle text-warning-emphasis" },
  answered: { emoji: "🔵", label: body.dataset.tStatusAnswered || "Answered", class: "bg-info-subtle text-info-emphasis" },
  solved:   { emoji: "🟢", label: body.dataset.tStatusSolved || "Solved",     class: "bg-success-subtle text-success-emphasis" },
  closed:   { emoji: "🔴", label: body.dataset.tStatusClosed || "Closed",     class: "bg-danger-subtle text-danger-emphasis" }
};

async function loadMyTickets() {
  const container = document.getElementById("myTicketsList");
  if (!container) return;

  const noTicketsText = body.dataset.tSupportNoTickets || "No tickets yet";
  const loadErrorText = body.dataset.tSupportLoadError || "Failed to load";
  const replyLabel = body.dataset.tSupportReplyLabel || "Reply";
  const missionLabel = body.dataset.tSupportMissionLabel || "Mission";

  try {
    const response = await fetch("/api/my_support_tickets");
    const data = await response.json();

    if (!data.success || data.tickets.length === 0) {
      container.innerHTML = `<div class="text-center text-muted py-3 small">${noTicketsText}</div>`;
      return;
    }

    container.innerHTML = data.tickets.map(tk => {
      const status = STATUS_CONFIG[tk.status] || STATUS_CONFIG.open;
      return `
        <div class="border rounded-3 p-3">
          <div class="d-flex justify-content-between align-items-start mb-2">
            <span class="fw-bold">#${tk.id} — ${tk.category}</span>
            <span class="badge ${status.class}">${status.emoji} ${status.label}</span>
          </div>
          ${tk.mission_title ? `<div class="small text-muted mb-1">${missionLabel}: ${tk.mission_title}</div>` : ''}
          ${tk.description ? `<div class="small mb-2">${tk.description}</div>` : ''}
          ${tk.admin_reply ? `<div class="small bg-light rounded p-2 mt-2"><strong>${replyLabel}:</strong> ${tk.admin_reply}</div>` : ''}
          <div class="text-muted small mt-2">${tk.created_at}</div>
        </div>
      `;
    }).join("");

  } catch (err) {
    console.error("Помилка завантаження звернень:", err);
    container.innerHTML = `<div class="text-center text-danger py-3 small">${loadErrorText}</div>`;
  }
}

document.addEventListener("DOMContentLoaded", loadMyTickets);