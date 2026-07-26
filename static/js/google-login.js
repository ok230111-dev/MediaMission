import { auth, provider } from "./firebase-config.js";

import {
    signInWithPopup
} from "https://www.gstatic.com/firebasejs/12.16.0/firebase-auth.js";

const btn = document.getElementById("googleBtn");

function showAlert(message, type = 'danger') {
    const alertBox = document.getElementById("authAlert");
    alertBox.className = `alert alert-${type} mt-3`;
    alertBox.textContent = message;
    alertBox.classList.remove("d-none");
}

btn.addEventListener("click", async () => {
    try {
        const result = await signInWithPopup(auth, provider);
        const user = result.user;

        // 1. Створюємо запис у власній БД, якщо його ще немає
        await fetch("/api/create_user", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                uid: user.uid,
                email: user.email,
                display_name: user.displayName || "Користувач",
                provider: user.providerData[0]?.providerId || "google.com",
                email_verified: user.emailVerified
            })
        });

        // 2. Встановлюємо Flask-сесію
        await fetch("/api/session_login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ uid: user.uid })
        });

        showAlert("Вхід успішний!", "success");

        setTimeout(() => {
            window.location.href = "/missions-overview";
        }, 900);

    } catch (error) {
        console.error("Помилка входу через Google:", error);
        showAlert(error.message, "danger");
    }
});