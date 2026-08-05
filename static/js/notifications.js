import { getMessaging, getToken } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-messaging.js";
import { app } from "./firebase-config.js";

const messaging = getMessaging(app);

// 1. Показ сповіщень поверх усіх модальних вікон
export function showAlert(message, type = "success") {
    let alertContainer = document.getElementById("alert-container");
    if (!alertContainer) {
        alertContainer = document.createElement("div");
        alertContainer.id = "alert-container";
        alertContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
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

// 2. Ініціалізація та прив'язка
function initNotifications() {
    console.log("🔍 [PUSH] Спроба знайти #pushNotificationsSwitch...");
    const pushSwitch = document.getElementById("pushNotificationsSwitch");

    if (!pushSwitch) {
        console.warn("⚠️ [PUSH] #pushNotificationsSwitch не знайдено на сторінці.");
        return;
    }

    console.log("✅ [PUSH] Перемикач знайдено! Поточний статус дозволу:", Notification.permission);

    if (Notification.permission === "granted") {
        pushSwitch.checked = true;
    }

    if (pushSwitch.dataset.initialized === "true") {
        return;
    }
    pushSwitch.dataset.initialized = "true";

    pushSwitch.addEventListener("change", async () => {
        console.log("👉 [PUSH] Зміна стану перемикача:", pushSwitch.checked);

        if (pushSwitch.checked) {
            try {
                showAlert("Запит дозволу на сповіщення...", "info");

                // Перевірка підтримки браузером
                if (!("Notification" in window)) {
                    showAlert("Цей браузер не підтримує PUSH-сповіщення!", "danger");
                    pushSwitch.checked = false;
                    return;
                }

                const permission = await Notification.requestPermission();
                console.log("📋 [PUSH] Результат запиту дозволу:", permission);

                if (permission !== "granted") {
                    pushSwitch.checked = false;
                    showAlert("Дозвіл на сповіщення відхилено в налаштуваннях браузера!", "warning");
                    return;
                }

                showAlert("Отримання FCM-токена...", "info");

                const token = await getToken(messaging, {
                    vapidKey: "BD3FQs9fZ4EbLPDubiJ5NsrDnA3orDBtV9NsFs-Xj16oVGbqbzlSk0bCQ0MBFasq2BQZHipxJ6xtOdIZU_kdqG0"
                });

                console.log("🔑 [PUSH] Отримано FCM Токен:", token);

                if (!token) {
                    pushSwitch.checked = false;
                    showAlert("Не вдалося отримати PUSH-токен від Firebase!", "danger");
                    return;
                }

                const response = await fetch("/api/save_notification_token", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ token: token })
                });

                console.log("🌐 [PUSH] Відповідь сервера на збереження токена:", response.status);

                if (response.ok) {
                    showAlert("PUSH-сповіщення успішно увімкнено!", "success");
                } else {
                    pushSwitch.checked = false;
                    showAlert("Помилка збереження токена на сервері (HTTP " + response.status + ")", "danger");
                }

            } catch (err) {
                console.error("❌ [PUSH] Помилка:", err);
                pushSwitch.checked = false;
                showAlert("Помилка: " + err.message, "danger");
            }
        } else {
            showAlert("PUSH-сповіщення вимкнено", "info");
        }
    });
}

// Запуск
document.addEventListener("DOMContentLoaded", () => {
    initNotifications();

    const accountModal = document.getElementById("accountInfoModal");
    if (accountModal) {
        accountModal.addEventListener("shown.bs.modal", () => {
            initNotifications();
        });
    }
});