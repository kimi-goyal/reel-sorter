// frontend/src/App.jsx
import React, { useEffect, useState } from 'react';

const API_BASE = "http://localhost:8000/api";

export default function App() {
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedChapter, setSelectedChapter] = useState('All');

  const fetchRecipes = async () => {
    try {
      const res = await fetch(`${API_BASE}/recipes`);
      const data = await res.json();
      setRecipes(data);
      setLoading(false);
    } catch (err) {
      console.error("Error loading recipes:", err);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecipes();
  }, []);

  const handleStatusChange = async (recipeId, approvedVal) => {
    try {
      const res = await fetch(`${API_BASE}/recipes/${recipeId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved: approvedVal })
      });
      if (res.ok) {
        // Optimistic locally updated state
        setRecipes(recipes.filter(r => r.id !== recipeId || approvedVal !== 0));
        fetchRecipes();
      }
    } catch (err) {
      console.error("Error updating recipe state:", err);
    }
  };

  // Compile chapters based on dynamic occurrence count of Special Ingredients
  const getChapters = () => {
    const counts = {};
    recipes.forEach(r => {
      r.special_ingredients?.forEach(ing => {
        counts[ing] = (counts[ing] || 0) + 1;
      });
    });
    
    // Pick ingredients that repeat the most (e.g. top 6 ingredients are key Chapters)
    const sortedIngs = Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .map(([name]) => name);

    return ['All', ...sortedIngs.slice(0, 7)];
  };

  const filteredRecipes = selectedChapter === 'All'
    ? recipes
    : recipes.filter(r => r.special_ingredients?.some(ing => ing.toLowerCase() === selectedChapter.toLowerCase()));

  return (
    <div className="min-h-screen bg-amber-50 text-stone-800 font-sans">
      <header className="bg-amber-800 text-amber-50 shadow-md py-6 px-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-serif font-bold tracking-tight">🍂 Digital Heritage Cookbook</h1>
          <p className="text-sm text-amber-200 mt-1">AI-Parsed recipe intelligence from your Instagram saved reels</p>
        </div>
        <div className="text-xs text-amber-100 bg-amber-900/40 py-1 px-3 rounded-full font-mono">
          Total Recipes: {recipes.length}
        </div>
      </header>

      {/* Chapters Navigation */}
      <div className="bg-amber-100/60 border-b border-amber-200 py-4 px-8 overflow-x-auto whitespace-nowrap flex gap-2">
        {getChapters().map(chapter => (
          <button
            key={chapter}
            onClick={() => setSelectedChapter(chapter)}
            className={`px-4 py-1.5 rounded-full text-sm font-semibold capitalize transition-all duration-200 ${
              selectedChapter === chapter
                ? 'bg-amber-800 text-amber-50 shadow-sm scale-105'
                : 'bg-white hover:bg-amber-200/50 border border-amber-200 text-amber-950'
            }`}
          >
            {chapter === 'All' ? '📂 All Recipes' : `✨ ${chapter}`}
          </button>
        ))}
      </div>

      <main className="max-w-7xl mx-auto py-8 px-6">
        {loading ? (
          <div className="text-center py-16 text-amber-900 font-medium">Fetching recipe library...</div>
        ) : filteredRecipes.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-xl border border-dashed border-amber-200">
            <h3 className="text-lg font-serif font-semibold text-stone-600">No recipes found under this chapter.</h3>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {filteredRecipes.map(recipe => (
              <div key={recipe.id} className="bg-white rounded-2xl border border-amber-100 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between overflow-hidden">
                <div className="p-6">
                  <div className="flex justify-between items-start gap-4 mb-4">
                    <h2 className="text-xl font-serif font-bold text-amber-950 capitalize leading-tight">
                      {recipe.recipe_name || "Extracted Recipe"}
                    </h2>
                    <a
                      href={recipe.reel_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-amber-700 bg-amber-100 hover:bg-amber-200 font-semibold py-1 px-3.5 rounded-full transition-colors flex items-center shrink-0"
                    >
                      🔗 Watch Reel
                    </a>
                  </div>

                  {recipe.transcript && (
                    <div className="bg-stone-50 p-3 rounded-xl text-xs text-stone-600 italic line-clamp-3 mb-4 border border-stone-100">
                      "{recipe.transcript}"
                    </div>
                  )}

                  {/* Special Ingredients */}
                  <div className="mb-4">
                    <span className="text-[11px] uppercase tracking-wider font-bold text-amber-800 block mb-1.5">Special Ingredients</span>
                    <div className="flex flex-wrap gap-1.5">
                      {recipe.special_ingredients?.map(ing => (
                        <span key={ing} className="text-xs bg-red-50 text-red-700 border border-red-100/70 font-semibold px-2 py-0.5 rounded capitalize">
                          {ing}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Common Base */}
                  <div>
                    <span className="text-[11px] uppercase tracking-wider font-bold text-stone-400 block mb-1.5">Pantry Staples</span>
                    <div className="flex flex-wrap gap-1.5">
                      {recipe.common_ingredients?.map(ing => (
                        <span key={ing} className="text-xs bg-stone-100 text-stone-600 px-2 py-0.5 rounded capitalize">
                          {ing}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="bg-stone-50/55 px-6 py-4 border-t border-stone-100 flex gap-2 justify-end">
                  {recipe.approved !== 1 && (
                    <button
                      onClick={() => handleStatusChange(recipe.id, 1)}
                      className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold py-2 px-4 rounded-xl shadow-sm transition-colors"
                    >
                      ✓ Approve
                    </button>
                  )}
                  <button
                    onClick={() => handleStatusChange(recipe.id, 0)}
                    className="bg-stone-200 hover:bg-rose-500 hover:text-white text-stone-700 text-xs font-semibold py-2 px-4 rounded-xl transition-all"
                  >
                    🗑️ Skip / Dismiss
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}