#@cantarellabots
# Global storage for URLs per user
current_urls = {}
user_episodes = {} # user_id -> {'anime_title': title, 'episodes': [...], 'url': url}
user_search_results = {} # user_id -> search_results

# ── Ongoing auto-download toggle ──
# Note: ongoing_enabled state is now managed via database: `await db.get_user_setting(0, "ongoing_enabled", False)`
