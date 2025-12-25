from src.cache_manager import CacheManager
import logging
import sys

# Configure logging to stdout
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

print("--- Starting Cache Top 1000 Debug ---")

try:
    cm = CacheManager()
    print(f"Cache Initialized. Loaded: {cm.loaded}. Items: {len(cm.movie_map)}")
    
    print("Testing _fetch_top1000_movies explicitly...")
    data = cm._fetch_top1000_movies()
    print(f"Fetch returned: {len(data)} items.")
    
    if len(data) > 0:
        print("First item sample:", data[0])
        print("Testing _add_top1000_items...")
        before_count = len(cm.movie_map)
        cm._add_top1000_items(data)
        after_count = len(cm.movie_map)
        print(f"Added {after_count - before_count} new items. Total: {after_count}")
        cm.save_cache()
        print("Saved.")
    else:
        print("FAILURE: Fetch returned 0 items.")

except Exception as e:
    print(f"CRITICAL FAILIURE: {e}")
    import traceback
    traceback.print_exc()
