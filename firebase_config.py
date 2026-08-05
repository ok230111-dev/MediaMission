import firebase_admin
from firebase_admin import credentials, auth  # Додайте auth тут
import os

# Ініціалізація Firebase
cred_path = "serviceAccountKey.json"

if not os.path.exists(cred_path):
    # Спробуємо інші варіанти
    alternatives = [
        "mediamission-a0b70-firebase-adminsdk-fbsvc-9cea1cad13.json",
        "serviceAccountKey.json.json"
    ]
    for alt in alternatives:
        if os.path.exists(alt):
            cred_path = alt
            break
    else:
        raise FileNotFoundError(f"Файл облікових даних не знайдено")

print(f"✅ Використовуємо файл: {cred_path}")
cred = credentials.Certificate(cred_path)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
    print("✅ Firebase Admin SDK ініціалізовано!")

# Експортуємо auth для використання в інших файлах
# Тепер можна робити: from firebase_config import auth