#!/usr/bin/env python3
"""
Export a SQLite database to CSV (one file per table/view), optionally as a .zip.

    python export_csv.py --db app.db                          # everything -> ./export/
    python export_csv.py --db app.db --user-id 1 --zip        # one user's data -> export_user1.zip
    python export_csv.py --db app.db --include-views          # also dump v_all_metrics etc.

The `userlog` (login) table is always skipped because it holds credentials.
Use only the standard library, so it also works inside your FastAPI server
(import export_database and call it from a download endpoint).
"""
import argparse
import csv
import shutil
import sqlite3
import sys
from pathlib import Path

SKIP = {"userlog", "users", "sqlite_sequence"}


def q(name):  # quote an identifier that came from sqlite_master
    return '"' + name.replace('"', '""') + '"'


def export_database(db_path, out_dir, user_id=None, include_views=False, make_zip=False):
    conn = sqlite3.connect(db_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    kinds = ("table", "view") if include_views else ("table",)
    objects = conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN (%s) AND name NOT LIKE 'sqlite_%%' ORDER BY name"
        % ",".join("?" * len(kinds)), kinds).fetchall()
    written = []
    for (name,) in objects:
        if name in SKIP:
            continue
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({q(name)})")]
        sql, params = f"SELECT * FROM {q(name)}", ()
        if user_id is not None and "user_id" in cols:
            sql, params = sql + " WHERE user_id = ?", (user_id,)
        cur = conn.execute(sql, params)
        path = out / f"{name}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([d[0] for d in cur.description])
            n = 0
            for row in cur:
                writer.writerow(row)
                n += 1
        written.append((name, n))
    conn.close()
    if make_zip:
        archive = shutil.make_archive(str(out), "zip", out)
        return written, archive
    return written, None


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", required=True)
    p.add_argument("--out", help="output folder (default: export or export_user<ID>)")
    p.add_argument("--user-id", type=int, help="only export rows belonging to this user")
    p.add_argument("--include-views", action="store_true")
    p.add_argument("--zip", action="store_true", help="also create <out>.zip")
    a = p.parse_args()
    if not Path(a.db).exists():
        sys.exit(f"Database not found: {a.db}")
    out = a.out or (f"export_user{a.user_id}" if a.user_id is not None else "export")
    written, archive = export_database(a.db, out, a.user_id, a.include_views, a.zip)
    for name, n in written:
        print(f"  {name + '.csv':32s}{n:>9d} rows")
    print(f"\nWrote {len(written)} files to {out}/" + (f" and {archive}" if archive else ""))


if __name__ == "__main__":
    main()
