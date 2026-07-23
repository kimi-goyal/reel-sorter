import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "../data/recipes.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reels (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            url              TEXT UNIQUE,
            caption          TEXT,
            hashtags         TEXT,
            creator_name     TEXT,
            creator_username TEXT,
            collection_name  TEXT,
            status           TEXT DEFAULT 'pending', -- pending, processed, failed
            created_at       TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            reel_id      INTEGER UNIQUE,
            recipe_name  TEXT,
            transcript   TEXT,
            approved     INTEGER DEFAULT NULL, -- NULL = Unreviewed, 1 = Approved, 0 = Skipped
            tried_at     TEXT,
            FOREIGN KEY(reel_id) REFERENCES reels(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingredients (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER,
            name      TEXT,
            category  TEXT, -- 'common' or 'special'
            FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()
    print("✨ Database initialized successfully.")

if __name__ == "__main__":
    init_db()