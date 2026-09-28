import sqlite3
from pathlib import Path

APP_DIR = Path.home() / ".paperflow"
APP_DIR.mkdir(exist_ok=True)
DB_PATH = APP_DIR / "paperflow.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
 id INTEGER PRIMARY KEY,
 filepath TEXT UNIQUE NOT NULL,
 filename TEXT NOT NULL,
 title TEXT DEFAULT '',
 authors TEXT DEFAULT '',
 journal TEXT DEFAULT '',
 year TEXT DEFAULT '',
 volume TEXT DEFAULT '',
 issue TEXT DEFAULT '',
 pages TEXT DEFAULT '',
 doi TEXT DEFAULT '',
 abstract TEXT DEFAULT '',
 summary TEXT DEFAULT '',
 notes TEXT DEFAULT '',
 added_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute(SCHEMA)
    con.commit()
    return con

def upsert_paper(p):
    con = connect()
    cols = ["filepath","filename","title","authors","journal","year","volume","issue","pages","doi","abstract"]
    vals = [p.get(c,"") for c in cols]
    con.execute(f"""INSERT INTO papers ({",".join(cols)}) VALUES ({",".join("?"*len(cols))})
    ON CONFLICT(filepath) DO UPDATE SET
      filename=excluded.filename,
      title=CASE WHEN excluded.title<>'' THEN excluded.title ELSE papers.title END,
      authors=CASE WHEN excluded.authors<>'' THEN excluded.authors ELSE papers.authors END,
      journal=CASE WHEN excluded.journal<>'' THEN excluded.journal ELSE papers.journal END,
      year=CASE WHEN excluded.year<>'' THEN excluded.year ELSE papers.year END,
      volume=CASE WHEN excluded.volume<>'' THEN excluded.volume ELSE papers.volume END,
      issue=CASE WHEN excluded.issue<>'' THEN excluded.issue ELSE papers.issue END,
      pages=CASE WHEN excluded.pages<>'' THEN excluded.pages ELSE papers.pages END,
      doi=CASE WHEN excluded.doi<>'' THEN excluded.doi ELSE papers.doi END,
      abstract=CASE WHEN excluded.abstract<>'' THEN excluded.abstract ELSE papers.abstract END
    """, vals)
    con.commit()
    con.close()

def list_papers(search=""):
    con = connect()
    if search:
        q = f"%{search}%"
        rows = con.execute("""SELECT * FROM papers WHERE title LIKE ? OR authors LIKE ?
                            OR journal LIKE ? OR doi LIKE ? OR filename LIKE ?
                            ORDER BY year DESC, title""", (q,q,q,q,q)).fetchall()
    else:
        rows = con.execute("SELECT * FROM papers ORDER BY year DESC, title").fetchall()
    con.close()
    return rows

def update_text(pid, field, value):
    if field not in {"summary","notes"}:
        raise ValueError("Invalid field")
    con = connect()
    con.execute(f"UPDATE papers SET {field}=? WHERE id=?", (value,pid))
    con.commit()
    con.close()
