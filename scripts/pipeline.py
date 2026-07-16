# scripts/pipeline.py
import os
import time
import json
import sqlite3
import subprocess
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(__file__), "../data/recipes.db")
TEMP_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "../data/temp_audio")
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

COMMON_INGREDIENTS = {
    "salt", "oil", "onion", "tomato", "water", "garlic", "ginger", 
    "green chilli", "red chilli", "turmeric", "cumin", "coriander powder", 
    "garam masala", "black pepper", "mustard seeds", "sugar", "butter"
}

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_pending_reels():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, url, caption FROM reels WHERE status = 'pending'")
    rows = cursor.fetchall()
    conn.close()
    return rows
def download_audio(url, reel_id):
    """Downloads audio only using yt-dlp, without locking browser cookies."""
    output_template = os.path.join(TEMP_AUDIO_DIR, f"audio_{reel_id}.%(ext)s")
    
    command = [
        "yt-dlp",
        "-x",                           # Extract audio
        "--audio-format", "mp3",        # Force MP3 encoding
        "--audio-quality", "5",         # Balanced compression
        "-o", output_template,
        url
    ]
    
    try:
        # Runs cleanly without trying to read Chrome's locked database
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        expected_file = os.path.join(TEMP_AUDIO_DIR, f"audio_{reel_id}.mp3")
        return expected_file if os.path.exists(expected_file) else None
    except subprocess.CalledProcessError as e:
        print(f"  ❌ yt-dlp process failed for Reel {reel_id}.")
        print(f"  [DEBUG ERROR STDOUT]: {e.stdout}")
        print(f"  [DEBUG ERROR STDERR]: {e.stderr}")
        return None
    
def transcribe_audio(file_path):
    """Leverages Groq's super-fast and free cloud-hosted Whisper-v3 model."""
    try:
        with open(file_path, "rb") as file:
            translation = client.audio.transcriptions.create(
                file=(os.path.basename(file_path), file.read()),
                model="whisper-large-v3",
                response_format="text"
            )
            return translation
    except Exception as e:
        print(f"  ❌ Whisper API error: {e}")
        return None

def parse_recipe_details(transcript, caption):
    """Extracts structural JSON details from video transcripts or captions."""
    prompt = f"""
Analyze the recipe text (could be from audio transcript or video caption) and return structured recipe details.
Transcript: "{transcript}"
Instagram Caption: "{caption}"

Return the output strictly in the following JSON format without formatting code blocks or conversational text.
{{
    "recipe_name": "Name of the dish",
    "common": ["list", "of", "common", "ingredients", "used"],
    "special": ["list", "of", "special", "ingredients", "used"]
}}

Categorize your ingredients logically. Common ingredients include:
{', '.join(COMMON_INGREDIENTS)}. Everything else is special.
"""
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        # Parse output safely
        text_response = completion.choices[0].message.content.strip()
        # Clean potential markdown wrapping if present
        if text_response.startswith("```json"):
            text_response = text_response.replace("```json", "", 1).rstrip("` \n")
        elif text_response.startswith("```"):
            text_response = text_response.replace("```", "", 1).rstrip("` \n")
            
        return json.loads(text_response)
    except Exception as e:
        print(f"  ❌ LLM Extraction failed: {e}")
        return None

def save_recipe_to_db(reel_id, name, transcript, common_list, special_list):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Insert main recipe details
        cursor.execute("""
            INSERT OR REPLACE INTO recipes (reel_id, recipe_name, transcript)
            VALUES (?, ?, ?)
        """, (reel_id, name, transcript))
        recipe_id = cursor.lastrowid

        # Insert categorized ingredients
        for ing in common_list:
            cursor.execute("INSERT INTO ingredients (recipe_id, name, category) VALUES (?, ?, 'common')", (recipe_id, ing.strip().lower()))
        for ing in special_list:
            cursor.execute("INSERT INTO ingredients (recipe_id, name, category) VALUES (?, ?, 'special')", (recipe_id, ing.strip().lower()))
            
        # Update reel status
        cursor.execute("UPDATE reels SET status = 'processed' WHERE id = ?", (reel_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"  ❌ SQLite saving error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def run_pipeline():
    pending = get_pending_reels()
    if not pending:
        print("☕ No pending reels found. Database fully up to date!")
        return

    print(f"🚀 Found {len(pending)} pending reels. Initiating processing flow...")
    
    for reel_id, url, caption in pending:
        print(f"\n🎬 Processing reel ID {reel_id}: {url}")
        
        # 1. Download audio payload
        audio_file = download_audio(url, reel_id)
        if not audio_file:
            print("  ❌ Failed to download audio with yt-dlp.")
            mark_reel_failed(reel_id)
            continue

        # 2. Transcribe using Groq Cloud Whisper
        print("  🎙️ Transcribing audio using Whisper-v3 on Groq...")
        transcript = transcribe_audio(audio_file) or ""
        
        # Cleanup temporary files immediately
        if audio_file and os.path.exists(audio_file):
            os.remove(audio_file)
            
        # 3. LLM Extraction
        print("  🧠 Extracting ingredients with Llama-3.3-70b...")
        recipe_data = parse_recipe_details(transcript, caption)
        
        if not recipe_data:
            print("  ❌ Could not extract recipe details.")
            mark_reel_failed(reel_id)
            continue
            
        # 4. Save to Database
        success = save_recipe_to_db(
            reel_id=reel_id,
            name=recipe_data.get("recipe_name", "Unknown Recipe"),
            transcript=transcript,
            common_list=recipe_data.get("common", []),
            special_list=recipe_data.get("special", [])
        )
        
        if success:
            print(f"  🎉 Saved Recipe: '{recipe_data.get('recipe_name')}' successfully!")
        
        # Polite API delay to respect Groq rate-limiting rules
        time.sleep(2)

def mark_reel_failed(reel_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE reels SET status = 'failed' WHERE id = ?", (reel_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    run_pipeline()