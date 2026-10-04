import os, sys
from sqlalchemy import create_engine, text, inspect
from app import app
from extensions import db
import models  # реєструє всі моделі

if len(sys.argv) < 2:
    sys.exit("Використання: python import_sqlite.py шлях\\до\\файлу.db")

sqlite_engine = create_engine(f"sqlite:///{sys.argv[1]}")
pg_url = os.environ["DATABASE_URL"].replace("postgres://", "postgresql://", 1)
pg_engine = create_engine(pg_url)

tables = db.metadata.sorted_tables  # порядок з урахуванням зовнішніх ключів
lite_tables = set(inspect(sqlite_engine).get_table_names())

with pg_engine.begin() as pg, sqlite_engine.connect() as lite:
    names = ", ".join(f'"{t.name}"' for t in tables)
    pg.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))

    for t in tables:
        if t.name not in lite_tables:
            print(f"ПРОПУСК {t.name}: немає в SQLite")
            continue
        lite_cols = {c["name"] for c in inspect(sqlite_engine).get_columns(t.name)}
        cols = [c for c in t.c if c.name in lite_cols]
        missing = [c.name for c in t.c if c.name not in lite_cols]
        if missing:
            print(f"  {t.name}: немає колонок у SQLite: {missing}")
        rows = [dict(r) for r in lite.execute(t.select().with_only_columns(*cols)).mappings()]
        if rows:
            pg.execute(t.insert(), rows)
        print(f"{t.name}: {len(rows)} рядків")

    for t in tables:
        if "id" in t.c:
            pg.execute(text(
                f"SELECT setval(pg_get_serial_sequence('{t.name}', 'id'), "
                f"COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM \"{t.name}\""
            ))
print("Готово")