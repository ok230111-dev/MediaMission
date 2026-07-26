// firebase-config.js
import { initializeApp } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-app.js";
import { getAnalytics } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-analytics.js";
import { initializeFirestore } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-firestore.js";
import {
    getAuth,
    GoogleAuthProvider
} from "https://www.gstatic.com/firebasejs/12.16.0/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyAYBFjeI5iiff4LbODy24kn-4A1j0Mctto",
  authDomain: "mediamission-a0b70.firebaseapp.com",
  projectId: "mediamission-a0b70",
  storageBucket: "mediamission-a0b70.firebasestorage.app",
  messagingSenderId: "670283569215",
  appId: "1:670283569215:web:5a27f444d9f7c4cdf9808a"
};

const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);

export const auth = getAuth(app);
export const provider = new GoogleAuthProvider();

export const db = initializeFirestore(app, {
    experimentalForceLongPolling: true,
    useFetchStreams: false
});