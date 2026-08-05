import { auth, db } from "./firebase-config.js";

import {
    createUserWithEmailAndPassword,
    updateProfile
} from "https://www.gstatic.com/firebasejs/12.16.0/firebase-auth.js";

import { doc, setDoc, serverTimestamp } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-firestore.js";

function showAlert(message, type = "danger") {
    const alertBox = document.getElementById("authAlert");
    alertBox.className = `alert alert-${type} mt-3`;
    alertBox.textContent = message;
    alertBox.classList.remove("d-none");
}

const form = document.getElementById("registerForm");
const btn = document.getElementById("registerBtn");

form.addEventListener("submit", async (e) => {
    e.preventDefault(); // дуже важливо!

    const name = document.getElementById("name").value;
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    // Блокуємо кнопку та показуємо стан завантаження
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status"></span> Реєстрація...`;

    try {
        // 1. Створюємо користувача (ТІЛЬКИ email та password)
        const userCredential = await createUserWithEmailAndPassword(
            auth,
            email,
            password,
        );
        const user = userCredential.user;

        // 2. Зберігаємо Nickname в профілі користувача
        if (name) {
          await updateProfile(user, {
            displayName: name
          });
        }

        // 3. 🔑 ГОЛОВНЕ: Зберігаємо користувача в базу даних Firestore!
        // await setDoc(doc(db, "users", user.uid), {
        //     uid: user.uid,
        //     displayName: name || "Користувач",
        //     email: email,
        //     total_xp: 0,
        //     missions_completed: 0,
        //     day_streak: 1,
        //     accuracy_answers: 100,
        //     createdAt: serverTimestamp()
        // });

        await fetch("/api/create_user", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                uid: user.uid,
                email: user.email,
                display_name: user.displayName,
                provider: user.providerData[0]?.providerId || "password",
            })
        });

        const sessionResponse = await fetch("/api/session_login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ uid: user.uid })
        });
        const sessionData = await sessionResponse.json();
        if (!sessionResponse.ok || sessionData.success !== true) {
            throw new Error(sessionData.error || "Не вдалося встановити сесію");
        }

        showAlert("Реєстрація успішна! Перенаправлення...", "success");

        setTimeout(() => {
            window.location.href = "/missions-overview";
        }, 900);

    } catch (error) {
        console.log(error);

        // Повертаємо кнопці початковий стан
        btn.disabled = false;
        btn.innerText = "Зареєструватися";

        switch (error.code) {

        case "auth/email-already-in-use":
            showAlert("Користувач з таким email вже існує." , "danger");
            break;

        case "auth/weak-password":
            showAlert("Пароль має містити щонайменше 6 символів.", "danger");
            break;

        case "auth/invalid-email":
            showAlert("Некоректний email.", "danger");
            break;

        case "auth/network-request-failed":
            showAlert("Перенаправлення до Входу", "info");
            window.location.href = "/login";
            break;

        default:
            showAlert(error.message, "danger");
        }
    }
});
