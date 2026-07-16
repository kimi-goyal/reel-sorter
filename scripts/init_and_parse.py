# scripts/init_and_parse.py
import os
import json
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "../data/recipes.db")
EXPORT_PATH = os.path.join(os.path.dirname(__file__), "../data/instagram_export/saved_collections.json")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Reels Table
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

    # 2. Recipes Table
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

    # 3. Ingredients Table
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

def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)

def get_collection_name(collection):
    for label in collection.get("label_values", []):
        if label.get("label") == "Name":
            return label.get("value")
    return None

def find_target_collection(data, target_name):
    for collection in data:
        if get_collection_name(collection) == target_name:
            return collection
    return None

def extract_reels_from_collection(collection):
    for item in collection.get("label_values", []):
        if "dict" in item:
            return item["dict"]
    return []

def clean_reel_data(reel):
    clean = {
        "url": None,
        "caption": "",
        "hashtags": [],
        "creator_name": None,
        "creator_username": None
    }
    for item in reel.get("dict", []):
        label = item.get("label")
        title = item.get("title")
        
        if label == "URL":
            clean["url"] = item.get("value")
        elif label == "Caption":
            clean["caption"] = item.get("value") or ""
        elif title == "Hashtags":
            for sub in item.get("dict", []):
                for sub_field in sub.get("dict", []):
                    if sub_field.get("label") == "Name":
                        clean["hashtags"].append(sub_field.get("value"))
        elif title == "Owner":
            for sub in item.get("dict", []):
                for sub_field in sub.get("dict", []):
                    if sub_field.get("label") == "Name":
                        clean["creator_name"] = sub_field.get("value")
                    elif sub_field.get("label") == "Username":
                        clean["creator_username"] = sub_field.get("value")
    return clean

def populate_db():
    if not os.path.exists(EXPORT_PATH):
        print(f"❌ Instagram export file not found at {EXPORT_PATH}")
        return

    data = load_json(EXPORT_PATH)
    cook_collection = find_target_collection(data, "Cook")
    
    if not cook_collection:
        print("❌ 'Cook' collection not found in saved_collections.json")
        return

    reels_list = extract_reels_from_collection(cook_collection)
    print(f"Found {len(reels_list)} items in 'Cook' collection. Processing...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    inserted, skipped = 0, 0
    for raw_reel in reels_list:
        reel = clean_reel_data(raw_reel)
        if not reel["url"]:
            continue
            
        try:
            cursor.execute("""
                INSERT INTO reels (url, caption, hashtags, creator_name, creator_username, collection_name, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                reel["url"],
                reel["caption"],
                json.dumps(reel["hashtags"]),
                reel["creator_name"],
                reel["creator_username"],
                "Cook",
                datetime.now().isoformat()
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1

    conn.commit()
    conn.close()
    print(f"✅ Ingestion Complete. Saved to database: {inserted} reels | Already existing (skipped): {skipped}")

if __name__ == "__main__":
    init_db()
    populate_db()