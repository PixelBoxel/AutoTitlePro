import os
from guessit import guessit
from imdb import Cinemagoer
from duckduckgo_search import DDGS
import re
import datetime
import shutil
import threading
import traceback
import json
import time
import urllib.request

# Versioning: Year.Month.Day.Hour
now = datetime.datetime.now()
# Static version for release tracking
__version__ = "v2025.12.25.02"

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

        # 3. Top 250 TV
        if not safe_add(self.ia.get_top250_tv, "Top 250 TV Shows"):
             print("DEBUG: Official Top 250 TV failed. Trying Fallback JSON...")
             # Note: This fallback is actually "Popular 50", but it's better than empty.
             safe_add(self._fetch_fallback_pop_tv, "Top 50 Popular TV (GitHub JSON)", is_fallback=True, is_tv_fallback=True)
        
        # 4. Popular TV
        if hasattr(self.ia, 'get_popular100_tv'):
            safe_add(self.ia.get_popular100_tv, "Popular 100 TV Shows")
            
        # 5. Softbreak Top 1000 Movies (User Requested)
        safe_add(self._fetch_top1000_movies, "Top 1000 Movies (Softbreak)", is_softbreak=True)

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

class AutoRenamer:
    def __init__(self):
        self.ia = Cinemagoer()
        self.cache = CacheManager()
        threading.Thread(target=self.cache.populate_cache, daemon=True).start()

    def scan_directory(self, path, progress_callback=None):
        """Recursively finds video files in the given directory."""
        video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.wmv')
        files = []
        for root, _, filenames in os.walk(path):
            if progress_callback: progress_callback()
            for filename in filenames:
                if filename.lower().endswith(video_extensions):
                    files.append(os.path.join(root, filename))
        return files

    def parse_filename(self, file_path, media_type_hint=None):
        """Uses guessit to extract metadata from the full file path."""
        # guessit is smart enough to handle full paths and extract info from parent folders
        options = {}
        if media_type_hint:
            options['type'] = media_type_hint
            
        guess = guessit(file_path, options=options)
        
        # --- Sanitize Guess (Fix Leading Sort Numbers) ---
        # If guessit returns "01 A Nightmare", we strip the "01 ".
        # We only do this for leading ZEROs to avoid killing "1917" or "10 Cloverfield".
        if 'title' in guess:
            raw_title = guess['title']
            # Regex: Start with '0', digit, then separator (space . - _)
            match = re.match(r"^0\d+[\s\.\-_]+(.+)", raw_title)
            if match:
                clean_title = match.group(1).strip()
                print(f"DEBUG: Stripping sort number from guess: '{raw_title}' -> '{clean_title}'")
                guess['title'] = clean_title
                
        return guess

    def sanitize_title(self, text):
        """
        Aggressively strips common scene tags from a string to get a clean title.
        """
        if not text: return ""
        
        clean = text
        
        # 1. Remove Release Groups (heuristics: "-Group" at end) BEFORE stripping hyphens
        clean = re.sub(r"\-[a-zA-Z0-9]+$", "", clean)
        
        # 2. Replace dots/underscores/dashes with spaces
        clean = re.sub(r"[\.\-_]", " ", clean)
        
        # 3. List of tags to strip. 
        # INCLUDES SPACED VARIANTS because we just replaced separators with spaces.
        tags = [
            r"1080p", r"720p", r"2160p", r"480p", r"4k", r"8k",
            r"bluray", r"blu ray", r"dvd", r"dvdrip", r"dvd rip", 
            r"web", r"web dl", r"web rip", r"webrip", r"webdl",
            r"hdtv", r"remux", r"bdrip", r"brip",
            r"x264", r"x265", r"h264", r"h265", r"h 264", r"h 265", r"hevc", r"avc", r"divx", r"xvid",
            r"aac", r"ac3", r"eac3", r"dts", r"truehd", r"flac", r"mp3", r"ogg", r"wma", 
            r"dd5\.1", r"dd5 1", r"ddp5\.1", r"ddp5 1", r"dd", r"ddp", r"atmos",
            r"5\.1", r"5 1", r"7\.1", r"7 1", r"2\.0", r"2 0",
            r"hdr", r"10bit", r"12bit", 
            r"extended", r"uncut", r"directors cut", r"repack", r"proper",
            r"mp4", r"mkv", r"avi", r"wmv"
        ]
        
        regex = r"\b(" + "|".join(tags) + r")\b"
        clean = re.sub(regex, "", clean, flags=re.IGNORECASE)
        
        # 4. Handle patterns like "AAC5.1" (no boundary) or "DD5.1"
        # CRITICAL FIX: Ensure 'dd' has a boundary start, or is followed by digit
        clean = re.sub(r"\b(aac|ac3|dts|dd|ddp)[\s\.]*\d+", "", clean, flags=re.IGNORECASE)
        
        # 5. Clean up multiple spaces
        clean = re.sub(r"\s+", " ", clean).strip()
        
        return clean

    def fetch_metadata(self, guess, file_path=None, offline_only=False):
        """Queries IMDb via DuckDuckGo + Cinemagoer. Returns list of matches."""
        
        title = guess.get('title')
        year = guess.get('year')
        media_type = guess.get('type')
        
        # ... logic ...
        GENERIC_FOLDERS = {
            "movies", "films", "downloads", "completed", "video", "videos", 
            "tv", "tv shows", "tv series", "plex", "media", "unsorted", "library", "unknown"
        }

        # 1. Sanitize 'guess' title immediately
        if title:
             title = self.sanitize_title(title)
        
        if title and title.strip().lower() in GENERIC_FOLDERS:
            # print(f"DEBUG: 'guessit' returned generic title '{title}'. Discarding.")
            title = None 

        # 2. Fallback: context inference
        if not title and file_path:
            parent_name = os.path.basename(os.path.dirname(file_path))
            clean_parent = parent_name.strip().lower()
            
            if clean_parent in GENERIC_FOLDERS:
                # print(f"DEBUG: Generic parent '{parent_name}'. Trying raw filename.")
                # Try raw filename
                filename_base = os.path.splitext(os.path.basename(file_path))[0]
                title = self.sanitize_title(filename_base)
            else:
                if re.match(r"^(Season|S)\s*\d+$", parent_name, re.IGNORECASE):
                     grandparent = os.path.basename(os.path.dirname(os.path.dirname(file_path)))
                     grand_clean = grandparent.strip().lower()
                     if grandparent and grand_clean not in GENERIC_FOLDERS:
                         title = grandparent
                else:
                     title = parent_name
        
        if not title:
             # Final Hail Mary: Raw filename
             base = os.path.splitext(os.path.basename(file_path))[0]
             title = self.sanitize_title(base)

        # --- LOCAL CACHE CHECK ---
        if title:
            # Map guessit type to IMDb kind
            k_filter = None
            if media_type == 'movie': k_filter = 'movie'
            elif media_type == 'episode': k_filter = 'episode' # Map to TV Series check
            
            cached_matches = self.cache.search(title, year, kind_filter=k_filter)
            if cached_matches:
                print(f"DEBUG: Using cached result for '{title}'")
                return cached_matches
                
        # --- OFFLINE EXIT ---
        if offline_only:
            # If we didn't find it in cache, we stop here.
            return []

        queries_to_try = []
        if title:
            # Try combining with Year/Type for precision
            if year:
                queries_to_try.append(f"{title} {year} {media_type if media_type else 'movie'}")
            
            if media_type:
                 queries_to_try.append(f"{title} {media_type}")
                 
            queries_to_try.append(title)
            
        candidates = []
        found_ids = set()

        try:
            with DDGS() as ddgs:
                for q in queries_to_try:
                    if len(candidates) >= 5: break
                    
                    print(f"DEBUG: Searching DDG for '{q}'")
                    # Limit to results, search specifically for imdb
                    results_gen = ddgs.text(f"{q} imdb", max_results=5)
                    results_list = list(results_gen)
                    print(f"DEBUG: Query '{q}' returned {len(results_list)} results.")
                    
                    for r in results_list:
                        url = r['href']
                        match = re.search(r'tt\d+', url)
                        if match:
                            imdb_id = match.group(0)
                            if imdb_id not in found_ids:
                                found_ids.add(imdb_id)
                                try:
                                    clean_id = imdb_id.replace('tt', '')
                                    movie = self.ia.get_movie(clean_id)
                                    if movie:
                                        candidates.append(movie)
                                        # --- CACHE ON LEARN ---
                                        # If we successfully found a movie online that wasn't in cache, add it.
                                        # Note: This adds *candidates*. Ideally we only add the *chosen* one?
                                        # But for search cache, knowing candidates is good too.
                                        # Let's add all valid metadata found.
                                        self.cache.add_to_cache(movie)
                                except Exception as e:
                                    print(f"Error fetching ID {imdb_id}: {e}")
            
            return candidates

        except Exception as e:
            print(f"Error fetching metadata for {title}: {e}")
            return []

    def find_cached_match_raw(self, filename):
        """
        Attempts to find a cache match using the raw filename (sanitized).
        Returns a Movie object or None.
        """
        base = os.path.splitext(filename)[0]
        # Use sanitize_title to strip scene tags
        clean_name = self.sanitize_title(base)
        
        # Heuristic: If name is too short, skip raw check (too many false positives?)
        if len(clean_name) < 3:
            return None
            
        # Search cache
        # We don't have year or kind from raw filename reliably, so we search broad.
        # But we can try to extract a year using regex to help strictness.
        year_match = re.search(r'\b(19|20)\d{2}\b', clean_name)
        year = year_match.group(0) if year_match else None
        
        matches = self.cache.search(clean_name, year=year)
        if matches:
            # Return best match
            m = matches[0]
            m.source = "DB"
            return m
        return None

    def propose_rename(self, file_path, guess, metadata_list, format_string=None):
        """Generates a list of new filenames based on metadata candidates."""
        if not metadata_list or not guess:
            return []
        
        # Get extension
        _, ext = os.path.splitext(file_path)
        
        proposed_names = []
        
        for metadata in metadata_list:
            # Clean title
            title = metadata.get('title')
            # Enforce Title Case
            if title:
                title = title.strip().title()
                
            title = "".join([c for c in title if c not in r'<>:"/\|?*'])
            
            new_filename = None
            
            if guess.get('type') == 'episode' or metadata.get('kind') in ['tv series', 'tv mini series', 'episode']:
                # TV Show format
                season = guess.get('season')
                episode = guess.get('episode')
                
                if season is not None and episode is not None:
                    if isinstance(season, list): season = season[0]
                    if isinstance(episode, list): episode = episode[0]
                    
                    if format_string:
                        data = {
                            'title': title,
                            'season': season,
                            'episode': episode,
                            'year': metadata.get('year')
                        }
                        stem = self.apply_format(format_string, data)
                        new_filename = f"{stem}{ext}"
                    else:
                        s_str = f"S{season:02d}"
                        e_str = f"E{episode:02d}"
                        new_filename = f"{title} - {s_str}{e_str}{ext}"
                        
                    if new_filename not in proposed_names:
                        proposed_names.append(new_filename)
                else:
                    new_filename = f"{title}{ext}"
                    if new_filename not in proposed_names:
                        proposed_names.append(new_filename)
            else:
                # Movie format
                year = metadata.get('year')
                if year:
                    new_filename = f"{title} ({year}){ext}"
                else:
                    new_filename = f"{title}{ext}"
                
                if new_filename and new_filename not in proposed_names:
                    proposed_names.append(new_filename)
                        
        return proposed_names

    def extract_context_title(self, file_path):
        """
        Walks up the directory tree to find a 'Rich Title' from folder names.
        Skips generic folders like 'Season X', 'Specials', 'Subs'.
        Returns the title string if found, or None.
        """
        try:
            ignore_pattern = re.compile(r"^(season ?\d+|specials|featurettes|subs|subtitles|bonus|cd\d+)$", re.IGNORECASE)
            
            GENERIC_FOLDERS = {
                "movies", "films", "downloads", "completed", "video", "videos", 
                "tv", "tv shows", "tv series", "plex", "media", "unsorted", "library", "unknown"
            }

            # Start from parent
            parent = os.path.dirname(file_path)
            
            # Walk up at most 2 levels
            for _ in range(2):
                dirname = os.path.basename(parent)
                if not dirname or len(dirname) < 2: # Root or empty
                    break
                    
                clean_name = dirname.strip().lower()
                
                if clean_name not in GENERIC_FOLDERS and not ignore_pattern.match(dirname):
                    # Found a potential candidate!
                    # Clean it: Remove trailing " - Season X" or " Season X"
                    title = dirname.strip()
                    title = re.sub(r"[ -]*Season ?\d+$", "", title, flags=re.IGNORECASE)
                    return title.strip()
                    
                # Move up
                parent = os.path.dirname(parent)
        except Exception:
            pass
        return None

    def apply_format(self, template, data):
        """
        Applies data to the format template.
        Supported tokens: {Title}, {title}, {season}, {episode}, {year}.
        Auto-handles S/E padding.
        """
        # Prepare data dict
        fmt_data = {}
        
        # Title
        t = data.get('title', '')
        fmt_data['Title'] = t.strip().title()
        fmt_data['title'] = t.strip() # As parsed
        
        # Season/Episode (Ensure 02d)
        s = data.get('season')
        e = data.get('episode')
        
        if s is not None:
            try: fmt_data['season'] = f"{int(s):02d}"
            except: fmt_data['season'] = str(s)
        else: fmt_data['season'] = ""
            
        if e is not None:
             try: fmt_data['episode'] = f"{int(e):02d}"
             except: fmt_data['episode'] = str(e)
        else: fmt_data['episode'] = ""
        
        # Year
        y = data.get('year')
        fmt_data['year'] = str(y) if y else ""

        # Safe formatting
        # We need to replace only known keys.
        # Python's format() fails if missing keys.
        # So we do a manual replacement or SafeSub.
        # Manual replace is safer for limited set.
        
        result = template
        for key, val in fmt_data.items():
            result = result.replace(f"{{{key}}}", val)
            
        # Clean double spaces or weird chars from template artifacts?
        # nah, trust user template.
        
        # Sanitize filename characters at end?
        # Just ensure valid chars.
        result = "".join([c for c in result if c not in r'<>:"/\|?*'])
        
        return result

    def generate_name_from_guess(self, guess, extension, format_string=None):
        """Generates a formatted filename from guessit dict."""
        if not guess: return None
        
        title = guess.get('title')
        if not title: return None
        
        # --- CRITICAL CONFIDENCE CHECK ---
        # If the title still contains tech specs, it's a bad guess.
        # But wait, sanitize_title STRIPS them.
        # So let's sanitize. If the result is empty or weird, reject.
        clean_title = self.sanitize_title(title)
        if not clean_title or len(clean_title) < 2:
            return None
            
        # Use clean title for generation
        title = clean_title.title()

        media_type = guess.get('type')
        if media_type == 'episode':
            season = guess.get('season')
            episode = guess.get('episode')
            
            if season is not None and episode is not None:
                if isinstance(season, list): season = season[0]
                if isinstance(episode, list): episode[0]
                
                # Use format string if provided
                if format_string:
                    data = {
                        'title': title,
                        'season': season,
                        'episode': episode,
                        'year': guess.get('year'),
                    }
                    stem = self.apply_format(format_string, data)
                    return f"{stem}{extension}"
                else:
                    # Default
                    s_str = f"S{season:02d}"
                    e_str = f"E{episode:02d}"
                    return f"{title} - {s_str}{e_str}{extension}"
                
        elif media_type == 'movie':
            year = guess.get('year')
            if year:
                return f"{title} ({year}){extension}"
            else:
                 # For movies without year, we might accept just title, but it's risky.
                 # Let's verify we at least have a title.
                 return f"{title}{extension}"
                 
        return None

    def rename_file(self, old_path, new_path):
        """Renames the file and any companion files (subtitles, etc)."""
        COMPANION_EXTS = {'.srt', '.sub', '.idx', '.vtt', '.ssa', '.ass', '.nfo', '.jpg', '.jpeg', '.png', '.txt'}
        
        try:
            os.rename(old_path, new_path)
            
            # Rename companions
            old_base = os.path.splitext(old_path)[0]
            new_base = os.path.splitext(new_path)[0]
            
            # Check standard extensions
            for ext in COMPANION_EXTS:
                old_comp = old_base + ext
                if os.path.exists(old_comp):
                    new_comp = new_base + ext
                    try:
                        os.rename(old_comp, new_comp)
                        print(f"DEBUG: Renamed companion {old_comp} -> {new_comp}")
                    except OSError as e:
                        print(f"Error renaming companion {old_comp}: {e}")
            return True
        except OSError as e:
            print(f"Error renaming {old_path} to {new_path}: {e}")
            return False

    def organize_files(self, scanned_files, scan_root, settings=None):
        """
        Restructures folders to ensure 'Show Name/Show Name - Season X/File' hierarchy.
        Now supports standardizing existing movie folders ("renaming parent") to keep companions together.
        """
        if settings is None: settings = {}
        
        organize_enabled = settings.get("organize", True)
        
        # If organization is disabled, we do nothing but return empty stats
        if not organize_enabled:
            return {"status": "Organization Disabled"}
            
        stats = {"folders_created": 0, "folders_renamed": 0, "files_moved": 0, "folders_moved": 0}
        
        # 1. Analyze Directory Structure
        # Map ParentDir -> List of (original_path, new_path)
        dir_contents = {}
        
        for item in scanned_files:
            try:
                abs_root = os.path.abspath(scan_root)
            except Exception:
                continue

            root_name = os.path.basename(abs_root)
            
            final_show_dir = None
            
            # Case 1: The Root IS the Show Folder (e.g. user selected "halo")
            if root_name.lower() == show_name.lower():
                # If casing is wrong, we SHOULD rename the root for consistency.
                if root_name != show_name:
                    print(f"DEBUG: Fixing case for Root Show Folder: {root_name} -> {show_name}")
                    new_root_path = os.path.join(os.path.dirname(abs_root), show_name)
                    temp_root_path = os.path.join(os.path.dirname(abs_root), f"{root_name}_temp_rename")
                    
                    try:
                        os.rename(abs_root, temp_root_path)
                        os.rename(temp_root_path, new_root_path)
                        
                        # Update our references
                        stats["folders_renamed"] += 1
                        path_replacements.append((abs_root, new_root_path))
                        
                        # Update abs_root for future iterations of this loop? 
                        # abs_root is calculated per item? No, abs_root is constant.
                        # We must update abs_root variable!
                        abs_root = new_root_path
                        # Also scan_root?
                        scan_root = new_root_path
                        
                        # CRITICAL: Update abs_current because it lives inside abs_root
                        # We must re-resolve abs_current immediately
                        abs_current = os.path.join(new_root_path, os.path.relpath(abs_current, path_replacements[-1][0]))
                        
                    except OSError as e:
                        print(f"Error capitalizing root folder: {e}")
                        # Fallback: Treat existing root as the show dir despite case
                        
                # Fallback: Treat existing root as the show dir despite case
                        
                final_show_dir = abs_root
            else:
                # Case 3: We are inside the Show Folder (e.g. scan_root is "Season 1", parent is "halo")
                # User selected a subfolder. We should check the parent.
                parent_dir = os.path.dirname(abs_root)
                parent_name = os.path.basename(parent_dir)
                
                if parent_name.lower() == show_name.lower():
                    # We are INSIDE the show folder.
                    
                    # Check casing of PARENT
                    if parent_name != show_name:
                         print(f"DEBUG: Fixing case for Parent Show Folder: {parent_name} -> {show_name}")
                         grandparent = os.path.dirname(parent_dir)
                         new_parent_path = os.path.join(grandparent, show_name)
                         temp_parent_path = os.path.join(grandparent, f"{parent_name}_temp_rename")
                         
                         try:
                             # Rename Parent
                             os.rename(parent_dir, temp_parent_path)
                             os.rename(temp_parent_path, new_parent_path)
                             
                             stats["folders_renamed"] += 1
                             # Track replacement logic
                             # This invalidates scan_root and everything inside it!
                             path_replacements.append((parent_dir, new_parent_path))
                             
                             # Update our local variables
                             parent_dir = new_parent_path
                             # scan_root has moved relative to FS, so update abs_root
                             # abs_root was "parent_dir/root_name"
                             abs_root = os.path.join(new_parent_path, root_name)
                             scan_root = abs_root # For consistency
                             
                             # CRITICAL: Re-resolve abs_current
                             if abs_current.startswith(path_replacements[-1][0] + os.sep):
                                  rel = os.path.relpath(abs_current, path_replacements[-1][0])
                                  abs_current = os.path.join(new_parent_path, rel)
                                  
                         except OSError as e:
                             print(f"Error capitalizing parent show folder: {e}")
                    
                    final_show_dir = parent_dir
                    
                else:
                    # Case 2: The Show Folder should be a child of Root (e.g. user selected "TV Shows")
                    
                    found_match = None
                    # Use cache for O(1) lookup
                    existing_child = root_children_cache.get(show_name.lower())
                    
                    if existing_child:
                        child_path = os.path.join(abs_root, existing_child)
                        if os.path.isdir(child_path):
                            # Found it! Check casing.
                            if existing_child != show_name:
                                # Wrong casing (e.g. "halo"). Rename.
                                print(f"DEBUG: Fixing case for Show Folder: {existing_child} -> {show_name}")
                                temp_path = os.path.join(abs_root, f"{existing_child}_temp_rename")
                                final_path = os.path.join(abs_root, show_name)
                                try:
                                    os.rename(child_path, temp_path)
                                    os.rename(temp_path, final_path)
                                    child_path = final_path
                                    # Update cache
                                    root_children_cache[show_name.lower()] = show_name
                                    stats["folders_renamed"] += 1
                                    # Track replacement
                                    old_abs = os.path.join(abs_root, existing_child)
                                    path_replacements.append((old_abs, final_path))
                                    
                                    # CRITICAL: If abs_current was inside this folder, we must update it NOW
                                    # otherwise the move below will look for file in old folder
                                    if abs_current.startswith(old_abs + os.sep) or abs_current == old_abs:
                                         abs_current = os.path.join(final_path, os.path.relpath(abs_current, old_abs))
                                         
                                except OSError as e:
                                    print(f"Error capitalizing show folder: {e}")
                                    # Fallback to existing
                            
                            found_match = child_path
                    
                    if found_match:
                        final_show_dir = found_match
                    else:
                        final_show_dir = os.path.join(abs_root, show_name)
                        # We might create it, so update cache for subsequent files!
                        root_children_cache[show_name.lower()] = show_name

            # --- Determine Season Dir & Fix Case ---
            # Get Folder Format
            folder_fmt = settings.get("folder_format")
            
            if folder_fmt:
                 # Clean format string to avoid path injection
                 folder_fmt = "".join([c for c in folder_fmt if c not in r':*?"<>|'])
                 data = {'title': show_name, 'season': season_num, 'episode': 0, 'year': ''}
                 target_season_dir_name = self.apply_format(folder_fmt, data)
            else:
                 # Default
                 target_season_dir_name = f"{show_name} - Season {season_num}"

            # We must check if season dir exists inside final_show_dir with wrong case
            final_season_dir = os.path.join(final_show_dir, target_season_dir_name)
            
            if os.path.exists(final_show_dir):
                try:
                    for child in os.listdir(final_show_dir):
                        if child.lower() == target_season_dir_name.lower():
                            child_path = os.path.join(final_show_dir, child)
                            if os.path.isdir(child_path):
                                if child != target_season_dir_name:
                                    print(f"DEBUG: Fixing case for Season Folder: {child} -> {target_season_dir_name}")
                                    temp_path = os.path.join(final_show_dir, f"{child}_temp_rename")
                                    final_path = os.path.join(final_show_dir, target_season_dir_name)
                                    try:
                                        os.rename(child_path, temp_path)
                                        os.rename(temp_path, final_path)
                                        stats["folders_renamed"] += 1
                                        # Track replacement
                                        path_replacements.append((child_path, final_path))
                                    except OSError as e:
                                         print(f"Error capitalizing season folder: {e}")
                                break
                except OSError: pass
            
            final_file_path = os.path.join(final_season_dir, filename)
            
            # --- Move File ---
            if abs_current != final_file_path:
                print(f"DEBUG: Organizing {filename} -> {final_season_dir}")
                
                if not os.path.exists(final_show_dir):
                    try:
                         os.makedirs(final_show_dir)
                         stats["folders_created"] += 1
                    except OSError: pass

                if not os.path.exists(final_season_dir):
                    try:
                        os.makedirs(final_season_dir)
                        stats["folders_created"] += 1
                    except OSError: pass
                
                # Check collision
                if os.path.exists(final_file_path):
                    # Collision. If src != dst, we have a duplicate?
                    # Or we already moved it? (Logic above check abs_current != final_file_path)
                    print(f"DEBUG: Target file exists {final_file_path}, skipping move.")
                else:
                    try:
                        os.rename(abs_current, final_file_path)
                        stats["files_moved"] += 1
                        
                        # Move Companions
                        old_base_path = os.path.splitext(abs_current)[0]
                        new_base_path = os.path.splitext(final_file_path)[0]
                        for ext in COMPANION_EXTS:
                            old_comp = old_base_path + ext
                            if os.path.exists(old_comp):
                                new_comp = new_base_path + ext
                                try:
                                    os.rename(old_comp, new_comp)
                                    print(f"DEBUG: Moved companion {old_comp} -> {new_comp}")
                                except OSError as e:
                                    print(f"Error moving companion {old_comp}: {e}")
                                    
                        # Update current_path reference if we were tracking it (scanned_files is distinct)
                        cleanup_candidates.add(os.path.dirname(abs_current))
                    except OSError as e:
                        print(f"Error moving file: {e}")
            else:
                # Already in correct place
                pass

        # --- Cleanup Empty Dirs ---
        # Sort by depth (deepest first) to delete leaf nodes first
        sorted_candidates = sorted(list(cleanup_candidates), key=lambda p: len(p), reverse=True)
        
        for d in sorted_candidates:
            # Check if empty
            try:
                if not os.listdir(d):
                    print(f"DEBUG: Removing empty folder {d}")
                    os.rmdir(d)
                else:
                    # check if it contains only empty season folders we just emptied?
                    # The recursion above handles depth, but if we have multiple levels...
                    # simple rmdir only works if empty.
                    pass
            except OSError:
                pass
                
        return stats

    def infer_missing_titles(self, scanned_files):
        """
        Post-process pass to fill in 'Unknown' files using siblings in the same folder.
        scanned_files format: [(original, new_name, full_new_path, status, options), ...]
        Returns updated scanned_files list.
        """
        from collections import Counter
        
        # 1. Group by directory
        dir_groups = {}
        for idx, item in enumerate(scanned_files):
            original = item[0]
            dirname = os.path.dirname(original)
            if dirname not in dir_groups:
                dir_groups[dirname] = []
            dir_groups[dirname].append(idx)
            
        updated_files = list(scanned_files)
        
        for dirname, indices in dir_groups.items():
            # Gather successful matches in this folder
            valid_titles = []
            
            for idx in indices:
                # new_name is item[1]
                new_name = updated_files[idx][1]
                if new_name and new_name != "Unknown":
                    # Extract title from "Title - SxxExx.ext"
                    # Regex is safest
                    match = re.search(r"^(.*?) - S\d+E\d+", new_name)
                    if match:
                        valid_titles.append(match.group(1))
            
            if not valid_titles:
                continue
                
            # Find consensus title
            common_title = Counter(valid_titles).most_common(1)[0][0]
            print(f"DEBUG: Consensus title for '{dirname}' is '{common_title}'")
            
            # Apply to failures
            for idx in indices:
                original, new_name, full_path, status, options = updated_files[idx]
                
                if new_name == "Unknown" or new_name is None:
                    # Parse original to get S/E
                    guess = self.parse_filename(original)
                    season = guess.get('season')
                    episode = guess.get('episode')
                    
                    if season and episode:
                         if isinstance(season, list): season = season[0]
                         if isinstance(episode, list): episode = episode[0]
                         
                         _, ext = os.path.splitext(original)
                         
                         # Construct new name
                         s_str = f"S{season:02d}"
                         e_str = f"E{episode:02d}"
                         inferred_name = f"{common_title} - {s_str}{e_str}{ext}"
                         
                         print(f"DEBUG: Inferring name for {os.path.basename(original)} -> {inferred_name}")
                         
                         dirname = os.path.dirname(original)
                         new_full_path = os.path.join(dirname, inferred_name)
                         
                         # Update tuple
                         # We add the inferred name as an option (and selection)
                         # options list was empty for unknown
                         new_options = [inferred_name]
                         updated_files[idx] = (original, inferred_name, new_full_path, "Ready (Inferred)", new_options)
                         
        return updated_files

 
    def preview_folder_changes(self, scanned_files, scan_root, settings=None):
        """
        Generates a list of planned folder operations for UI preview.
        Supports Movies (Rename Parent) and TV Shows (Structure).
        """
        if settings is None: settings = {}
        organize_enabled = settings.get("organize", True)
        if not organize_enabled: return []

        preview_ops = []
        
        # Group by Parent Directory to detect "Movie Folder" candidates
        dir_contents = {}
        for item in scanned_files:
            original = item[0]
            if "Skipped" in item[3] or "Error" in item[3]: continue
            
            # Use full_new_path if set
            full_new_path = item[2]
            if not full_new_path: continue
            
            parent = os.path.dirname(original)
            if parent not in dir_contents: dir_contents[parent] = []
            dir_contents[parent].append(item)

        # Track renames to avoid confusion
        processed_folders = set()
        
        for parent_dir, items in dir_contents.items():
             if parent_dir in processed_folders: continue
             processed_folders.add(parent_dir)
             
             is_root = os.path.normpath(parent_dir) == os.path.normpath(scan_root)
             
             # MOVIE/SINGLE VIDEO FOLDER LOGIC
             # If folder has 1 video file in our list, and we are organizing...
             if not is_root and len(items) == 1:
                 item = items[0]
                 original = item[0]
                 full_new_path = item[2]
                 
                 target_dir = os.path.dirname(full_new_path)
                 
                 # If we are changing the folder name
                 if os.path.normpath(parent_dir) != os.path.normpath(target_dir):
                     
                     # Heuristic: Are we moving to a sibling folder? (Rename)
                     # Or moving far away? (Move)
                     # Assuming scan_root is common ancestor.
                     
                     # Simple Preview Logic:
                     # If target doesn't exist, we propose "Rename Folder".
                     if not os.path.exists(target_dir):
                         preview_ops.append({
                             "action": "Rename Folder",
                             "src": parent_dir,
                             "dst": target_dir,
                             "reason": "Match Movie Title"
                         })
                     else:
                         # Target exists, so it's a Merge/Move files
                         preview_ops.append({
                             "action": "Move File",
                             "src": original,
                             "dst": full_new_path,
                             "reason": "Merge into existing folder"
                         })
             
             else:
                 # Multiple files or Root -> Likely TV Show or Messy Folder
                 # For Preview, we can just show "Organize x Files" or assume TV Logic?
                 # Existing TV logic was complex. Let's simplify for Preview:
                 # Just show distinct destination folders being created.
                 
                 dest_folders = set()
                 for it in items:
                     fp = it[2]
                     if fp: dest_folders.add(os.path.dirname(fp))
                 
                 for d in dest_folders:
                     if not os.path.exists(d):
                          preview_ops.append({
                             "action": "Create Folder",
                             "src": None,
                             "dst": d,
                             "reason": "New Structure"
                         })

        return preview_ops
