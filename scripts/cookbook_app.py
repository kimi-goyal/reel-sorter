# scripts/cookbook_app.py
import os
import sqlite3
import streamlit as st
from ai_engine import sync_sqlite_to_vector_db, orchestrate_agent_response

# 1. Page Configuration & Aesthetic Style Injection
st.set_page_config(
    page_title="Reel Recipe Box", 
    page_icon="🍳", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom minimal styling mimicking the premium dark cream UI blocks
st.markdown("""
<style>
    /* Global Background Adjustments */
    .stApp {
        background-color: #121214 !important;
        color: #f4f4f6 !important;
    }
    
    /* Sidebar Overrides */
    section[data-testid="stSidebar"] {
        background-color: #1a1a1e !important;
        border-right: 1px solid #2a2a32;
    }

    /* Premium Index Card Component Design */
    .recipe-card {
        background-color: #1a1a1e;
        padding: 24px;
        border-radius: 4px;
        border: 1px solid #2a2a32;
        margin-bottom: 20px;
        display: flex;
        flex-direction: column;
        gap: 12px;
    }
    
    .card-header-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 12px;
    }
    
    .card-title {
        color: #f4f4f6;
        font-family: serif;
        font-size: 1.35rem;
        font-weight: 600;
        line-height: 1.3;
    }
    
    .card-badge {
        font-family: monospace;
        font-size: 0.75rem;
        color: #8e8e9f;
        white-space: nowrap;
        padding-top: 4px;
    }
    
    /* Links & Accents matching Mustard & Tomato tokens */
    .reel-link {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        color: #ff5a5a !important; /* Tomato token */
        text-decoration: none;
        font-size: 0.8rem;
        font-weight: 500;
        transition: color 0.2s ease;
    }
    .reel-link:hover {
        color: #e5a93b !important; /* Mustard hover token */
    }

    /* Text blocks formatting */
    .section-label-special {
        color: #e5a93b; /* Mustard token */
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
        font-weight: 600;
    }
    
    .section-label-pantry {
        color: #8e8e9f; /* Mute token */
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
        font-weight: 600;
    }

    /* Tabs Styling Overrides */
    button[data-baseweb="tab"] {
        color: #8e8e9f !important;
        font-size: 0.9rem !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #e5a93b !important;
        border-bottom-color: #e5a93b !important;
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
st.markdown('<h1 style="font-family:serif; color:#f4f4f6; font-size: 2.5rem; margin-bottom: 5px;"><span style="color:#e5a93b;">Reel</span> Recipe Box</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#8e8e9f; font-size:0.95rem; margin-bottom:30px;">Search recipes with AI, browse your collection via index cards, or plan your weekly grocery runs.</p>', unsafe_allow_html=True)

# 3. Sidebar Controls
with st.sidebar:
    st.markdown('<h2 style="font-family:serif; color:#f4f4f6; font-size: 1.5rem;">Settings</h2>', unsafe_allow_html=True)
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
    st.warning("⚠️ Your recipe box is currently empty.")
    st.info("Please import your recipe files or use the synchronization button to get started.")
else:
    recipes = {}
    for recipe_id, recipe_name, url, ing_name, category in raw_data:
        ing_name_clean = ing_name.lower().strip()
        
        if recipe_id not in recipes:
            recipes[recipe_id] = {
                "id": recipe_id,
                "name": recipe_name,
                "url": url,
                "ingredients": []
            }
        recipes[recipe_id]["ingredients"].append((ing_name_clean, category))

    # 5. Application Workspace Tab Layout Routing
    tab_agent, tab_cookbook, tab_planner = st.tabs([
        "🤖 Ask the Box", 
        "📖 Recipe Box", 
        "🛒 Grocery Planner"
    ])

    # === TAB 1: CHAT ASSISTANT ===
    with tab_agent:
        st.markdown('<h2 style="font-family:serif; color:#f4f4f6; font-size: 1.8rem; margin-bottom:10px;">Ask the Box</h2>', unsafe_allow_html=True)
        
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # Streamlit container layout matching the chat height parameters
        chat_container = st.container(height=450)
        with chat_container:
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        if user_input := st.chat_input("Something spicy with chicken..."):
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(user_input)
                
                with st.chat_message("assistant"):
                    # Quick custom processing note matching requirements
                    status_placeholder = st.empty()
                    status_placeholder.markdown('<p style="font-family:monospace; font-size:12px; color:#8e8e9f;">checking your recipe box...</p>', unsafe_allow_html=True)
                    
                    try:
                        enhanced_prompt = f"{user_input} (Note: If you mention any specific recipes, make sure to explicitly provide their corresponding link or video URL so I can watch them!)"
                        agent_reply = orchestrate_agent_response(enhanced_prompt)
                        status_placeholder.empty()
                        st.markdown(agent_reply)
                        st.session_state.chat_history.append({"role": "assistant", "content": agent_reply})
                    except Exception as e:
                        status_placeholder.empty()
                        st.error(f"Something went wrong processing your request. Let's try again!")

    # === TAB 2: VISUAL RECIPE CARDS GRID ===
    with tab_cookbook:
        st.markdown('<h2 style="font-family:serif; color:#f4f4f6; font-size: 1.8rem; margin-bottom:15px;">Your Collection</h2>', unsafe_allow_html=True)
        
        recipe_list = list(recipes.values())
        
        # Responsive 2-column card layout workspace matching grid layout aesthetics
        for i in range(0, len(recipe_list), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(recipe_list):
                    recipe = recipe_list[i + j]
                    
                    specials = [ing.capitalize() for ing, cat in recipe['ingredients'] if cat == 'special']
                    commons = [ing.capitalize() for ing, cat in recipe['ingredients'] if cat != 'special']
                    
                    with cols[j]:
                        # Card structure containing precise header fields matching React layout template
                        st.markdown(f"""
                        <div class="recipe-card">
                            <div class="card-header-row">
                                <div class="card-title">{recipe['name']}</div>
                                <div class="card-badge">{len(specials)} special</div>
                            </div>
                            <div>
                                <a href="{recipe['url']}" target="_blank" class="reel-link">Watch the reel &rarr;</a>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Expandable custom text ingredients configuration engine blocks nested contextually
                        with st.expander("Show ingredients"):
                            if specials:
                                st.markdown('<p class="section-label-special">Special</p>', unsafe_allow_html=True)
                                for item in specials:
                                    st.markdown(f"<span style='color:#f4f4f6; font-size:0.9rem;'>• {item}</span>", unsafe_allow_html=True)
                            
                            if commons:
                                st.markdown('<p class="section-label-pantry" style="margin-top:10px;">Pantry Staples</p>', unsafe_allow_html=True)
                                for item in commons:
                                    st.markdown(f"<span style='color:#8e8e9f; font-size:0.9rem;'>• {item}</span>", unsafe_allow_html=True)
                        
                        # Functional interaction state logic buttons
                        col_btn1, col_btn2 = st.columns([1.2, 1])
                        with col_btn1:
                            st.button("Made it & loved it", key=f"love_{recipe['id']}", use_container_width=True)
                        with col_btn2:
                            st.button("Skip", key=f"skip_{recipe['id']}", use_container_width=True)
            st.write("") 

    # === TAB 3: GROCERY PLANNER ===
    with tab_planner:
        col_meals, col_list = st.columns(2)
        
        recipe_options = {details["name"]: r_id for r_id, details in recipes.items()}
        
        with col_meals:
            st.markdown('<h2 style="font-family:serif; color:#f4f4f6; font-size: 1.8rem; margin-bottom:15px;">This week\'s meals</h2>', unsafe_allow_html=True)
            
            # Using an isolated panel block context matching .index-card container styles
            st.markdown('<div style="background-color:#1a1a1e; padding:20px; border-radius:4px; border:1px solid #2a2a32;">', unsafe_allow_html=True)
            selected_recipe_names = st.multiselect("Select your recipes:", list(recipe_options.keys()), label_visibility="collapsed")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_list:
            st.markdown('<h2 style="font-family:serif; color:#f4f4f6; font-size: 1.8rem; margin-bottom:15px;">Shopping list</h2>', unsafe_allow_html=True)
            
            st.markdown('<div style="background-color:#1a1a1e; padding:20px; border-radius:4px; border:1px solid #2a2a32; min-height:150px;">', unsafe_allow_html=True)
            if selected_recipe_names:
                selected_ids = [recipe_options[name] for name in selected_recipe_names]
                
                needed_special = set()
                needed_common = set()

                for r_id in selected_ids:
                    for ing, cat in recipes[r_id]["ingredients"]:
                        if cat == 'special':
                            needed_special.add(ing)
                        else:
                            needed_common.add(ing)

                # Buy Checklist Items Section
                st.markdown('<p class="section-label-special">Buy</p>', unsafe_allow_html=True)
                if not needed_special:
                    st.markdown('<p style="color:#8e8e9f; font-size:0.9rem;">Nothing yet — pick some meals.</p>', unsafe_allow_html=True)
                for item in sorted(needed_special):
                    st.checkbox(item.capitalize(), key=f"plan_buy_{item}")

                # Check Pantry Items Section
                if needed_common:
                    st.markdown('<p class="section-label-pantry" style="margin-top:20px;">Check your pantry</p>', unsafe_allow_html=True)
                    for item in sorted(needed_common):
                        st.markdown(f"<p style='color:#8e8e9f; font-size:0.9rem; margin-bottom:4px;'>✓ {item.capitalize()}</p>", unsafe_allow_html=True)
            else:
                st.markdown('<p style="color:#8e8e9f; font-size:0.9rem;">Nothing yet — pick some meals.</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)