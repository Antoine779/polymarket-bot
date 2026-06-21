import sqlite3
from datetime import datetime

DB_PATH = "subscribers.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS subscribers (
        chat_id INTEGER PRIMARY KEY,
        first_name TEXT,
        username TEXT,
        language TEXT,
        joined_at TEXT
    )""")
    c.execute("CREATE TABLE IF NOT EXISTS sent_alerts (slug TEXT PRIMARY KEY)")
    c.execute("""CREATE TABLE IF NOT EXISTS tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        source TEXT,
        timestamp TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS odds_history (
    match_slug TEXT,
    team TEXT,
    probability REAL,
    updated_at TEXT,
    PRIMARY KEY (match_slug, team)
)""")
    conn.commit()
    conn.close()


def add_subscriber(chat_id, first_name="", username="", language=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO subscribers (chat_id, first_name, username, language, joined_at) VALUES (?, ?, ?, ?, ?)",
        (chat_id, first_name, username, language, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


def remove_subscriber(chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM subscribers WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()


def get_all_subscribers():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT chat_id FROM subscribers")
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]


def get_subscriber_count():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM subscribers")
    total = c.fetchone()[0]
    conn.close()
    return total


def get_recent_subscribers(limit=5):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT first_name, username, language, joined_at FROM subscribers ORDER BY joined_at DESC LIMIT ?",
        (limit,)
    )
    rows = c.fetchall()
    conn.close()
    return rows


def log_source(chat_id, source):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO tracking (chat_id, source, timestamp) VALUES (?, ?, ?)",
        (chat_id, source, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


def get_tracking_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT source, COUNT(*) as total FROM tracking GROUP BY source ORDER BY total DESC")
    rows = c.fetchall()
    conn.close()
    return rows


def is_alert_sent(slug):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT slug FROM sent_alerts WHERE slug = ?", (slug,))
    result = c.fetchone()
    conn.close()
    return result is not None


def mark_alert_sent(slug):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO sent_alerts (slug) VALUES (?)", (slug,))
    conn.commit()
    conn.close()

    def get_last_odds(match_slug, team):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT probability FROM odds_history WHERE match_slug = ? AND team = ?",
        (match_slug, team)
    )
    result = c.fetchone()
    conn.close()
    return result[0] if result else None


def update_odds(match_slug, team, probability):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO odds_history (match_slug, team, probability, updated_at) VALUES (?, ?, ?, ?)",
        (match_slug, team, probability, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()