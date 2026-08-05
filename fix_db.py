from app import app, db

with app.app_context():
    with db.engine.connect() as conn:
        # Видаляємо стару таблицю зі старими обмеженнями NOT NULL
        conn.execute(db.text("DROP TABLE IF EXISTS notification;"))
        conn.commit()
        print("Стару таблицю notification успішно видалено.")

    # Перестворюємо її наново відповідно до нової моделі у models.py
    db.create_all()
    print("Нову таблицю notification успішно створено!")