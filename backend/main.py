# backend/main.py
import os
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DB_PATH = os.path.join(os.path.dirname(__file__), "../data/recipes.db")

app = FastAPI(title="Digital Cookbook Backend")

# Enable CORS for local React development or production deployment URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StatusUpdate(BaseModel):
    approved: int # 1 = approved, 0 = skipped

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@app.get("/api/recipes")
def get_recipes():
    """Returns approved/unreviewed recipes grouped dynamically by special ingredients (chapters)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    # Query recipes and join with matching reel details
    cursor.execute("""
        SELECT 
            r.id, 
            r.recipe_name, 
            r.transcript, 
            r.approved,
            re.url as reel_url, 
            re.caption
        FROM recipes r
        JOIN reels re ON r.reel_id = re.id
        WHERE r.approved IS NOT 0 -- Filter out skipped recipes
    """)
    recipes = cursor.fetchall()

    # Get ingredients for each recipe
    for recipe in recipes:
        cursor.execute("SELECT name, category FROM ingredients WHERE recipe_id = ?", (recipe["id"],))
        ingredients = cursor.fetchall()
        recipe["common_ingredients"] = [ing["name"] for ing in ingredients if ing["category"] == "common"]
        recipe["special_ingredients"] = [ing["name"] for ing in ingredients if ing["category"] == "special"]

    conn.close()
    return recipes

@app.post("/api/recipes/{recipe_id}/status")
def update_recipe_status(recipe_id: int, payload: StatusUpdate):
    """Updates the recipe status (Approve: 1, Skip: 0)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE recipes SET approved = ? WHERE id = ?", (payload.approved, recipe_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Recipe not found")
        conn.commit()
        return {"status": "success", "message": f"Recipe status updated to {payload.approved}"}
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)