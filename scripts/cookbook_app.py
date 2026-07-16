# scripts/cookbook_app.py
import os
import sqlite3
import streamlit as st
from ai_engine import sync_sqlite_to_vector_db, orchestrate_agent_response

# 1. Page Configuration & Aesthetic Style Injection
st.set_page_config(
    page_title="My Digital Intelligent Cookbook", 
    page_icon="🍳", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom minimal styling to mimic clean card components
st.markdown("""
<style>
    .recipe-card {
        background-color: #f9f9fb;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #eef0f5;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        margin-bottom: 20px;
        transition: transform 0.2s ease;
    }
    .recipe-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.05);
    }
    .card-title {
        color: #1e293b;
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 8px;
    }
    .reel-btn {
        display: inline-block;
        background-color: #ff4b4b;
        color: white !important;
        padding: 6px 14px;
        border-radius: 20px;
        text-decoration: none;
        font-size: 0.85rem;
        font-weight: 500;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

DB_PATH = os.path.join(os.path.dirname(__file__), "../data/recipes.db")

@st.cache_data(ttl=60)
def load_database_records():
    """Fetch recipes, ingredients, and matching reels from the database."""
    if not os.path.exists(DB_PATH):
        return []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT r.id, r.recipe_name, re.url, i.name, i.category
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

# 2. Main App Header
st.title("🍳 My Smart Digital Cookbook")
st.markdown("Welcome! Search recipes with AI, browse your collection via cards, or plan your weekly grocery runs.")

# 3. Sidebar Controls (Simplified)
with st.sidebar:
    st.header("⚙️ Cookbook Settings")
    st.write("Added new recipes to your library files? Keep the search engine updated here.")
    
    if st.button("🔄 Refresh Search Engine", use_container_width=True):
        with st.spinner("Updating smart search data..."):
            try:
                count = sync_sqlite_to_vector_db()
                st.success(f"Successfully refreshed {count} recipes!")
                st.rerun()
            except Exception as e:
                st.error(f"Could not refresh: {str(e)}")
                
    st.divider()
    st.markdown("💡 **Pro-Tip:** In the AI Assistant tab, try asking: *'Give me something spicy and tell me what special ingredients I need to buy!'*")

# 4. Data Conversion Layer
raw_data = load_database_records()

if not raw_data:
    st.warning("⚠️ Your recipe book is currently empty.")
    st.info("Please import your recipe files or use the synchronization button to get started.")
else:
    # Process Relational Mappings safely
    recipes = {}
    for recipe_id, recipe_name, url, ing_name, category in raw_data:
        ing_name_clean = ing_name.lower().strip()
        
        if recipe_id not in recipes:
            recipes[recipe_id] = {
                "name": recipe_name,
                "url": url,
                "ingredients": []
            }
        recipes[recipe_id]["ingredients"].append((ing_name_clean, category))

    # 5. Application Tab Routing Workspace Layout
    tab_agent, tab_cookbook, tab_planner = st.tabs([
        "🤖 Chat Assistant", 
        "📖 Browse Recipe Cards", 
        "🛒 Grocery Shopping Planner"
    ])

    # === TAB 1: USER FRIENDLY CHAT ASSISTANT ===
    with tab_agent:
        st.subheader("💬 Ask Your Smart Assistant")
        st.write("Type what you're craving or what ingredients you have left in the fridge. The assistant will find matching recipes and link you directly to their video reels.")
        
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # Display historical message context state logs
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Capture dynamic real-time query parameters
        if user_input := st.chat_input("What are we cooking today? (e.g. Show me a high-protein dinner idea)"):
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)
                
            with st.chat_message("assistant"):
                with st.spinner("Checking your recipe collection..."):
                    try:
                        # Append systemic instruction ensuring the engine includes links naturally
                        enhanced_prompt = f"{user_input} (Note: If you mention any specific recipes, make sure to explicitly provide their corresponding link or video URL so I can watch them!)"
                        agent_reply = orchestrate_agent_response(enhanced_prompt)
                        st.markdown(agent_reply)
                        st.session_state.chat_history.append({"role": "assistant", "content": agent_reply})
                    except Exception as e:
                        st.error(f"Something went wrong processing your request. Let's try again!")

    # === TAB 2: VISUAL RECIPE CARDS GRID ===
    with tab_cookbook:
        st.subheader("Your Recipe Collection")
        st.write("Click on any recipe card below to instantly unfold the full ingredient breakdowns.")
        
        # Turn dictionary items into a list for simple grid slicing
        recipe_list = list(recipes.values())
        
        # Create a responsive columns grid (3 columns wide)
        for i in range(0, len(recipe_list), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(recipe_list):
                    recipe = recipe_list[i + j]
                    with cols[j]:
                        # Wrap the header layout inside a stylish HTML Card block
                        st.markdown(f"""
                        <div class="recipe-card">
                            <div class="card-title">🍲 {recipe['name']}</div>
                            <span style="font-size: 0.85rem; color:#64748b;">Includes {len(recipe['ingredients'])} total ingredients</span><br>
                            <a href="{recipe['url']}" target="_blank" class="reel-btn">📸 Watch Reel Video</a>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Interactive expansion slot for ingredient details directly underneath card
                        with st.expander("🔍 View Full Ingredients List"):
                            specials = [ing.capitalize() for ing, cat in recipe['ingredients'] if cat == 'special']
                            commons = [ing.capitalize() for ing, cat in recipe['ingredients'] if cat != 'special']
                            
                            if specials:
                                st.markdown("**🛒 Special items needed:**")
                                for item in specials:
                                    st.markdown(f"- {item}")
                            if commons:
                                st.markdown("**🧂 Standard pantry staples:**")
                                for item in commons:
                                    st.markdown(f"- {item}")
            st.write("") # Margin buffer between rows

    # === TAB 3: GROCERY PLANNER ===
    with tab_planner:
        st.subheader("Weekly Grocery Planner")
        st.write("Pick the recipes you want to prepare this week, and we'll automatically organize your shopping list into an easy checklist.")

        recipe_options = {details["name"]: r_id for r_id, details in recipes.items()}
        selected_recipe_names = st.multiselect("Which meals are you planning to make?", list(recipe_options.keys()))

        if selected_recipe_names:
            selected_ids = [recipe_options[name] for name in selected_recipe_names]
            
            st.markdown("#### 🔗 Quick Reference Links")
            for r_id in selected_ids:
                st.markdown(f"- **[{recipes[r_id]['name']}]({recipes[r_id]['url']})**")

            needed_special = set()
            needed_common = set()

            for r_id in selected_ids:
                for ing, cat in recipes[r_id]["ingredients"]:
                    if cat == 'special':
                        needed_special.add(ing)
                    else:
                        needed_common.add(ing)

            st.divider()
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🛒 Checklist: Items to Buy")
                st.caption("Grab these specialty ingredients at the grocery store:")
                for item in sorted(needed_special):
                    st.checkbox(item.capitalize(), key=f"shopping_{item}")

            with col2:
                st.markdown("### 🧂 Household Pantry Staples")
                st.caption("Double check you already have these standard items at home:")
                for item in sorted(needed_common):
                    st.write(f"✓ {item.capitalize()}")