
import os
import sqlite3
import streamlit as st
from ai_engine import (
    sync_sqlite_to_vector_db,
    orchestrate_agent_response,
    ingest_user_instagram_collection
)

st.set_page_config(
    page_title="Recipe Box",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

<style>
    /* ── Reset & Base ── */
    .stApp {
        background-color: #0F0F0F !important;
        color: #F5F0E8 !important;
    }
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 4rem !important;
        max-width: 1200px !important;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background-color: #0F0F0F !important;
        border-right: 1px solid #2A2A2F !important;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem !important;
    }

    /* ── Page Header ── */
    .page-header {
        margin-bottom: 3rem;
        padding-bottom: 1.5rem;
        border-bottom: 1px solid #2A2A2F;
    }
    .page-title {
        font-family: 'Playfair Display', serif;
        font-size: 2.8rem;
        font-weight: 700;
        color: #F5F0E8;
        line-height: 1.1;
        margin: 0;
    }
    .page-title span {
        color: #C8A96E;
    }
    .page-subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 0.9rem;
        color: #6B7280;
        margin-top: 0.5rem;
        font-weight: 300;
        letter-spacing: 0.02em;
    }

    /* ── Stats Bar ── */
    .stats-bar {
        display: flex;
        gap: 2rem;
        margin-bottom: 2.5rem;
        padding: 1rem 1.5rem;
        background: #1C1C1F;
        border: 1px solid #2A2A2F;
        border-radius: 2px;
    }
    .stat-item {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    .stat-number {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.4rem;
        font-weight: 500;
        color: #C8A96E;
    }
    .stat-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.7rem;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* ── Chapter Divider ── */
    .chapter-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin: 3rem 0 1.5rem 0;
        padding-left: 1rem;
        border-left: 3px solid #C8A96E;
    }
    .chapter-name {
        font-family: 'Playfair Display', serif;
        font-size: 1.5rem;
        font-weight: 600;
        color: #F5F0E8;
        text-transform: capitalize;
    }
    .chapter-count {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: #6B7280;
        padding: 2px 8px;
        border: 1px solid #2A2A2F;
        border-radius: 2px;
    }

    /* ── Recipe Card ── */
    .recipe-card {
        background: #1C1C1F;
        border: 1px solid #2A2A2F;
        border-radius: 2px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: border-color 0.2s ease;
        height: 100%;
    }
    .recipe-card:hover {
        border-color: #C8A96E;
    }
    .recipe-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.1rem;
        font-weight: 600;
        color: #F5F0E8;
        line-height: 1.3;
        margin-bottom: 0.75rem;
    }
    .recipe-creator {
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        color: #6B7280;
        margin-bottom: 1rem;
        font-weight: 300;
    }
    .reel-link {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-family: 'Inter', sans-serif;
        font-size: 0.8rem;
        font-weight: 500;
        color: #E85D4A !important;
        text-decoration: none;
        letter-spacing: 0.02em;
    }
    .reel-link:hover {
        color: #C8A96E !important;
    }

    /* ── Ingredient Pills ── */
    .ingredients-section {
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid #2A2A2F;
    }
    .ingredient-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 0.4rem;
    }
    .label-special { color: #C8A96E; }
    .label-common  { color: #6B7280; }

    .pills-row {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-bottom: 0.75rem;
    }
    .pill-special {
        font-family: 'Inter', sans-serif;
        font-size: 0.72rem;
        color: #F5F0E8;
        background: #2A2A2F;
        border: 1px solid #C8A96E33;
        padding: 3px 10px;
        border-radius: 20px;
    }
    .pill-common {
        font-family: 'Inter', sans-serif;
        font-size: 0.72rem;
        color: #6B7280;
        background: #1C1C1F;
        border: 1px solid #2A2A2F;
        padding: 3px 10px;
        border-radius: 20px;
    }

    /* ── Sidebar Chapter Nav ── */
    .sidebar-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.1rem;
        color: #F5F0E8;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #2A2A2F;
    }
    
    /* Target unique styling injection for native stream buttons inside the sidebar navigation */
    div[data-testid="stSidebar"] div.stButton > button {
        width: 100% !important;
        text-align: left !important;
        justify-content: flex-start !important;
        border: none !important;
        padding: 6px 0px !important;
        color: #6B7280 !important;
        text-transform: capitalize !important;
    }
    div[data-testid="stSidebar"] div.stButton > button:hover {
        color: #C8A96E !important;
        background: transparent !important;
    }

    /* ── Tabs ── */
    button[data-baseweb="tab"] {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.85rem !important;
        color: #6B7280 !important;
        letter-spacing: 0.03em !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #C8A96E !important;
        border-bottom-color: #C8A96E !important;
    }

    /* ── Chat ── */
    .stChatMessage {
        background: #1C1C1F !important;
        border: 1px solid #2A2A2F !important;
        border-radius: 2px !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        border-radius: 2px !important;
        border: 1px solid #2A2A2F !important;
        background: transparent !important;
        color: #6B7280 !important;
        letter-spacing: 0.03em !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        border-color: #C8A96E !important;
        color: #C8A96E !important;
    }

    /* ── Grocery Planner ── */
    .planner-panel {
        background: #1C1C1F;
        border: 1px solid #2A2A2F;
        border-radius: 2px;
        padding: 1.5rem;
        min-height: 300px;
    }
    .planner-section-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.3rem;
        color: #F5F0E8;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #2A2A2F;
    }
    .buy-item {
        font-family: 'Inter', sans-serif;
        font-size: 0.85rem;
        color: #F5F0E8;
        padding: 6px 0;
        border-bottom: 1px solid #2A2A2F22;
        text-transform: capitalize;
    }
    .pantry-item {
        font-family: 'Inter', sans-serif;
        font-size: 0.82rem;
        color: #6B7280;
        padding: 4px 0;
        text-transform: capitalize;
    }

    /* ── Upload Form ── */
    .upload-panel {
        background: #1C1C1F;
        border: 1px solid #2A2A2F;
        border-radius: 2px;
        padding: 1.5rem;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize navigation session state variable if it doesn't exist yet
if "selected_chapter" not in st.session_state:
    st.session_state["selected_chapter"] = "all"

def approve_recipe(recipe_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE recipes SET approved = 1 WHERE id = ?", (recipe_id,))
    conn.commit()
    conn.close()
    st.cache_data.clear()

def skip_recipe(recipe_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE recipes SET approved = 0 WHERE id = ?", (recipe_id,))
    conn.commit()
    conn.close()
    st.cache_data.clear()

# ── DB Path ──────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "../data/recipes.db")

# ── Data Loading ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_database_records():
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT r.id, r.recipe_name, re.url, re.creator_username,
                   i.name, i.category
            FROM recipes r
            JOIN reels re ON r.reel_id = re.id
            JOIN ingredients i ON r.id = i.recipe_id
        """)
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        rows = []
    finally:
        conn.close()
    return rows

# ── Data Processing ───────────────────────────────────────────
raw_data = load_database_records()

recipes = {}
if raw_data:
    for recipe_id, recipe_name, url, creator, ing_name, category in raw_data:
        if recipe_id not in recipes:
            recipes[recipe_id] = {
                "id": recipe_id,
                "name": recipe_name,
                "url": url,
                "creator": creator or "Unknown",
                "special": [],
                "common": []
            }
        if category == "special":
            recipes[recipe_id]["special"].append(ing_name.capitalize())
        else:
            recipes[recipe_id]["common"].append(ing_name.capitalize())

# Build chapters — group by each special ingredient
chapters = {}
for recipe in recipes.values():
    for ing in recipe["special"]:
        key = ing.lower().strip()
        if key not in chapters:
            chapters[key] = []
        if recipe not in chapters[key]:
            chapters[key].append(recipe)

# Sort chapters by recipe count
chapters = dict(sorted(chapters.items(), key=lambda x: len(x[1]), reverse=True))
top_chapters = dict(list(chapters.items())[:15])

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-title">📖 Recipe Box</div>', unsafe_allow_html=True)

    # Stats
    total = len(recipes)
    total_chapters = len(top_chapters)
    st.markdown(f"""
    <div style="margin-bottom:1.5rem;">
        <div style="font-family:JetBrains Mono,monospace; font-size:1.6rem; color:#C8A96E;">{total}</div>
        <div style="font-family:Inter,sans-serif; font-size:0.7rem; color:#6B7280; text-transform:uppercase; letter-spacing:0.08em;">recipes saved</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="font-family:Inter,sans-serif; font-size:0.7rem; color:#6B7280; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.75rem;">Chapters</div>', unsafe_allow_html=True)

    # Reset nav button to let user clear filtering filters easily
    if st.button("✨ Show All Chapters", key="show_all_btn"):
        st.session_state["selected_chapter"] = "all"
        st.rerun()

    for chapter_name, chapter_recipes in top_chapters.items():
        # Render a real native button with labels formatted to show data metrics
        button_label = f"{chapter_name.capitalize()} ({len(chapter_recipes)})"
        if st.button(button_label, key=f"nav_{chapter_name}"):
            st.session_state["selected_chapter"] = chapter_name
            st.rerun()

    st.markdown('<hr style="border-color:#2A2A2F; margin:1.5rem 0;">', unsafe_allow_html=True)

    # Upload section
    st.markdown('<div style="font-family:Inter,sans-serif; font-size:0.7rem; color:#6B7280; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.75rem;">Import Collection</div>', unsafe_allow_html=True)

    with st.form(key="instagram_upload_form"):
        target_col = st.text_input("Collection name", placeholder="e.g. Cook")
        uploaded_file = st.file_uploader("saved_collections.json", type=["json"])
        submit_btn = st.form_submit_button("Import", use_container_width=True)

    if submit_btn:
        if not target_col or not uploaded_file:
            st.error("Fill in both fields.")
        else:
            with st.spinner("Importing..."):
                try:
                    temp_path = "temp_saved_collections.json"
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    count = ingest_user_instagram_collection(temp_path, target_col)
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    st.success(f"{count} recipes imported.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

# ── Main Header ───────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <div class="page-title">Your <span>Recipe</span> Box</div>
    <div class="page-subtitle">Saved from Instagram — organized by what to buy</div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────
tab_cookbook, tab_agent, tab_planner = st.tabs([
    "📖 Cookbook", "🤖 Ask the Box", "🛒 Grocery Planner"
])

# ══════════════════════════════════════════════════════════════
# TAB 1 — COOKBOOK (Chapters View)
# ══════════════════════════════════════════════════════════════
with tab_cookbook:
    if not recipes:
        st.markdown("""
        <div style="text-align:center; padding:4rem 0; color:#6B7280;">
            <div style="font-family:Playfair Display,serif; font-size:1.5rem; margin-bottom:0.5rem;">Nothing here yet</div>
            <div style="font-family:Inter,sans-serif; font-size:0.85rem;">Import your Instagram collection from the sidebar to get started.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Determine the display dataset based on sidebar status filter
        active_filter = st.session_state["selected_chapter"]
        
        # Filter top_chapters dictionary down to just the selected category if needed
        display_chapters = top_chapters
        if active_filter != "all" and active_filter in top_chapters:
            display_chapters = {active_filter: top_chapters[active_filter]}
            
            # Show active badge with option to close filter view
            col_lbl, col_reset = st.columns([6, 1])
            with col_lbl:
                st.markdown(f"📍 *Filtering by chapter:* **{active_filter.upper()}**")
            with col_reset:
                if st.button("Clear Filter ✖", key="clear_inline_filter"):
                    st.session_state["selected_chapter"] = "all"
                    st.rerun()

        for chapter_name, chapter_recipes in display_chapters.items():
            # Chapter header
            st.markdown(f"""
            <div class="chapter-header">
                <div class="chapter-name">{chapter_name}</div>
                <div class="chapter-count">{len(chapter_recipes)} recipes</div>
            </div>
            """, unsafe_allow_html=True)

            # 2-column card grid
            for i in range(0, len(chapter_recipes), 2):
                cols = st.columns(2, gap="medium")
                for j in range(2):
                    if i + j < len(chapter_recipes):
                        r = chapter_recipes[i + j]

                        special_pills = "".join([f'<span class="pill-special">{s}</span>' for s in r["special"][:5]])
                        common_pills  = "".join([f'<span class="pill-common">{c}</span>'  for c in r["common"][:4]])

                        with cols[j]:
                            st.markdown(f"""
                            <div class="recipe-card">
                                <div class="recipe-title">{r["name"]}</div>
                                <div class="recipe-creator">by @{r["creator"]}</div>
                                <a href="{r["url"]}" target="_blank" class="reel-link">▶ Watch reel</a>
                                <div class="ingredients-section">
                                    <div class="ingredient-label label-special">Buy</div>
                                    <div class="pills-row">{special_pills}</div>
                                    <div class="ingredient-label label-common">Pantry</div>
                                    <div class="pills-row">{common_pills}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
# ══════════════════════════════════════════════════════════════
# TAB 2 — ASK THE BOX
# ══════════════════════════════════════════════════════════════
with tab_agent:
    st.markdown("""
    <div style="margin-bottom:1.5rem;">
        <div style="font-family:Playfair Display,serif; font-size:1.8rem; color:#F5F0E8;">Ask the Box</div>
        <div style="font-family:Inter,sans-serif; font-size:0.85rem; color:#6B7280; margin-top:4px;">
            Try: "What can I make with paneer?" or "Show me quick pasta recipes"
        </div>
    </div>
    """, unsafe_allow_html=True)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    chat_container = st.container(height=450)
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if user_input := st.chat_input("What do you want to cook today?"):
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_input)
            with st.chat_message("assistant"):
                status = st.empty()
                status.markdown('<span style="font-family:JetBrains Mono,monospace; font-size:11px; color:#6B7280;">searching your recipe box...</span>', unsafe_allow_html=True)
                try:
                    reply = orchestrate_agent_response(user_input)
                    status.empty()
                    st.markdown(reply)
                    st.session_state.chat_history.append({"role": "assistant", "content": reply})
                except Exception as e:
                    status.empty()
                    st.error("Something went wrong. Try again.")

# ══════════════════════════════════════════════════════════════
# TAB 3 — GROCERY PLANNER
# ══════════════════════════════════════════════════════════════
with tab_planner:
    st.markdown("""
    <div style="font-family:Playfair Display,serif; font-size:1.8rem; color:#F5F0E8; margin-bottom:1.5rem;">
        This Week's Meals
    </div>
    """, unsafe_allow_html=True)

    recipe_options = {r["name"]: r["id"] for r in recipes.values()}
    col_meals, col_list = st.columns([1, 1], gap="large")

    with col_meals:
        st.markdown('<div class="planner-section-title">Pick your recipes</div>', unsafe_allow_html=True)
        selected_names = st.multiselect(
            "Select recipes",
            list(recipe_options.keys()),
            label_visibility="collapsed"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_list:
        st.markdown('<div class="planner-section-title">Shopping list</div>', unsafe_allow_html=True)

        if selected_names:
            selected_ids = [recipe_options[n] for n in selected_names]
            buy = set()
            pantry = set()

            for r_id in selected_ids:
                r = recipes[r_id]
                for ing in r["special"]:
                    buy.add(ing.lower())
                for ing in r["common"]:
                    pantry.add(ing.lower())

            if buy:
                st.markdown('<div style="font-family:JetBrains Mono,monospace; font-size:0.65rem; color:#C8A96E; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.5rem;">Buy</div>', unsafe_allow_html=True)
                for item in sorted(buy):
                    st.checkbox(item.capitalize(), key=f"buy_{item}")

            if pantry:
                st.markdown('<div style="font-family:JetBrains Mono,monospace; font-size:0.65rem; color:#6B7280; text-transform:uppercase; letter-spacing:0.1em; margin:1rem 0 0.5rem 0;">Check pantry</div>', unsafe_allow_html=True)
                for item in sorted(pantry):
                    st.markdown(f'<div class="pantry-item">✓ {item.capitalize()}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-family:Inter,sans-serif; font-size:0.85rem; color:#6B7280; padding-top:0.5rem;">Pick some recipes to build your list.</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)