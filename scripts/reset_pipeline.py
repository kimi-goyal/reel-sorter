# scripts/reset_pipeline.py
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "../data/recipes.db")

def reset_pipeline():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Enable foreign keys so deleting a recipe automatically cascades and deletes its ingredients
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # 2. Clear out all downstream recipe and ingredient data
    cursor.execute("DELETE FROM recipes;")
    print("🧹 Cleared recipes and ingredients tables.")
    
    # 3. Mark all reels back to pending
    cursor.execute("UPDATE reels SET status = 'pending';")
    print("🔄 Reset all reel statuses back to 'pending'.")
    
    conn.commit()
    conn.close()
    print("✨ Ready to run pipeline.py again!")

if __name__ == "__main__":
    reset_pipeline()