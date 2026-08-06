importScripts('https://www.gstatic.com/firebasejs/12.16.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/12.16.0/firebase-messaging-compat.js');

const firebaseConfig = {
    apiKey: "AIzaSyAYBFjeI5iiff4LbODy24kn-4A1j0Mctto",
    authDomain: "mediamission-a0b70.firebaseapp.com",
    projectId: "mediamission-a0b70",
    storageBucket: "mediamission-a0b70.firebasestorage.app",
    messagingSenderId: "670283569215",
    appId: "1:670283569215:web:5a27f444d9f7c4cdf9808a",
    measurementId: "G-6634TK13EZ"
};

firebase.initializeApp(firebaseConfig);
const messaging = firebase.messaging();

// ---------- PUSH NOTIFICATIONS ----------
messaging.onBackgroundMessage(function(payload) {
    console.log('[firebase-messaging-sw.js] Received background message ', payload);

    const notificationTitle = payload.notification?.title || 'MediaMission';
    
    // Отримуємо URL для переходу з fcmOptions чи data
    const targetUrl = payload.fcmOptions?.link || payload.data?.url || '/';

    const notificationOptions = {
        body: payload.notification?.body || '',
        icon: '/static/icons/icon-192.png',
        badge: '/static/favicon/favicon-32x32.png',
        data: {
            url: targetUrl
        }
    };

    self.registration.showNotification(notificationTitle, notificationOptions);
});

// Клік по сповіщенню
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    
    const targetUrl = event.notification.data?.url || '/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(windowClients) {
            // Якщо сайт уже відкритий у вкладці — фокусуємося і переходимо
            for (let i = 0; i < windowClients.length; i++) {
                let client = windowClients[i];
                if (client.url.includes(self.location.origin) && 'focus' in client) {
                    client.navigate(targetUrl);
                    return client.focus();
                }
            }
            // Якщо вкладка закрита — відкриваємо нову
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});

// ---------- CACHE CONFIG ----------
const CACHE_NAME = 'mediamission-54'; // Оновили версію кешу
const STATIC_CACHE = `static-${CACHE_NAME}`;
const DYNAMIC_CACHE = `dynamic-${CACHE_NAME}`;

const STATIC_FILES = [
    "/",
    "/offline",
    "/static/css/style.css",
    "/static/js/theme.js",
    "/static/js/authorized.js",
    "/static/favicon/favicon.ico",
    "/static/favicon/favicon-32x32.png",
    "/static/favicon/favicon-16x16.png",
    "/static/icons/icon-192.png",
    "/static/icons/icon-512.png"
];

// ---------- INSTALL ----------
self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('🔄 Кешуємо статичні файли...');
                return Promise.all(
                    STATIC_FILES.map(url => {
                        return cache.add(url).catch(error => {
                            console.warn(`⚠️ Не вдалося закешувати: ${url}`, error);
                        });
                    })
                );
            })
            .then(() => {
                console.log('✅ Service Worker встановлено!');
                return self.skipWaiting();
            })
    );
});

// ---------- ACTIVATE ----------
self.addEventListener("activate", event => {
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys
                    .filter(key => key !== STATIC_CACHE && key !== DYNAMIC_CACHE)
                    .map(key => {
                        console.log(`🗑️ Видаляємо старий кеш: ${key}`);
                        return caches.delete(key);
                    })
            );
        })
        .then(() => {
            console.log('✅ Service Worker активовано!');
            return self.clients.claim();
        })
    );
});

// ---------- FETCH ----------
self.addEventListener("fetch", event => {
    if (event.request.method !== "GET") return;

    // API-запити — завжди йдемо в мережу, ніколи не кешуємо
    if (event.request.url.includes("/api/")) {
        event.respondWith(fetch(event.request));
        return;
    }

    // HTML - network first
    if (event.request.headers.get("accept")?.includes("text/html")) {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    const clone = response.clone();
                    caches.open(DYNAMIC_CACHE)
                        .then(cache => cache.put(event.request, clone));
                    return response;
                })
                .catch(() => {
                    return caches.match(event.request)
                        .then(cacheResponse => cacheResponse || caches.match("/offline"));
                })
        );
        return;
    }

    // Інші файли - cache first
    event.respondWith(
        caches.match(event.request)
            .then(cacheResponse => {
                if (cacheResponse) return cacheResponse;
                return fetch(event.request)
                    .then(networkResponse => {
                        if (!networkResponse || networkResponse.status !== 200) {
                            return networkResponse;
                        }
                        const clone = networkResponse.clone();
                        caches.open(DYNAMIC_CACHE)
                            .then(cache => cache.put(event.request, clone));
                        return networkResponse;
                    });
            })
    );
});