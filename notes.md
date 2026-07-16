## Session — [02-06-2026]

### What I finished:
- ingest.py — all 6 parsing functions working
- 77 reels parsed from Cook collection
- URL, caption, hashtags, creator extracted

### Where I stopped:
- parse_all_reels() done and tested

### Next step:
- Build init_db() — create SQLite database and tables
- Build save_to_db() — insert parsed reels into DB

### Questions I have:
- How to fix emoji encoding issue in captions

## Session — [15-06-2026]

### What I finished:
- init_db() — 3 tables created
- save_reels_to_db() — 77 reels inserted
- Database verified, all data clean

### Next step:
- Phase 3 — LLM extraction agent
- Set up Groq API key
- Write extract.py — send caption to LLM, get back recipe name + ingredients

### Questions:
- How to structure the prompt for ingredient extraction?