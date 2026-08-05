// static/js/firebase-config.js
import { initializeApp } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-app.js";
import { getAnalytics } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-analytics.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-firestore.js";
import { getAuth, GoogleAuthProvider } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-auth.js";
import { getMessaging, getToken, onMessage } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-messaging.js";

const firebaseConfig = {
  apiKey: "AIzaSyAYBFjeI5iiff4LbODy24kn-4A1j0Mctto",
  authDomain: "mediamission-a0b70.firebaseapp.com",
  projectId: "mediamission-a0b70",
  storageBucket: "mediamission-a0b70.firebasestorage.app",
  messagingSenderId: "670283569215",
  appId: "1:670283569215:web:5a27f444d9f7c4cdf9808a",
  measurementId: "G-6634TK13EZ"
};

// Ініціалізація Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
const auth = getAuth(app);
const db = getFirestore(app);
const provider = new GoogleAuthProvider();

// Ініціалізація Messaging (з обробкою помилок)
let messaging = null;
try {
    messaging = getMessaging(app);
    console.log("✅ Firebase Messaging ініціалізовано");
} catch (error) {
    console.warn("⚠️ Firebase Messaging не доступний:", error.message);
}

// ЕКСПОРТУЄМО ВСІ ОБ'ЄКТИ
export { app, auth, db, provider, analytics, messaging, getToken, onMessage };