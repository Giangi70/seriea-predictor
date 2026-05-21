"""Persistenza predizioni e risultati reali su SQLite."""
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.config import DB_PATH


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    """Crea le tabelle se non esistono."""
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                match_date  TEXT,
                home_team   TEXT NOT NULL,
                away_team   TEXT NOT NULL,
                prediction  TEXT NOT NULL,   -- H / D / A
                prob_h      REAL,
                prob_d      REAL,
                prob_a      REAL,
                value_bet   INTEGER,         -- 0 / 1
                avg_odds    REAL,            -- quota media esito predetto
                result      TEXT,            -- H / D / A (compilato dopo la partita)
                created_at  TEXT DEFAULT (date('now'))
            )
        """)


def save_prediction(
    home_team: str,
    away_team: str,
    prediction: str,
    prob_h: float,
    prob_d: float,
    prob_a: float,
    value_bet: bool,
    avg_odds: float | None = None,
    match_date: str | None = None,
) -> int:
    """Salva una predizione. Restituisce l'id inserito."""
    init_db()
    with _conn() as con:
        cur = con.execute(
            """INSERT INTO predictions
               (match_date, home_team, away_team, prediction, prob_h, prob_d, prob_a, value_bet, avg_odds)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (match_date, home_team, away_team, prediction,
             prob_h, prob_d, prob_a, int(value_bet), avg_odds),
        )
        return cur.lastrowid


def set_result(prediction_id: int, result: str) -> None:
    """Registra il risultato reale (H/D/A) per una predizione."""
    with _conn() as con:
        con.execute("UPDATE predictions SET result = ? WHERE id = ?", (result, prediction_id))


def get_all_predictions() -> list[dict]:
    """Restituisce tutte le predizioni come lista di dict."""
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM predictions ORDER BY created_at DESC, id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_pending_predictions() -> list[dict]:
    """Restituisce le predizioni senza risultato registrato."""
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM predictions WHERE result IS NULL ORDER BY match_date"
        ).fetchall()
    return [dict(r) for r in rows]


def get_roi_stats() -> dict:
    """Calcola win rate e ROI sulle predizioni con risultato registrato e value_bet=1."""
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT prediction, result, avg_odds FROM predictions WHERE result IS NOT NULL AND value_bet = 1"
        ).fetchall()

    if not rows:
        return {"n": 0, "win_rate": None, "roi": None}

    wins = sum(1 for r in rows if r["prediction"] == r["result"])
    total_return = sum(
        (r["avg_odds"] - 1) if r["prediction"] == r["result"] else -1
        for r in rows
        if r["avg_odds"]
    )
    n = len(rows)
    return {
        "n": n,
        "win_rate": wins / n,
        "roi": total_return / n if n else None,
    }


def save_odds_cache(matches: list[dict]) -> None:
    """Salva le quote scaricate in cache (sovrascrive la cache precedente)."""
    import json
    init_db()
    with _conn() as con:
        con.execute("CREATE TABLE IF NOT EXISTS odds_cache (fetched_at TEXT, data TEXT)")
        con.execute("DELETE FROM odds_cache")
        con.execute("INSERT INTO odds_cache VALUES (datetime('now'), ?)", (json.dumps(matches),))


def load_odds_cache(max_age_hours: int = 6) -> list[dict] | None:
    """Restituisce le quote in cache se più recenti di max_age_hours, altrimenti None."""
    import json
    init_db()
    with _conn() as con:
        con.execute("CREATE TABLE IF NOT EXISTS odds_cache (fetched_at TEXT, data TEXT)")
        row = con.execute(
            "SELECT data, fetched_at FROM odds_cache "
            "WHERE fetched_at >= datetime('now', ?)",
            (f"-{max_age_hours} hours",)
        ).fetchone()
    if row:
        return json.loads(row["data"]), row["fetched_at"]
    return None, None
    """Calcola win rate e ROI sulle predizioni con risultato registrato e value_bet=1."""
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT prediction, result, avg_odds FROM predictions WHERE result IS NOT NULL AND value_bet = 1"
        ).fetchall()

    if not rows:
        return {"n": 0, "win_rate": None, "roi": None}

    wins = sum(1 for r in rows if r["prediction"] == r["result"])
    total_return = sum(
        (r["avg_odds"] - 1) if r["prediction"] == r["result"] else -1
        for r in rows
        if r["avg_odds"]
    )
    n = len(rows)
    return {
        "n": n,
        "win_rate": wins / n,
        "roi": total_return / n,
    }
