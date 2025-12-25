import os
import json
import time
import threading
from imdb import Cinemagoer
import re
import urllib.request
import datetime

class CacheManager:
    def __init__(self, cache_file="movie_cache.json"):
        self.cache_file = cache_file
        self.movie_map = {} # Title -> {year, id, kind}
        self.ia = Cinemagoer()
        self.lock = threading.Lock()
        self.loaded = False
        self.ready_event = threading.Event()
        
        self.load_cache()

    def load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.movie_map = json.load(f)
                self.loaded = True
                self.ready_event.set() # Ready immediately if we have data
                print(f"DEBUG: Loaded {len(self.movie_map)} movies from local cache.")
            except Exception as e:
                print(f"Error loading cache: {e}")
                self.movie_map = {}
        # If cache doesn't exist, we are NOT ready until population finishes.

    def wait_until_ready(self, timeout=None):
        """Blocks until cache is loaded or populated."""
        return self.ready_event.wait(timeout)

    def save_cache(self):
        with self.lock:
            try:
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(self.movie_map, f, indent=2)
            except Exception as e:
                print(f"Error saving cache: {e}")

    def populate_cache(self):
    def populate_cache(self):
        """Fetches Top 250 Movies, Popular Movies, Top 250 TV Shows, and Top 1000 Softbreak."""
        # User requested update on every launch.
        # We still set ready if loaded so we don't block the UI, but we proceed to fetch.
        if self.loaded:
             print("DEBUG: Cache loaded. Starting background refresh of data...")
        else:
             print("DEBUG: Cache empty. Populating...")
        
        # Ensure we don't block if we already have data
        if self.loaded:
            self.ready_event.set()

        print("DEBUG: Populating local cache (Movies + TV)...")
        
        # Explicit save function
        def safe_add(fetch_func, source_name, is_fallback=False, is_tv_fallback=False, is_softbreak=False):
            try:
                print(f"DEBUG: Fetching {source_name}...")
                items = fetch_func()
                if items:
                    if is_softbreak:
                        self._add_top1000_items(items)
                    elif is_fallback:
                        if is_tv_fallback:
                            self._add_fallback_tv_items(items)
                        else:
                            self._add_fallback_items(items)
                    else:
                        self._add_items(items)
                    print(f"DEBUG: Added {len(items)} items from {source_name}.")
                    self.save_cache()
                else:
                    print(f"WARNING: {source_name} returned no items.")
                    return False # Indicate failure
            except Exception as e:
                print(f"Error fetching {source_name}: {e}")
                return False
            return True

        # 1. Top 250 Movies (Try Official, Fallback to JSON)
        if not safe_add(self.ia.get_top250_movies, "Top 250 Movies (IMDbPY)"):
            print("DEBUG: Official Top 250 failed. Trying Fallback JSON...")
            safe_add(self._fetch_fallback_top250, "Top 250 Movies (GitHub JSON)", is_fallback=True)
        
        # 2. Popular Movies
        if hasattr(self.ia, 'get_popular100_movies'):
            safe_add(self.ia.get_popular100_movies, "Popular 100 Movies")

        if not safe_add(self.ia.get_top250_tv, "Top 250 TV Shows"):
             print("DEBUG: Official Top 250 TV failed. Trying Fallback JSON...")
             # Note: This fallback is actually "Popular 50", but it's better than empty.
             safe_add(self._fetch_fallback_pop_tv, "Top 50 Popular TV (GitHub JSON)", is_fallback=True, is_tv_fallback=True)
        
        # 4. Popular TV
        if hasattr(self.ia, 'get_popular100_tv'):
            safe_add(self.ia.get_popular100_tv, "Popular 100 TV Shows")

        self.ready_event.set()
        print(f"DEBUG: Cache initialization complete. {len(self.movie_map)} total titles cached.")

    def _fetch_fallback_top250(self):
        """Downloads raw JSON from GitHub as fallback."""
        url = "https://raw.githubusercontent.com/movie-monk-b0t/top250/master/top250.json"
        try:
            with urllib.request.urlopen(url) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    return data
        except Exception as e:
            print(f"Fallback fetch failed: {e}")
        return []

    def _add_fallback_items(self, items):
        """Parses the specific JSON structure of the fallback source."""
        with self.lock:
            for item in items:
                # Format: {"name": "The Godfather", "datePublished": "1972-03-24", "url": "/title/tt0068646/", "@type": "Movie"}
                title = item.get('name')
                
                # Parse Year
                year = None
                dp = item.get('datePublished')
                if dp:
                    try:
                        year = dp.split('-')[0]
                    except: pass
                
                # Parse ID
                mid = None
                url = item.get('url') # /title/tt0068646/
                if url:
                    match = re.search(r'tt(\d+)', url)
                    if match:
                        mid = match.group(1)
                
                kind = 'movie'
                if item.get('@type') == 'TVSeries': kind = 'tv series'
                
                if title and mid:
                    self._add_single_entry(title, year, mid, kind)

    def _fetch_fallback_pop_tv(self):
        """Downloads Top 50 TV Shows raw JSON from GitHub as fallback."""
        url = "https://raw.githubusercontent.com/crazyuploader/IMDb_Top_50/main/data/top50/shows.json"
        try:
            with urllib.request.urlopen(url) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    return data
        except Exception as e:
            print(f"Fallback TV fetch failed: {e}")
        return []

    def _add_fallback_tv_items(self, items):
        """Parses the specific JSON structure of the crazyuploader source."""
        # Format: {"Show Name": "The Last of Us", "Link": "https://www.imdb.com/title/tt3581920/"}
        with self.lock:
            for item in items:
                title = item.get('Show Name')
                link = item.get('Link')
                
                mid = None
                if link:
                    match = re.search(r'tt(\d+)', link)
                    if match:
                        mid = match.group(1)
                
                if title and mid:
                    # We don't have year, but better than nothing.
                    self._add_single_entry(title, None, mid, "tv series")

    def _fetch_top1000_movies(self):
        """Downloads Softbreak Top 1000 Movies raw JSON."""
        url = "https://raw.githubusercontent.com/softbreak/IMDB-Top-1000-Json/main/movies.json"
        try:
            with urllib.request.urlopen(url) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    return data
        except Exception as e:
             print(f"Top 1000 fetch failed: {e}")
        return []

    def _add_top1000_items(self, items):
        """Parses the Softbreak JSON structure."""
        # Format: {"Id": 243, "Title": "Inception", "Year": 2010, ...}
        with self.lock:
            for item in items:
                title = item.get('Title')
                year = item.get('Year')
                rank_id = item.get('Id')
                
                # We don't have a real IMDb ID, so we use a placeholder.
                # This is sufficient for offline renaming but won't support deep metadata lookups.
                mid = f"sb_{rank_id}" if rank_id else None
                
                if title:
                   # Use 'movie' kind as default for this list
                   self._add_single_entry(title, year, mid, "movie")

    def _add_items(self, items):
        """Parses IMDbPY objects."""
        with self.lock:
            for m in items:
                title = m.get('title')
                year = m.get('year')
                kind = m.get('kind')
                mid = m.movieID
                
                if title:
                    self._add_single_entry(title, year, mid, kind)
    
    def _add_single_entry(self, title, year, mid, kind):
        key = self._normalize(title)
        if key not in self.movie_map:
             self.movie_map[key] = []
        
        entry = {
            'title': title,
            'year': year,
            'id': mid,
            'kind': kind or 'unknown'
        }
        
        # Dup check
        exists = False
        for existing in self.movie_map[key]:
            if existing.get('id') == mid:
                exists = True
                break
        
        if not exists:
            self.movie_map[key].append(entry)

    def _normalize(self, title):
        # Remove punctuation, extra spaces, lower case
        clean = str(title).strip().lower()
        clean = re.sub(r'[^\w\s]', '', clean)
        clean = re.sub(r'\s+', ' ', clean)
        return clean
    
    # ... (search and add_to_cache remain) ...

    def search(self, title, year=None, kind_filter=None):
        """Local search. Returns list of Cinemagoer-like Movie objects."""
        if not title: return None
        
        key = self._normalize(title)
        candidates = self.movie_map.get(key)
        
        if not candidates:
             return None
             
        best_match = None
        
        # Filter logic
        filtered = []
        for c in candidates:
            # Type Filter
            if kind_filter:
                c_kind = c.get('kind', '')
                if kind_filter == 'movie' and c_kind not in ['movie', 'tv movie', 'video movie']:
                    continue
                if kind_filter == 'episode' and c_kind not in ['tv series', 'tv mini series']:
                     # Note: We cache SHOWS, but incoming guess is 'episode'
                     # So we want to match the Show Title
                     pass
            
            # Year Filter (Soft)
            score = 0
            if year and c.get('year'):
                try:
                    diff = abs(int(c['year']) - int(year))
                    if diff == 0: score = 10
                    elif diff == 1: score = 8
                    elif diff <= 2: score = 5
                    else: score = 1
                except: pass
            else:
                score = 5 # No year provided, neutral match
            
            filtered.append((score, c))
            
        filtered.sort(key=lambda x: x[0], reverse=True)
        
        if not filtered:
            return None
            
        # Return top matches converted to Objects
        results = []
        for score, data in filtered[:3]:
             from imdb.Movie import Movie
             m = Movie(_movieID=data['id'], isSameTitle=True)
             m['title'] = data['title']
             if data['year']: m['year'] = data['year']
             if data['kind']: m['kind'] = data['kind']
             results.append(m)
             
        return results

    def add_to_cache(self, movie_obj):
        """Adds a single Cinemagoer Movie object to the local cache and saves."""
        if not movie_obj: return
        
        title = movie_obj.get('title')
        mid = movie_obj.movieID
        year = movie_obj.get('year')
        kind = movie_obj.get('kind', 'unknown')
        
        if not title or not mid: return
        
        # We need to map kind properly if it's missing or vague
        # If adding from a TV find, let's trust it
        
        key = self._normalize(title)
        
        with self.lock:
            if key not in self.movie_map:
                self.movie_map[key] = []
                
            entry = {
                'title': title,
                'year': year,
                'id': mid,
                'kind': kind
            }
            
            # Check dup
            exists = False
            for existing in self.movie_map[key]:
                if existing.get('id') == mid:
                    exists = True
                    break
            
            if not exists:
                self.movie_map[key].append(entry)
                # print(f"DEBUG: Learnt new title: '{title}' ({year})")
                self.save_cache()
