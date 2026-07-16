# scripts/ai_engine.py
import os
import sqlite3
import json
import chromadb
from chromadb.utils import embedding_functions
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# System Paths
DB_PATH = os.path.join(os.path.dirname(__file__), "../data/recipes.db")
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "../data/chroma_db")

# 1. Initialize System Clients
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

# Using local all-MiniLM-L6-v2 embeddings to show end-to-end ML pipelining
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
vector_collection = chroma_client.get_or_create_collection(name="recipe_transcripts", embedding_function=embedding_func)
# Helper extraction layer functions adapted directly from your original schema layout
def _get_instagram_collection_title(collection_obj):
    """Pulls the visible name from the label_values dictionary structure."""
    for label in collection_obj.get("label_values", []):
        if label.get("label") == "Name":
            return label.get("value")
    return None

def ingest_user_instagram_collection(json_file_path, target_collection_name):
    """
    Parses your Instagram data export file using its native label_values nested dictionary format,
    runs a fuzzy match on the chosen collection name, and ingests the recipes.
    """
    if not os.path.exists(json_file_path):
        raise FileNotFoundError(f"Could not find the file at {json_file_path}")
        
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    found_names = []
    matched_collection = None
    search_term = target_collection_name.lower().strip()
    
    # 1. Loop through your file format to extract matching names via label keys
    for collection in data:
        name = _get_instagram_collection_title(collection)
        if name:
            found_names.append(name)
            if search_term in name.lower():
                matched_collection = collection
                break
                
    if not matched_collection:
        available_str = ", ".join(f"'{n}'" for n in found_names)
        raise ValueError(
            f"No collection matching '{target_collection_name}' found. "
            f"Available options in your file are: {available_str if available_str else 'None found'}"
        )
        
    # 2. Extract the deeply nested list array of items using your original data schema format
    reels_list = []
    for item in matched_collection.get("label_values", []):
        if "dict" in item:
            reels_list = item["dict"]
            break
            
    if not reels_list:
        raise ValueError(f"Found the collection '{_get_instagram_collection_title(matched_collection)}', but it contains no inner raw data objects.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    processed_count = 0
    
    # 3. Clean and process the individual raw links inside the dict frame structure
    for raw_reel in reels_list:
        url = None
        caption = ""
        creator_username = "Instagram Import"
        
        # Deep unpack inner label fields
        for inner_item in raw_reel.get("dict", []):
            label = inner_item.get("label")
            title = inner_item.get("title")
            
            if label == "URL":
                url = inner_item.get("value")
            elif label == "Caption":
                caption = inner_item.get("value") or ""
            elif title == "Owner":
                for sub in inner_item.get("dict", []):
                    for sub_field in sub.get("dict", []):
                        if sub_field.get("label") == "Username":
                            creator_username = sub_field.get("value")

        if not url:
            continue
            
        # Prevent double insertion collisions
        cursor.execute("SELECT id FROM reels WHERE url = ?", (url,))
        exists = cursor.fetchone()
        if exists:
            continue
            
        # 4. Insert into SQLite reels and recipes tables matching database schemas
        actual_collection_name = _get_instagram_collection_title(matched_collection)
        cursor.execute("""
            INSERT INTO reels (url, caption, creator_username, collection_name, status, created_at) 
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (url, caption, creator_username, actual_collection_name, "processed"))
        reel_id = cursor.lastrowid
        
        # Clean title name up from caption snippet or default ID fallback string
        recipe_name = caption[:40].strip() + "..." if caption else f"Imported Recipe {reel_id}"
        mock_transcript = f"Delicious recipe imported from your saved Instagram collection '{actual_collection_name}'. Caption highlights: {caption}"
        
        cursor.execute(
            "INSERT INTO recipes (reel_id, recipe_name, transcript) VALUES (?, ?, ?)",
            (reel_id, recipe_name, mock_transcript)
        )
        recipe_id = cursor.lastrowid
        
        # Generate essential starter items to make the card component view display perfectly
        cursor.execute("INSERT INTO ingredients (recipe_id, name, category) VALUES (?, ?, ?)", (recipe_id, "Main Element", "special"))
        cursor.execute("INSERT INTO ingredients (recipe_id, name, category) VALUES (?, ?, ?)", (recipe_id, "Pantry Staple", "pantry"))
        processed_count += 1
        
    conn.commit()
    conn.close()
    
    # 5. Kick off vector DB sync if new items were brought in
    if processed_count > 0:
        sync_sqlite_to_vector_db()
        
    return processed_count
def sync_sqlite_to_vector_db():
    """Pipeline component: Syncs raw text transcripts from SQLite to Vector Space."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.id, r.recipe_name, r.transcript, re.caption, re.url 
        FROM recipes r 
        JOIN reels re ON r.reel_id = re.id
    """)
    rows = cursor.fetchall()
    conn.close()

    for recipe_id, name, transcript, caption, url in rows:
        combined_text = f"Recipe: {name}\nTranscript: {transcript}\nCaption: {caption}"
        # Upsert into ChromaDB vector index
        vector_collection.upsert(
            documents=[combined_text],
            metadatas=[{"recipe_name": name, "url": url, "database_id": recipe_id}],
            ids=[str(recipe_id)]
        )
    return len(rows)

def tool_sql_query_executor(sql_query):
    """Agent Tool: Executes safe, read-only analytical queries against SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(sql_query)
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return json.dumps(results)
    except Exception as e:
        return json.dumps({"error": f"Invalid SQL generated by Agent: {str(e)}"})
    finally:
        conn.close()

def tool_semantic_vector_search(semantic_query, n_results=3):
    """Agent Tool: Queries Vector DB using embedding distance matrix for fuzzy extraction."""
    results = vector_collection.query(
        query_texts=[semantic_query],
        n_results=int(n_results)
    )
    
    extracted_context = []
    if results['documents']:
        for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
            extracted_context.append({
                "source_text": doc,
                "recipe_name": metadata["recipe_name"],
                "url": metadata["url"]
            })
    return json.dumps(extracted_context)

def orchestrate_agent_response(user_query):
    """Supervisor Agent: Analyzes runtime intent and dispatches specialized execution paths."""
    
    # Declare advanced micro-tools to the Supervisor Agent
    tools = [
        {
            "type": "function",
            "function": {
                "name": "tool_sql_query_executor",
                "description": "Run read-only database tracking operations. Use ONLY when user asks for exact aggregate counts, list of distinct categories, or structural mappings.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql_query": {
                            "type": "string",
                            "description": "Valid SQLite string. Tables: reels(id, url, status, creator_username), recipes(id, reel_id, recipe_name, transcript), ingredients(id, recipe_id, name, category)."
                        }
                    },
                    "required": ["sql_query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "tool_semantic_vector_search",
                "description": "Fuzzy query matching tool. Use when user asks based on flavor profiles, leftovers, mood, duration, styles, or missing items.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "semantic_query": {
                            "type": "string",
                            "description": "Fuzzy raw string highlighting ingredients or concepts, e.g., 'high protein quick meal with garlic'"
                        },
                        "n_results": {"type": "integer", "default": 3}
                    },
                    "required": ["semantic_query"]
                }
            }
        }
    ]

    messages = [
        {
            "role": "system",
            "content": (
                "You are an Advanced AI Agent Orchestrator. Break down queries dynamically. "
                "If the data needs precise count metrics, compile structural SQLite queries. "
                "If the query focuses on ingredients or culinary styles, dispatch Vector Searches."
            )
        },
        {"role": "user", "content": user_query}
    ]

    # Step 1: LLM Tool Routing Decision Execution
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.1
    )
    
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    # Step 2: Intermediate Multi-Tool Execution Processing
    if tool_calls:
        available_tools = {
            "tool_sql_query_executor": tool_sql_query_executor,
            "tool_semantic_vector_search": tool_semantic_vector_search
        }
        
        messages.append(response_message)
        
        for call in tool_calls:
            function_name = call.function.name
            tool_function = available_tools[function_name]
            arguments = json.loads(call.function.arguments)
            
            # Execute selected backend tool
            tool_result = tool_function(**arguments)
            
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "name": function_name,
                "content": tool_result
            })
        
        # Step 3: Synthesis Generation
        final_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3
        )
        return final_response.choices[0].message.content
        
    return response_message.content