import { auth } from "./firebase-config.js";
import { 
  signInWithEmailAndPassword,
  fetchSignInMethodsForEmail
 } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-auth.js";

const form = document.getElementById("loginForm");
const btn = document.getElementById("loginBtn");

function showAlert(message, type = "danger") {
  const alertBox = document.getElementById("authAlert");
  if (alertBox) {
    alertBox.className = `alert alert-${type} mt-3`;
    alertBox.textContent = message;
    alertBox.classList.remove("d-none");
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  // Індикація завантаження на кнопці
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status"></span> Вхід...`;

  try {
    // Авторизація (ТІЛЬКИ email та password)
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    const user = userCredential.user;

    showAlert("Вхід успішний! Перенаправлення...", "success");

    console.log("Авторизовано:", userCredential.user);

    await fetch("/api/session_login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ uid: user.uid })
    });

    setTimeout(() => {
      window.location.href = "/missions-overview";
    }, 900);

  } catch (error) {
    console.error("Помилка входу:", error.code, error.message);

    // Повертаємо кнопці початковий стан
    btn.disabled = false;
    btn.innerText = "Увійти";

    // Обробка помилок саме для ВХОДУ
    switch (error.code) {
      case "auth/invalid-credential":
      case "auth/user-not-found":
      case "auth/wrong-password": {
        const res = await fetch("/api/check_provider", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email })
        });
        const { providers } = await res.json();

        if (providers.includes("google.com") && !providers.includes("password")) {
          showAlert("Цей email зареєстрований через Google. Скористайтесь кнопкою «Увійти через Google».", "info");
        } else {
          showAlert("Невірна електронна пошта або пароль.", "danger");
        }
        break;
      }

      case "auth/invalid-email":
        showAlert("Некоректний формат email.", "danger");
        break;

      case "auth/too-many-requests":
        showAlert("Забагато невдалих спроб. Спробуйте пізніше.", "danger");
        break;

      default:
        showAlert("Помилка входу: " + error.message, "danger");
    }
  }
});