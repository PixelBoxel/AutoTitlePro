import os
from guessit import guessit
from imdb import Cinemagoer
from duckduckgo_search import DDGS
import re
import datetime

# Versioning: Year.Month.Day.Hour
now = datetime.datetime.now()
__version__ = f"v{now.year}.{now.month:02d}.{now.day:02d}.{now.hour:02d}"

class AutoRenamer:
    def __init__(self):
        self.ia = Cinemagoer()

    def scan_directory(self, path):
        """Recursively finds video files in the given directory."""
        video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.wmv')
        files = []
        for root, _, filenames in os.walk(path):
            for filename in filenames:
                if filename.lower().endswith(video_extensions):
                    files.append(os.path.join(root, filename))
        return files

    def parse_filename(self, file_path):
        """Uses guessit to extract metadata from the full file path."""
        # guessit is smart enough to handle full paths and extract info from parent folders
        guess = guessit(file_path)
        return guess

    def fetch_metadata(self, guess):
        """Queries IMDb via DuckDuckGo + Cinemagoer. Returns list of matches."""
        if not guess or 'title' not in guess:
            return []
        
        title = guess['title']
        year = guess.get('year')
        media_type = guess.get('type')
        
        queries_to_try = []
        base_query = f"{title}"
        if year: base_query += f" {year}"
        
        # Priority 1: Specific type
        if media_type == 'episode':
            queries_to_try.append(base_query + " tv series")
        elif media_type == 'movie':
            queries_to_try.append(base_query + " movie")
            
        # Priority 2: Base query
        queries_to_try.append(base_query)

        candidates = []
        found_ids = set()

        try:
            with DDGS() as ddgs:
                for q in queries_to_try:
                    print(f"DEBUG: Searching DDG for '{q}'")
                    # Limit to results, search specifically for imdb
                    results_gen = ddgs.text(f"{q} imdb", max_results=5)
                    results_list = list(results_gen)
                    print(f"DEBUG: Query '{q}' returned {len(results_list)} results.")
                    
                    found_in_this_query = False
                    for r in results_list:
                        url = r['href']
                        match = re.search(r'tt\d+', url)
                        if match:
                            imdb_id = match.group(0)
                            if imdb_id not in found_ids:
                                found_ids.add(imdb_id)
                                found_in_this_query = True
                                # Fetch details
                                try:
                                    clean_id = imdb_id.replace('tt', '')
                                    movie = self.ia.get_movie(clean_id)
                                    candidates.append(movie)
                                except Exception as e:
                                    print(f"Error fetching ID {imdb_id}: {e}")
                    
                    # If we found good results with the specific query, maybe we stop?
                    # But user wants options. Let's get up to 5 unique ones.
                    if len(candidates) >= 5:
                        break
            
            return candidates

        except Exception as e:
            print(f"Error fetching metadata for {title}: {e}")
            return []

    def propose_rename(self, file_path, guess, metadata_list):
        """Generates a list of new filenames based on metadata candidates."""
        if not metadata_list or not guess:
            return []
        
        # Get extension
        _, ext = os.path.splitext(file_path)
        
        proposed_names = []
        
        for metadata in metadata_list:
            # Clean title
            title = metadata.get('title')
            title = "".join([c for c in title if c not in r'<>:"/\|?*'])
            
            new_filename = None
            
            if guess.get('type') == 'episode' or metadata.get('kind') in ['tv series', 'tv mini series', 'episode']:
                # TV Show format: Show Name SxxExx
                season = guess.get('season')
                episode = guess.get('episode')
                
                if season is not None and episode is not None:
                    if isinstance(season, list): season = season[0]
                    if isinstance(episode, list): episode = episode[0]
                    s_str = f"S{season:02d}"
                    e_str = f"E{episode:02d}"
                    new_filename = f"{title} {s_str}{e_str}{ext}"
                else:
                    new_filename = f"{title}{ext}"
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

    def rename_file(self, old_path, new_path):
        """Renames the file."""
        try:
            os.rename(old_path, new_path)
            return True
        except OSError as e:
            print(f"Error renaming {old_path} to {new_path}: {e}")
            return False

    def rename_folders(self, directories):
        """
        Renames directories based on the files they contain.
        Expected structures: 'Show Name/Season X' or 'Show Name - Season X'.
        """
        # Sort directories by depth (deepest first) to avoid path invalidation
        # deeper paths have more separators
        directories = sorted(list(set(directories)), key=lambda p: p.count(os.sep), reverse=True)
        
        for directory in directories:
            # We need to analyze content again or infer from previous scans?
            # Simpler: Scan the directory properly?
            # Actually, we can just guessit on the directory name itself or look at children.
            
            # Let's inspect the folder name itself
            dirname = os.path.basename(directory)
            guess = guessit(dirname)
            
            # Strategies:
            # 1. Season Folder: "Season 1", "S1", "Show - Season 1" -> "Season 01"
            # 2. Show Folder: "Show Name" -> "Show Name (Year)" (Maybe too risky? User said 'update folder names too')
            
            # Let's focus on Season folders first as requested
            if guess.get('type') == 'episode' or 'season' in guess:
                 # It thinks it's an episode/season related structure
                 season = guess.get('season')
                 
                 if season is not None:
                     if isinstance(season, list): season = season[0]
                     
                     # Check if it has a show title in the folder name
                     # If it has a title + season, user might prefer "Season XX" inside a Show folder
                     # OR "Show name - Season XX" if it's a flat structure.
                     
                     # Let's try to normalize to "Season XX" IF the parent folder seems to be the Show Name.
                     # But we don't know if the parent is the show name.
                     
                     # Heuristic: 
                     # If folder name is just "Season N" or "S1", rename to "Season 0N".
                     # If folder name is "Show - Season N", maybe rename to "Season 0N" AND move to "Show" folder? 
                     # Moving files is risky. Let's just rename inplace.
                     
                     new_dirname = None
                     
                     # Case: "Season 1" -> "Season 01"
                     if 'season' in dirname.lower() and 'packet' not in dirname.lower(): # simple check
                         new_dirname = f"Season {season:02d}"
                    
                     # If valid rename and different
                     if new_dirname and new_dirname != dirname:
                         parent = os.path.dirname(directory)
                         new_path = os.path.join(parent, new_dirname)
                         
                         # Check collision
                         if not os.path.exists(new_path):
                             print(f"Renaming folder: {directory} -> {new_path}")
                             try:
                                 os.rename(directory, new_path)
                             except Exception as e:
                                 print(f"Failed to rename folder {directory}: {e}")

