# scripts/kitchen_agent.py
import os
import sqlite3
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.path.join(os.path.dirname(__file__), "../data/recipes.db")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def sql_search_ingredients(ingredients_list):
    """Tool: Searches the SQLite database for recipes containing specific items."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Simple placeholder matching for demonstration
    placeholders = ', '.join(['?'] * len(ingredients_list))
    query = f"""
        SELECT r.recipe_name, re.url, GROUP_CONCAT(i.name)
        FROM recipes r
        JOIN reels re ON r.reel_id = re.id
        JOIN ingredients i ON r.id = i.recipe_id
        WHERE r.id IN (
            SELECT recipe_id FROM ingredients 
            WHERE name IN ({placeholders}) AND category = 'special'
        )
        GROUP BY r.id
    """
    cursor.execute(query, ingredients_list)
    results = cursor.fetchall()
    conn.close()
    
    formatted = []
    for name, url, ings in results:
        formatted.append({"recipe": name, "url": url, "all_ingredients": ings.split(",")})
    return json.dumps(formatted)

def run_kitchen_agent(user_prompt):
    # 1. Define the tools available to our Agent
    tools = [{
        "type": "function",
        "function": {
            "name": "sql_search_ingredients",
            "description": "Finds saved recipes that strictly contain specific unique key ingredients.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ingredients_list": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of special ingredients to search for, e.g., ['chicken', 'paneer']"
                    }
                },
                "required": ["ingredients_list"],
            },
        },
    }]

    # 2. Let the LLM decide which tool to use
    messages = [
        {"role": "system", "content": "You are an intelligent kitchen assistant. Use tools to check the user's saved cookbook database before responding."},
        {"role": "user", "content": user_prompt}
    ]
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    # 3. If the Agent decided to call a tool, execute it
    if tool_calls:
        available_functions = {"sql_search_ingredients": sql_search_ingredients}
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)
            
            # Execute tool
            tool_output = function_to_call(ingredients_list=function_args.get("ingredients_list"))
            
            # Send the tool output context back to the LLM to get a final natural answer
            messages.append(response_message)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": tool_output,
            })
            
            final_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages
            )
            return final_response.choices[0].message.content

    return response_message.content

if __name__ == "__main__":
    # Test the Agentic flow locally!
    user_query = "I have chicken and heavy cream sitting in my fridge. What can I cook from my saved reels?"
    print(f"Thinking Agent Query: '{user_query}'\n")
    print(run_kitchen_agent(user_query))