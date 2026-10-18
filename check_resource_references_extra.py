import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from sqlalchemy import inspect, text, bindparam
from app.db.session import engine

inspector = inspect(engine)
checks = [
    ("room_id", [1, 2, 3, 4, 5, 6]),
    ("building_id", [1, 2, 3]),
]

with engine.connect() as conn:
    for column_name, ids in checks:
        print(f"\nChecking {column_name} values {ids}:")
        found = False
        for table in inspector.get_table_names():
            columns = {c["name"] for c in inspector.get_columns(table)}
            if column_name not in columns:
                continue
            query = text(
                f'SELECT "{column_name}", COUNT(*) FROM "{table}" '
                f'WHERE "{column_name}" IN :ids GROUP BY "{column_name}"'
            ).bindparams(bindparam("ids", expanding=True))
            rows = conn.execute(query, {"ids": ids}).fetchall()
            for row in rows:
                print(f"  {table}.{column_name}: ID {row[0]} -> {row[1]} row(s)")
                found = True
        if not found:
            print("  No references found.")
