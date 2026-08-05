import { getMessaging, getToken } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-messaging.js";
import { app } from "./firebase-config.js";

const messaging = getMessaging(app);

// Глобальна функція сповіщення, розрахована на Bootstrap Modal z-index
export function showAlert(message, type = "success") {
    let alertContainer = document.getElementById("alert-container");
    if (!alertContainer) {
        alertContainer = document.createElement("div");
        alertContainer.id = "alert-container";
        alertContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1090;
            min-width: 300px;
            max-width: 400px;
        `;
        document.body.appendChild(alertContainer);
    }

    const alertEl = document.createElement("div");
    alertEl.className = `alert alert-${type} alert-dismissible fade show shadow-lg border-0`;
    alertEl.style.borderRadius = "12px";

    let icon = '🔔';
    if (type === 'success') icon = '✅';
    if (type === 'danger') icon = '❌';
    if (type === 'warning') icon = '⚠️';
    if (type === 'info') icon = 'ℹ️';

    alertEl.innerHTML = `
        <div class="d-flex align-items-center justify-content-between">
            <div class="d-flex align-items-center gap-2">
                <span>${icon}</span>
                <span class="fw-semibold small">${message}</span>
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;

    alertContainer.appendChild(alertEl);

    setTimeout(() => {
        alertEl.classList.remove("show");
        setTimeout(() => alertEl.remove(), 300);
    }, 4000);
}

// Прив'язуємо listener ТІЛЬКИ після повного завантаження DOM
document.addEventListener("DOMContentLoaded", () => {
    const pushSwitch = document.getElementById("pushNotificationsSwitch");

    if (!pushSwitch) {
        console.warn("Перемикач #pushNotificationsSwitch не знайдено на сторінці.");
        return;
    }

    // Перевірка дозволу при відкритті
    if (Notification.permission === "granted") {
        pushSwitch.checked = true;
    }

    pushSwitch.addEventListener("change", async () => {
        if (pushSwitch.checked) {
            try {
                // 1. Запит дозволу
                const permission = await Notification.requestPermission();

                if (permission !== "granted") {
                    pushSwitch.checked = false;
                    showAlert("Дозвіл на сповіщення відхилено в браузері!", "warning");
                    return;
                }

                // 2. Отримання токена
                const token = await getToken(messaging, {
                    vapidKey: "BD3FQs9fZ4EbLPDubiJ5NsrDnA3orDBtV9NsFs-Xj16oVGbqbzlSk0bCQ0MBFasq2BQZHipxJ6xtOdIZU_kdqG0"
                });

                if (!token) {
                    pushSwitch.checked = false;
                    showAlert("Не вдалося отримати PUSH-токен!", "danger");
                    return;
                }

                // 3. Відправка на Flask Backend
                const response = await fetch("/api/save_notification_token", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ token: token })
                });

                if (response.ok) {
                    showAlert("PUSH-сповіщення успішно увімкнено!", "success");
                } else {
                    pushSwitch.checked = false;
                    showAlert("Помилка збереження токена на сервері", "danger");
                }

            } catch (err) {
                console.error("Помилка при збереженні Push-токена:", err);
                pushSwitch.checked = false;
                showAlert("Виникла помилка під час активації", "danger");
            }
        } else {
            showAlert("PUSH-сповіщення вимкнено", "info");
        }
    });
});

// Автоматично ініціалізуємо при відкритті модального вікна акаунта
document.addEventListener("DOMContentLoaded", () => {
    const accountModal = document.getElementById("accountInfoModal");
    if (accountModal) {
        accountModal.addEventListener("shown.bs.modal", () => {
            initNotifications();
        });
    } else {
        initNotifications();
    }
});