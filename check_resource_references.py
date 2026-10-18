import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from sqlalchemy import inspect, text
from app.db.session import engine

inspector = inspect(engine)
targets = {
    "buildings": {1, 2, 3},
    "rooms": {1, 2, 3, 4, 5, 6},
}
with engine.connect() as conn:
    for table, ids in targets.items():
        print(f"\nReferences to {table}, IDs {sorted(ids)}:")
        found = False
        for other_table in inspector.get_table_names():
            for fk in inspector.get_foreign_keys(other_table):
                if fk.get("referred_table") != table:
                    continue
                columns = fk.get("constrained_columns") or []
                referred = fk.get("referred_columns") or []
                for col, ref_col in zip(columns, referred):
                    if ref_col != "id":
                        continue
                    query = text(
                        f'SELECT "{col}", COUNT(*) FROM "{other_table}" '
                        f'WHERE "{col}" IN :ids GROUP BY "{col}"'
                    ).bindparams()
                    # Use an expanding parameter for the ID list.
                    from sqlalchemy import bindparam
                    query = text(
                        f'SELECT "{col}", COUNT(*) FROM "{other_table}" '
                        f'WHERE "{col}" IN :ids GROUP BY "{col}"'
                    ).bindparams(bindparam("ids", expanding=True))
                    rows = conn.execute(query, {"ids": list(ids)}).fetchall()
                    for row in rows:
                        print(f"  {other_table}.{col}: ID {row[0]} -> {row[1]} row(s)")
                        found = True
        if not found:
            print("  No references found.")
