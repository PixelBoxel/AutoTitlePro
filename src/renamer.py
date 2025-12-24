import os
from guessit import guessit
from imdb import Cinemagoer
from duckduckgo_search import DDGS
import re
import datetime

# Versioning: Year.Month.Day.Hour
now = datetime.datetime.now()
# Static version for release tracking
__version__ = "v2025.12.24.08"

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

    def fetch_metadata(self, guess, file_path=None):
        """Queries IMDb via DuckDuckGo + Cinemagoer. Returns list of matches."""
        
        title = guess.get('title')
        year = guess.get('year')
        media_type = guess.get('type')
        
        # Fallback: If title is missing or generic (e.g. "Episode 1"), use parent folder
        if not title and file_path:
            parent_name = os.path.basename(os.path.dirname(file_path))
            # Basic cleanup of parent name? (Remove "Season X"?)
            # If parent is "Season 1", we need the grandparent.
            if re.match(r"^(Season|S)\s*\d+$", parent_name, re.IGNORECASE):
                 grandparent = os.path.basename(os.path.dirname(os.path.dirname(file_path)))
                 if grandparent:
                     print(f"DEBUG: Using grandparent '{grandparent}' as fallback title source.")
                     title = grandparent
            else:
                 print(f"DEBUG: Using parent '{parent_name}' as fallback title source.")
                 title = parent_name
        
        if not title:
            return []
            
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
            # Enforce Title Case
            if title:
                title = title.strip().title()
                
            title = "".join([c for c in title if c not in r'<>:"/\|?*'])
            
            new_filename = None
            
            if guess.get('type') == 'episode' or metadata.get('kind') in ['tv series', 'tv mini series', 'episode']:
                # TV Show format: Show Name - SxxExx
                season = guess.get('season')
                episode = guess.get('episode')
                
                if season is not None and episode is not None:
                    if isinstance(season, list): season = season[0]
                    if isinstance(episode, list): episode = episode[0]
                    s_str = f"S{season:02d}"
                    e_str = f"E{episode:02d}"
                    # User Request: "Show Name - SXXEXX"
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

    def generate_name_from_guess(self, guess, extension):
        """
        Attempts to generate a clean filename purely from the guessit result.
        Returns a string or None if critical info is missing.
        """
        if not guess or 'title' not in guess:
            return None
            
        title = guess['title']
        # Enforce Title Case for consistency
        title = title.strip().title()
        
        # Determine type
        media_type = guess.get('type')
        
        if media_type == 'episode':
            season = guess.get('season')
            episode = guess.get('episode')
            
            if season is not None and episode is not None:
                if isinstance(season, list): season = season[0]
                if isinstance(episode, list): episode = episode[0]
                
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
            
            dirname = os.path.dirname(old_path)
            
            # Check for suffixes (case-insensitive check would be better but simple suffix loop works for now)
            # Actually, standard OS filesystems are tricky.
            # Best way: listdir and check startswith? No, too slow.
            # Just check the set.
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
        Uses scan_root and 'Show Name' anchors to flatten recursive/messy structures.
        """
        if settings is None: settings = {}
        
        organize_enabled = settings.get("organize", True)
        title_case_enabled = settings.get("title_case", True)
        
        # If organization is disabled, we do nothing but return empty stats
        if not organize_enabled:
            return {"status": "Organization Disabled"}
            
        stats = {"folders_created": 0, "folders_renamed": 0, "files_moved": 0, "folders_moved": 0}
        COMPANION_EXTS = {'.srt', '.sub', '.idx', '.vtt', '.ssa', '.ass', '.nfo', '.jpg', '.jpeg', '.png', '.txt'}
        
        # Set of source directories we have moved files FROM, to clean up later
        cleanup_candidates = set()
        
        # Optimization: Cache root children for fast lookup in batch mode
        # Map lower_case -> actual_name
        root_children_cache = {}
        try:
            if os.path.exists(scan_root):
                for child in os.listdir(scan_root):
                    root_children_cache[child.lower()] = child
        except OSError:
            pass

        for item in scanned_files:
            original, new_name, current_path, status, _ = item
            
            valid_statuses = ["Renamed", "File OK", "Ready (Local)", "Ready (Organize Only)", "Skipped Rename"]
            if status not in valid_statuses or not current_path or not os.path.exists(current_path):
                continue
                
            filename = os.path.basename(current_path)
            # Safe regex for cleaned files
            match = re.search(r"^(.*?) - S(\d+)E\d+", filename)
            if not match:
                continue
            
            raw_show_name = match.group(1)
            season_num = int(match.group(2))
            
            # Enforce Title Case for Folders (Uniformity)
            show_name = raw_show_name.strip()
            if title_case_enabled:
                show_name = show_name.title()
            
            target_season_dir_name = f"{show_name} - Season {season_num}"
            target_show_dir_name = show_name
            
            # --- Determine Base/Anchor (Strict Flattening Logic) ---
            # We want to enforce that the Show Folder is either the Root itself (if selected)
            # OR a direct child of the Root. 
            # This bypasses all deep/recursive nesting.

            # Normalize paths
            try:
                abs_current = os.path.abspath(current_path)
                abs_root = os.path.abspath(scan_root)
            except Exception:
                continue

            root_name = os.path.basename(abs_root)
            
            final_show_dir = None
            
            # Case 1: The Root IS the Show Folder (e.g. user selected "Halo")
            if root_name.lower() == show_name.lower():
                # We can't easily rename the root scanning directory itself safely.
                # Assume it is acceptable or user must rename root manually.
                final_show_dir = abs_root
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
                            except OSError as e:
                                print(f"Error capitalizing show folder: {e}")
                                # Fallback to existing
                        
                        found_match = child_path
                
                if found_match:
                    final_show_dir = found_match
                else:
                    final_show_dir = os.path.join(abs_root, show_name)
                    # We might create it, so update cache for subsequent files!
                    # Only logically, the directory doesn't verify existence until makedirs
                    # keys are lower case
                    root_children_cache[show_name.lower()] = show_name

            # --- Determine Season Dir & Fix Case ---
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

