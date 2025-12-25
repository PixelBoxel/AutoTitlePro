import tkinter
import customtkinter
import threading
import os
import time
import sys
import traceback
import tkinter.messagebox
import re
from renamer import AutoRenamer, __version__

class Watchdog:
    """
    Background thread that monitors the application's liveness.
    If the worker thread doesn't 'kick' the dog for 30 seconds, 
    it assumes a hang and dumps a crash log.
    """
    def __init__(self, timeout=30.0):
        self.timeout = timeout
        self._last_kick = time.time()
        self._running = False
        self._monitor_thread = None
        self._triggered = False

    def start(self):
        self._running = True
        self._triggered = False
        self._last_kick = time.time()
        self._monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self._monitor_thread.start()

    def stop(self):
        self._running = False

    def kick(self):
        """Update the last activity timestamp."""
        self._last_kick = time.time()

    def _monitor(self):
        while self._running:
            time.sleep(1.0)
            if not self._running: break
            
            delta = time.time() - self._last_kick
            if delta > self.timeout and not self._triggered:
                self._triggered = True
                self.dump_state()
                # We could alert user here or just log
                print("WATCHDOG: Hang detected! Dumped state.")
                
    def dump_state(self):
        filename = f"crash_dump_{int(time.time())}.txt"
        with open(filename, "w") as f:
            f.write(f"AutoTitlePro Crash Dump - {time.ctime()}\n")
            f.write("="*40 + "\n")
            f.write("Application appears to be hung (active scan timeout).\n\n")
            
            f.write("Stack Traces:\n")
            # Dump all threads
            for thread_id, frame in sys._current_frames().items():
                f.write(f"\nThread ID: {thread_id}\n")
                traceback.print_stack(frame, file=f)
                f.write("-" * 20 + "\n")

class ToolTip(object):
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind("<Enter>", self.showtip)
        self.widget.bind("<Leave>", self.hidetip)

    def showtip(self, event=None):
        "Display text in tooltip window"
        self.text = self.widget.tooltip_text if hasattr(self.widget, 'tooltip_text') else self.text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        self.tipwindow = tw = tkinter.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        
        label = customtkinter.CTkLabel(tw, text=self.text, corner_radius=6, fg_color="#333333", text_color="white", padx=10, pady=5)
        label.pack(ipadx=1)
        
    def hidetip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class AutoTitleApp(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        
        # Ensure Taskbar Icon works (AppUserModelID)
        try:
            from ctypes import windll
            myappid = f'autotitlepro.version.{__version__}'
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        self.title(f"AutoTitlePro {__version__}")
        self.geometry("1200x800")
        
        # Icon resource path helper
        def resource_path(relative_path):
            try:
                base_path = sys._MEIPASS
            except Exception:
                # In dev, we are in src/, so we need to go up one level if using this logic,
                # BUT if CWD is root (standard), we just need relative path.
                # To be safe, let's use the file location logic for dev.
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            return os.path.join(base_path, relative_path)

        icon_path = resource_path(os.path.join('assets', 'icon.ico'))
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        
        self.renamer = AutoRenamer()
        self.scanned_files = [] # List of tuples: (original_path, new_name_candidate, full_new_path, status)
        self.is_scanning = False

        # Layout configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        self.header_frame = customtkinter.CTkFrame(self)
        self.header_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        self.label = customtkinter.CTkLabel(self.header_frame, text="AutoTitlePro", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.label.pack(side="left", padx=10)
        
        # Settings Button
        self.settings_button = customtkinter.CTkButton(self.header_frame, text="⚙ Settings", width=100, command=self.open_settings)
        self.settings_button.pack(side="right", padx=10)
        
        # Organization Status Indicator
        self.org_indicator = customtkinter.CTkLabel(self.header_frame, text="", font=customtkinter.CTkFont(size=12, weight="bold"))
        self.org_indicator.pack(side="right", padx=20)
        
        # Media Type Toggle
        self.type_var = customtkinter.StringVar(value="Auto")
        self.type_switch = customtkinter.CTkSegmentedButton(self.header_frame, values=["Auto", "Movie", "TV"], variable=self.type_var)
        self.type_switch.pack(side="right", padx=10)
        self.type_label = customtkinter.CTkLabel(self.header_frame, text="Media Type:", font=customtkinter.CTkFont(size=12, weight="bold"))
        self.type_label.pack(side="right", padx=(10, 5))
        
        # Deep Search Mode Toggle
        self.search_mode_var = customtkinter.StringVar(value="Auto")
        self.search_mode_switch = customtkinter.CTkSegmentedButton(self.header_frame, values=["Fast", "Auto", "Deep"], variable=self.search_mode_var)
        self.search_mode_switch.pack(side="right", padx=10)
        self.search_mode_lbl = customtkinter.CTkLabel(self.header_frame, text="Deep Search (?):", font=customtkinter.CTkFont(size=12, weight="bold"))
        self.search_mode_lbl.pack(side="right", padx=(10, 5))

        # Tooltip for Deep Search logic
        # Attached to Label because CTkSegmentedButton doesn't support bind well
        self.search_mode_lbl.tooltip_text = "Fast: Offline only\nAuto: Online fallback\nDeep: Online Driven"
        ToolTip(self.search_mode_lbl, self.search_mode_lbl.tooltip_text)

        # Settings Storage (Default values)
        self.settings = {
            "organize": True,
            "title_case": True,
            "dark_mode": True,
            "rename_files": True,
            "rename_format": "{Title} - S{season}E{episode}" # Default
        }
        
        self.show_all_var = customtkinter.BooleanVar(value=False)
        self.page_size = 50
        self.current_page = 0
        self.total_pages = 0
        self.filtered_indices = [] # Indices of scanned_files that are currently visible

        # Content Area - Tab View
        self.tab_view = customtkinter.CTkTabview(self)
        self.tab_view.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        self.tab_files = self.tab_view.add("Files")
        self.tab_folders = self.tab_view.add("Folders")
        
        # Configure Grid Weights for tabs
        self.tab_files.grid_columnconfigure(0, weight=1)
        self.tab_folders.grid_columnconfigure(0, weight=1)
        
        # Use a container for the list + pagination controls
        self.file_list_frame = customtkinter.CTkFrame(self.tab_files, fg_color="transparent")
        self.file_list_frame.pack(fill="both", expand=True)

        self.status_label = customtkinter.CTkLabel(self.file_list_frame, text="Select a directory to start scanning.")
        self.status_label.pack(pady=20)
        
        # Pagination Controls (Bottom of tab)
        self.pagination_frame = customtkinter.CTkFrame(self.tab_files, height=40)
        self.pagination_frame.pack(fill="x", pady=5, padx=10, side="bottom")
        
        self.btn_prev = customtkinter.CTkButton(self.pagination_frame, text="Previous", width=80, command=self.prev_page, state="disabled")
        self.btn_prev.pack(side="left", padx=10)
        
        self.lbl_page = customtkinter.CTkLabel(self.pagination_frame, text="Page 1 / 1")
        self.lbl_page.pack(side="left", expand=True)
        
        self.btn_next = customtkinter.CTkButton(self.pagination_frame, text="Next", width=80, command=self.next_page, state="disabled")
        self.btn_next.pack(side="right", padx=10)

        # Footer (remains same)
        self.footer_frame = customtkinter.CTkFrame(self)
        self.footer_frame.grid(row=2, column=0, padx=20, pady=20, sticky="ew")

        self.select_button = customtkinter.CTkButton(self.footer_frame, text="Select Directory", command=self.select_directory)
        self.select_button.pack(side="left", padx=10, pady=10)

        self.run_button = customtkinter.CTkButton(self.footer_frame, text="Start Processing", state="disabled", command=self.start_renaming)
        self.run_button.pack(side="right", padx=10, pady=10)
        
        self.current_label = customtkinter.CTkLabel(self.footer_frame, text="")
        
        self.progress_bar = customtkinter.CTkProgressBar(self.footer_frame)
        self.progress_bar.set(0)
        
        self.update_status_indicators()

    def update_status_indicators(self):
        if self.settings.get("organize"):
            self.org_indicator.configure(text="Folder Sort: ON", text_color="#55ff55") # Green
        else:
            self.org_indicator.configure(text="Folder Sort: OFF", text_color="#ff5555") # Red

    def open_settings(self):
        self.settings_window = customtkinter.CTkToplevel(self)
        self.settings_window.title("Settings")
        self.settings_window.geometry("400x500") # Increased height
        
        # Make modal
        self.settings_window.grab_set()
        
        # Title
        lbl = customtkinter.CTkLabel(self.settings_window, text="Preferences", font=customtkinter.CTkFont(size=16, weight="bold"))
        lbl.pack(pady=(10, 5))
        
        # Version
        v_lbl = customtkinter.CTkLabel(self.settings_window, text=f"AutoTitlePro {__version__}", text_color="gray")
        v_lbl.pack(pady=(0, 10))
        
        # 1. Dark Mode
        self.sw_dark = customtkinter.CTkSwitch(self.settings_window, text="Dark Mode", command=self.toggle_theme)
        if self.settings["dark_mode"]: self.sw_dark.select()
        self.sw_dark.pack(pady=10, data=None) # simple pack

        # 2. Title Case (Moved per request)
        self.sw_case = customtkinter.CTkSwitch(self.settings_window, text="Enforce Title Case", command=lambda: self.update_setting("title_case", self.sw_case.get()))
        if self.settings["title_case"]: self.sw_case.select()
        self.sw_case.pack(pady=10)
        
        # 3. Rename Files
        self.sw_rename = customtkinter.CTkSwitch(self.settings_window, text="Rename Files", command=lambda: self.update_setting("rename_files", self.sw_rename.get()))
        if self.settings["rename_files"]: self.sw_rename.select()
        self.sw_rename.pack(pady=10)
        
        # 4. Rename Format
        fmt_frame = customtkinter.CTkFrame(self.settings_window, fg_color="transparent")
        fmt_frame.pack(pady=10, padx=20, fill="x")
        
        customtkinter.CTkLabel(fmt_frame, text="Rename Format:", anchor="w").pack(fill="x")
        self.entry_fmt = customtkinter.CTkEntry(fmt_frame)
        self.entry_fmt.insert(0, self.settings.get("rename_format", "{Title} - S{season}E{episode}"))
        self.entry_fmt.pack(fill="x", pady=5)
        self.entry_fmt.bind("<KeyRelease>", lambda e: self.update_setting("rename_format", self.entry_fmt.get()))
        
        customtkinter.CTkLabel(fmt_frame, text="Tokens: {Title} {season} {episode} {year}", text_color="gray", font=("Arial", 10)).pack(anchor="w")

        # 5. Organize (Move) Files
        self.sw_org = customtkinter.CTkSwitch(self.settings_window, text="Organize into Folders", command=lambda: self.update_setting("organize", self.sw_org.get()))
        if self.settings["organize"]: self.sw_org.select()
        self.sw_org.pack(pady=10)
        
        # 6. Folder Format
        ffmt_frame = customtkinter.CTkFrame(self.settings_window, fg_color="transparent")
        ffmt_frame.pack(pady=10, padx=20, fill="x")
        
        customtkinter.CTkLabel(ffmt_frame, text="Season Folder Format:", anchor="w").pack(fill="x")
        self.entry_ffmt = customtkinter.CTkEntry(ffmt_frame)
        self.entry_ffmt.insert(0, self.settings.get("folder_format", "{Title} - Season {season}"))
        self.entry_ffmt.pack(fill="x", pady=5)
        self.entry_ffmt.bind("<KeyRelease>", lambda e: self.update_setting("folder_format", self.entry_ffmt.get()))
        
        customtkinter.CTkLabel(ffmt_frame, text="Tokens: {Title} {season}", text_color="gray", font=("Arial", 10)).pack(anchor="w")
        
    def update_setting(self, key, value):
        if key in ["rename_format", "folder_format"]:
             self.settings[key] = value # String
        else:
             self.settings[key] = bool(value)
             
        # Refresh Indicators
        self.update_status_indicators()
        
    def toggle_theme(self):
        val = self.sw_dark.get()
        self.settings["dark_mode"] = bool(val)
        customtkinter.set_appearance_mode("Dark" if val else "Light")

    def select_directory(self):
        if self.is_scanning:
            return
            
        directory = customtkinter.filedialog.askdirectory()
        if directory:
            self.start_scan(directory)

    def start_scan(self, directory):
        self.is_scanning = True
        self.current_directory = directory
        self.select_button.configure(state="disabled")
        self.run_button.configure(state="disabled")
        
        # Clear previous results (only data, refactor will handle UI)
        self.current_label.pack(side="bottom", pady=2)
        self.progress_bar.pack(side="bottom", fill="x", padx=10, pady=5)
        self.progress_bar.start()
        
        # Start Watchdog
        self.watchdog = Watchdog()
        self.watchdog.start()

        # Run in thread
        threading.Thread(target=self.scan_thread, args=(directory,), daemon=True).start()

    def update_progress_label(self, text):
        self.current_label.configure(text=text)

    def scan_thread(self, directory):
        try:
            print(f"DEBUG: Starting scan of {directory}")
            
            # --- BLOCK UNTIL CACHE READY ---
            if not self.renamer.cache.loaded: # Optimization: check loaded boolean first
                 self.update_progress_label("Initializing Movie Database... (First Run)")
                 # Wait up to 60s
                 ready = self.renamer.cache.wait_until_ready(timeout=60)
                 if not ready:
                     print("WARNING: Cache initialization timed out or failed. Proceeding anyway.")

            # Fix: Pass watchdog kick callback to prevent timeout during long file enumeration
            kick_callback = lambda: self.watchdog.kick() if hasattr(self, 'watchdog') else None
            files = self.renamer.scan_directory(directory, progress_callback=kick_callback)
            print(f"DEBUG: Found {len(files)} files in directory.")
            results = []
            
            # Cache for folder -> Show Title to speed up parsing
            known_dirs = {}
            
            # Get Format Setting
            fmt = self.settings.get("rename_format")
            
            # Get Media Type Override (Base)
            base_override = None
            type_val = self.type_var.get()
            if type_val == "Movie": base_override = 'movie'
            elif type_val == "TV": base_override = 'episode'
            
            # Get Deep Search Mode
            deep_search_mode = self.search_mode_var.get()
            
            print(f"DEBUG: Starting scan of {directory} with mode={type_val}, search={deep_search_mode}")
            
            for i, file_path in enumerate(files):
                # Watchdog Kick (I'm alive!)
                if hasattr(self, 'watchdog'): self.watchdog.kick()
                
                # Update UI for progress
                filename = os.path.basename(file_path)
                dirname = os.path.dirname(file_path)
                self.current_label.configure(text=f"Processing: {filename}")
                
                 # Dynamic Auto Logic
                current_override = base_override
                if type_val == "Auto":
                    # Check path for keywords
                    lower_path = file_path.lower()
                    # Use os.sep for robust check, or just loose string matching
                    if any(k in lower_path for k in ["/movies/", "\\movies\\", "films", "movie"]):
                         current_override = 'movie'
                    elif any(k in lower_path for k in ["/tv/", "\\tv\\", "shows", "series", "season"]):
                         current_override = 'episode'

                # PASS OVERRIDE TO PARSER
                guess = self.renamer.parse_filename(file_path, current_override)
                _, ext = os.path.splitext(file_path)
            
                # --- CONTEXTUAL TITLE INFERENCE (NEW) ---
                # Try to get a better title from parent folders logic if filename short/generic
                # Rule: If folder title is found and is longer/different than filename title, use it.
                context_title = self.renamer.extract_context_title(file_path)
                if context_title:
                    filename_title = guess.get('title', '')
                    guess['title'] = context_title
                
                # --- STRATEGY: CHECK LOCAL CACHE ("DB") BEFORE ANYTHING ELSE ---
                # As requested: "check the locl cache before going to guess it"
                # We interpret this as: Try Raw Filename against Cache.
                # If that hits, we TRUST the DB title/year, but we stick with Guessit's S/E.
                
                raw_match = self.renamer.find_cached_match_raw(filename)
                
                pre_matched_metadata = None
                
                if raw_match:
                     print(f"DEBUG: Raw filename matched in Cache: {raw_match['title']}")
                     # Override guess title/year with the authoritative DB info
                     guess['title'] = raw_match['title']
                     if raw_match.get('year'): 
                         guess['year'] = raw_match['year']
                     
                     # We treat this as our metadata result
                     pre_matched_metadata = [raw_match]
                     
                # --- MANDATORY YEAR CHECK (Movies) ---
                # If it's a movie and year is missing, and Deep Search is Auto, skip Fast Path.
                # If Fast Mode (Offline), we CANNOT skip local, we must try best effort.
                skip_local = False
                is_movie = (current_override == 'movie') or (guess.get('type') == 'movie')
                
                if is_movie and not guess.get('year'):
                     if deep_search_mode == "Deep": # Was "Auto"
                         # If we already matched raw cache, we have year hopefully.
                         if not pre_matched_metadata:
                             print(f"DEBUG: Missing year for movie '{filename}', forcing Deep Search.")
                             skip_local = True
                     elif deep_search_mode == "Fast":
                         # In Fast mode, we proceed with local guess even if missing year,
                         # but renamer might reject it (will result in "Unknown" likely)
                         pass
                
                # 1. FAST PATH: Local Parse (Only if NOT skipped AND NO DB/API match needed yet)
                # If we have a pre-match, we technically COULD use Fast Path logic if we update guess,
                # BUT we want to ensure we tag it as "DB". 
                # So if pre_matched_metadata is set, we skip Fast Path to force using the metadata in Slow Path logic.
                
                local_name = None
                if not skip_local and not pre_matched_metadata:
                    local_name = self.renamer.generate_name_from_guess(guess, ext, format_string=fmt)
                
                if local_name:
                    dirname = os.path.dirname(file_path)
                    full_new_path = os.path.join(dirname, local_name)
                    # Parse out the title to cache it
                    if guess.get('title'):
                        known_dirs[dirname] = guess['title'].strip().title()
                    
                    # Check for perfect match
                    # Tag as "FT" (File Title / Fast Track) logic
                    if local_name == filename:
                         results.append((file_path, local_name, full_new_path, "FT", [local_name]))
                    else:
                         results.append((file_path, local_name, full_new_path, "FT", [local_name]))
                
                # 2. CACHE PATH: Use known show title from siblings
                elif dirname in known_dirs and not pre_matched_metadata:
                    cached_title = known_dirs[dirname]
                    # We need Season/Episode from guess
                    season = guess.get('season')
                    episode = guess.get('episode')
                    
                    if season is not None and episode is not None:
                        if isinstance(season, list): season = season[0]
                        if isinstance(episode, list): episode = episode[0]
                        
                        # Apply Format
                        if fmt:
                            data = {'title': cached_title, 'season': season, 'episode': episode, 'year': guess.get('year')}
                            stem = self.renamer.apply_format(fmt, data)
                            inferred_name = f"{stem}{ext}"
                        else:
                            s_str = f"S{season:02d}"
                            e_str = f"E{episode:02d}"
                            inferred_name = f"{cached_title} - {s_str}{e_str}{ext}"
                            
                        full_new_path = os.path.join(dirname, inferred_name)
                        # Tag as "FT" also? It's inferred locally.
                        results.append((file_path, inferred_name, full_new_path, "FT", [inferred_name]))
                    else:
                        # Missing number info, can't infer name even with title
                         results.append((file_path, "Unknown", None, "Unknown", []))
                         
                else:
                    # 3. SLOW PATH: Fetch online metadata (OR Use Pre-Matched Raw Cache)
                    
                    offline_only = (deep_search_mode == "Fast")
                    
                    metadata_list = []
                    if pre_matched_metadata:
                        metadata_list = pre_matched_metadata
                    else:
                        print(f"DEBUG: Local parse insufficient for {filename}, fetching metadata...")
                        metadata_list = self.renamer.fetch_metadata(guess, file_path, offline_only=offline_only)
                    
                    # proposed_names is List[(name, source)]
                    proposed_tuples = self.renamer.propose_rename(file_path, guess, metadata_list, format_string=fmt)
                    
                    if proposed_tuples:
                        # Default to first
                        best_name = proposed_tuples[0][0]
                        source_tag = proposed_tuples[0][1]
                        
                        dirname = os.path.dirname(file_path)
                        full_new_path = os.path.join(dirname, best_name)
                        
                        # Extract just names for options
                        options = [p[0] for p in proposed_tuples]
                        
                        # Cache the title
                        if guess.get('title'):
                            known_dirs[dirname] = guess['title'].strip().title()
                            
                        results.append((file_path, best_name, full_new_path, source_tag, options))
                    else:
                         results.append((file_path, "Unknown", None, "Unknown", []))
    
                # GAP FILLING STEP: Infer titles for unknown files if siblings have matches
                # ... (infer_missing_titles logic needs update? It uses results structure. We kept it compatible.)
            
            results = self.renamer.infer_missing_titles(results)
            
            # Update main list
            self.scanned_files = results
            
            # Go to Display (main thread)
            self.after(0, self.display_results)

        except Exception as e:
            print(f"Error in scan thread: {e}")
            import traceback
            traceback.print_exc()
            self.after(0, lambda: tkinter.messagebox.showerror("Scan Error", f"An error occurred during scanning:\n{e}"))
            self.after(0, lambda: self.progress_bar.stop())
            self.after(0, lambda: self.run_button.configure(state="normal"))
        finally:
            self.is_scanning = False
            if hasattr(self, 'watchdog'): self.watchdog.stop()
    
    def display_results(self):
        self.is_scanning = False
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.current_label.pack_forget()
        self.select_button.configure(state="normal")
        
        if not self.scanned_files:
            # Clear UI if empty
            for widget in self.file_list_frame.winfo_children():
                widget.destroy()
            lbl = customtkinter.CTkLabel(self.file_list_frame, text="No video files found.")
            lbl.pack(pady=20)
            return

        # Sort results: Unknown -> Unchanged -> Changed
        def sort_key(entry):
             # entry = (original, new_name, full_new_path, status, options)
             orig_name = os.path.basename(entry[0])
             new_name = entry[1]
             
             # Priority 0: Unknown/Skipped
             if "Unknown" in entry[3] or not new_name or new_name == "Unknown":
                 return (0, orig_name)
             
             # Priority 1: Unchanged (if enabled, we want to see these)
             if new_name == orig_name:
                 return (1, orig_name)
                 
             # Priority 2: Changed
             return (2, orig_name)

        self.scanned_files.sort(key=sort_key)
        self.run_button.configure(state="normal")

        # FILTER PHASE
        self.filtered_indices = []
        show_all = self.show_all_var.get()
        
        print(f"DEBUG: Filtering results. Show All = {show_all}")
        
        for i, (original, new_name, _, status, _) in enumerate(self.scanned_files):
            orig_name = os.path.basename(original)
            
            should_show = True
            if not show_all:
                if new_name == orig_name and status != "Unknown":
                     should_show = False
                
            if should_show:
                self.filtered_indices.append(i)
                
        print(f"DEBUG: Filter complete. Showing {len(self.filtered_indices)} / {len(self.scanned_files)} items.")
        
        # Pagination Setup
        self.current_page = 0
        total_items = len(self.filtered_indices)
        self.total_pages = (total_items + self.page_size - 1) // self.page_size
        if self.total_pages < 1: self.total_pages = 1
        
        self.render_current_page()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.render_current_page()
            
    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.render_current_page()

    def update_choice(self, real_index, new_value):
        # Callback to update the underlying data model when combobox changes
        # This preserves state even if we paginate away
        if 0 <= real_index < len(self.scanned_files):
            # --- Handle Special Interactive Options ---
            if new_value == "Manual Correction...":
                self.handle_manual_rename(real_index)
                return
            elif new_value == "Deep Search...":
                self.handle_deep_search(real_index)
                return

            entry = self.scanned_files[real_index]
            # Tuple: (original, new_name, full_new_path, status, options)
             # Update new_name (index 1) and full_new_path (index 2)
            original = entry[0]
            dirname = os.path.dirname(original)
            full_new_path = os.path.join(dirname, new_value)
            
            # Construct new tuple
            new_entry = (original, new_value, full_new_path, "Manual", entry[4])
            self.scanned_files[real_index] = new_entry
            print(f"DEBUG: Updated index {real_index} -> {new_value}")
            
            # Trigger folder preview refresh if needed
            if self.settings.get("organize"):
                self.after(100, self.refresh_folder_preview)

    def handle_manual_rename(self, index):
        dialog = customtkinter.CTkInputDialog(text="Enter the correct filename (with extension):", title="Manual Correction")
        text = dialog.get_input()
        if text:
            text = text.strip()
            # Update entry
            original, current_name, current_full, status, options = self.scanned_files[index]
            
            if text not in options:
                options.insert(0, text)
            
            dirname = os.path.dirname(original)
            new_full_path = os.path.join(dirname, text)
            
            self.scanned_files[index] = (original, text, new_full_path, "Manual", options)
            self.render_current_page() # Refresh UI to show selected value
        else:
            self.render_current_page() # Revert selection

    def handle_deep_search(self, index):
        # AUTOMATIC Deep Search (No Dialog)
        # We construct a robust query from the filename + context
        
        original = self.scanned_files[index][0]
        filename = os.path.basename(original)
        dirname = os.path.dirname(original)
        parent_name = os.path.basename(dirname)
        
        # 1. Robust Clean
        clean_name = self.renamer.sanitize_title(os.path.splitext(filename)[0])
        print(f"DEBUG: Deep Search Clean Logic: '{filename}' -> '{clean_name}'")
        
        # 2. Get Media Type Context
        type_val = self.type_var.get()
        media_type_hint = None
        if type_val == "Movie": media_type_hint = 'movie'
        elif type_val == "TV": media_type_hint = 'episode'
        
        query = clean_name
        
        # 3. If TV, assume folder might be Show Name
        # If filename is short/numeric or explicit episode code, use parent
        is_tv_code = re.search(r"[Ss]\d+[Ee]\d+", filename)
        if media_type_hint == 'episode' or (not media_type_hint and is_tv_code):
             if len(clean_name) < 5 or is_tv_code:
                 ignore_pattern = re.compile(r"^(season ?\d+|specials|featurettes|subs|subtitles|bonus|cd\d+)$", re.IGNORECASE)
                 if not ignore_pattern.match(parent_name) and parent_name.lower() not in ["movies", "tv", "videos"]:
                     # If the parent name is not generic, assume it's the show name
                     # e.g. "Breaking Bad/Season 1/S01E01.mkv" -> grandparent?
                     # Our extract_context_title deals with that. Let's just grab direct parent for now,
                     # or maybe grandparent if parent is 'Season X'.
                     
                     context_title = self.renamer.extract_context_title(original)
                     if context_title:
                         query = f"{context_title} {clean_name}"
                     else:
                          query = f"{parent_name} {clean_name}"
        
        print(f"DEBUG: Automatic Deep Search Query: '{query}'")
        
        import threading
        # Run explicitly with the derived query
        threading.Thread(target=self._run_deep_search, args=(index, query), daemon=True).start()
            
    def _run_deep_search(self, index, query):
        try:
            print(f"DEBUG: Running deep search for '{query}'...")
            
            # Use current toggle setting for type hint
            media_type_hint = None
            type_val = self.type_var.get()
            if type_val == "Movie": media_type_hint = 'movie'
            elif type_val == "TV": media_type_hint = 'episode'
            
            # Construct a fake guess
            fake_guess = {'title': query} 
            if media_type_hint: fake_guess['type'] = media_type_hint
            
            # Use renamer instance
            results = self.renamer.fetch_metadata(fake_guess)
            
            # Generate names
            _, ext = os.path.splitext(self.scanned_files[index][0])
            # proposed_rename returns tuples now!
            proposed_tuples = self.renamer.propose_rename(self.scanned_files[index][0], fake_guess, results, self.settings.get("rename_format"))
            new_names = [p[0] for p in proposed_tuples]
            
            # Update Main Thread
            self.after(0, lambda: self._apply_deep_search_results(index, new_names))
            
        except Exception as e:
            print(f"Deep Search Error: {e}")
            self.after(0, self.render_current_page) # Reset
            
    def _apply_deep_search_results(self, index, new_names):
        import tkinter.messagebox
        if not new_names:
            tkinter.messagebox.showinfo("Deep Search", "No results found.")
            self.render_current_page()
            return

        original, current_name, current_full, status, options = self.scanned_files[index]
        
        # Merge new options
        for n in new_names:
            if n not in options:
                options.insert(0, n)
                
        # Select the best one (first one)
        best_new = new_names[0]
        dirname = os.path.dirname(original)
        new_full_path = os.path.join(dirname, best_new)
        
        self.scanned_files[index] = (original, best_new, new_full_path, "API", options) # Force API status for Deep Search
        self.render_current_page()
        tkinter.messagebox.showinfo("Deep Search", f"Found {len(new_names)} results!")

    def render_current_page(self):
        # Clear List Area
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
            
        # Update Pagination Controls
        self.lbl_page.configure(text=f"Page {self.current_page + 1} / {self.total_pages} (Total: {len(self.filtered_indices)})")
        self.btn_prev.configure(state="normal" if self.current_page > 0 else "disabled")
        self.btn_next.configure(state="normal" if self.current_page < self.total_pages - 1 else "disabled")
        
        # Slice for current page
        start_idx = self.current_page * self.page_size
        end_idx = start_idx + self.page_size
        page_indices = self.filtered_indices[start_idx:end_idx]
        
        if not page_indices:
             customtkinter.CTkLabel(self.file_list_frame, text="No files match current filter.").pack(pady=20)
             return

        # Render Table Headers
        header_frame = customtkinter.CTkFrame(self.file_list_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=5)
        
        header_frame.grid_columnconfigure(0, weight=1) 
        header_frame.grid_columnconfigure(1, weight=0) # Space 
        header_frame.grid_columnconfigure(2, weight=0) # Tag
        header_frame.grid_columnconfigure(3, weight=0) # Arrow
        header_frame.grid_columnconfigure(4, weight=1) # New Name
        header_frame.grid_columnconfigure(5, weight=0) # Checkbox (Right aligned)
        
        customtkinter.CTkLabel(header_frame, text="Original Names", font=customtkinter.CTkFont(size=14, weight="bold"), anchor="w").grid(row=0, column=0, padx=10, sticky="ew")
        # Empty space
        
        customtkinter.CTkLabel(header_frame, text="New Names", font=customtkinter.CTkFont(size=14, weight="bold"), anchor="w").grid(row=0, column=4, padx=10, sticky="ew")
        
        # Checkbox for Show All (Re-create since frame cleared)
        chk = customtkinter.CTkCheckBox(header_frame, text="Show Unchanged Files", variable=self.show_all_var, command=self.display_results)
        chk.grid(row=0, column=5, padx=10)

        # Scrollable Content
        scroll_frame = customtkinter.CTkScrollableFrame(self.file_list_frame, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        scroll_frame.grid_columnconfigure(0, weight=1)
        scroll_frame.grid_columnconfigure(1, weight=0) # Tag
        scroll_frame.grid_columnconfigure(2, weight=0) # Arrow
        scroll_frame.grid_columnconfigure(3, weight=1)
        
        for visual_row_idx, real_index in enumerate(page_indices):
            entry = self.scanned_files[real_index]
            original, new_name, _, status, options = entry
            orig_name = os.path.basename(original)
            
            # Color logic
            text_color = "white"
            tag_color = "gray"
            
            if "Unknown" in status:
                tag_color = "#ff5555" # Red
                text_color = "#ff5555"
                if not new_name: new_name = "Unknown"
            elif "DB" in status:
                tag_color = "#55ff55" # Green
            elif "API" in status:
                tag_color = "#55aaff" # Blueish
            elif "FT" in status:
                tag_color = "#ffff55" # Yellow
            elif "Manual" in status:
                tag_color = "#ffaa55" # Orange
            
            # Render Row
            row_idx = visual_row_idx * 2
            
            lbl_orig = customtkinter.CTkLabel(scroll_frame, text=orig_name, anchor="w", text_color=text_color if text_color != "white" else None)
            lbl_orig.grid(row=row_idx, column=0, padx=10, pady=5, sticky="ew")
            
            # Source Tag Label
            tag_text = status if status in ["DB", "API", "FT", "Manual", "Unknown"] else "FT"
            lbl_tag = customtkinter.CTkLabel(scroll_frame, text=tag_text, text_color=tag_color, width=40)
            lbl_tag.grid(row=row_idx, column=1, padx=5)
            
            # Arrow
            customtkinter.CTkLabel(scroll_frame, text="➜", text_color="gray").grid(row=row_idx, column=2, padx=5)
            
            if not options: options = ["Unknown"]
            if new_name and new_name not in options: options.insert(0, new_name)
            
            # --- Interactive Options (Avoid Duplicates) ---
            # Create a display copy so we don't pollute the data model
            display_options = list(options)
            if "Manual Correction..." not in display_options:
                display_options.append("Manual Correction...")
            if "Deep Search..." not in display_options:
                display_options.append("Deep Search...")
                
            combo = customtkinter.CTkComboBox(scroll_frame, values=display_options, command=lambda val, idx=real_index: self.update_choice(idx, val))
            if new_name: combo.set(new_name)
            else: combo.set("Unknown")
                
            combo.grid(row=row_idx, column=3, padx=10, pady=5, sticky="ew")
            
            # Separator
            sep = customtkinter.CTkFrame(scroll_frame, height=2, fg_color=("gray85", "gray25"))
            sep.grid(row=row_idx+1, column=0, columnspan=4, sticky="ew", padx=10, pady=0)
            
        # Folders Tab Preview
        self.refresh_folder_preview()

    def refresh_folder_preview(self):
        # Clear Folders Tab
        for widget in self.tab_folders.winfo_children():
            widget.destroy()
            
        # Add Header
        h_frame = customtkinter.CTkFrame(self.tab_folders, fg_color="transparent")
        h_frame.pack(fill="x", padx=10, pady=5)
        customtkinter.CTkLabel(h_frame, text="Action", width=120, anchor="w", font=customtkinter.CTkFont(size=12, weight="bold")).pack(side="left", padx=5)
        customtkinter.CTkLabel(h_frame, text="Source", width=300, anchor="w", font=customtkinter.CTkFont(size=12, weight="bold")).pack(side="left", padx=5)
        customtkinter.CTkLabel(h_frame, text="Destination", width=300, anchor="w", font=customtkinter.CTkFont(size=12, weight="bold")).pack(side="left", padx=5)

        ops = self.renamer.preview_folder_changes(self.scanned_files, self.current_directory, self.settings)
        
        if not ops:
            customtkinter.CTkLabel(self.tab_folders, text="No folder changes detected.").pack(pady=20)
            return

        for op in ops:
            row = customtkinter.CTkFrame(self.tab_folders)
            row.pack(fill="x", padx=10, pady=2)
            
            action = op['action']
            src = op['src'] if op['src'] else ""
            dst = op['dst']
            reason = op.get('reason', '')
            
            if action == "Create Folder":
                src_txt = "-"
                # Show relative path relative to scan_root if possible for readability
                try:
                    dst_txt = os.path.relpath(dst, self.current_directory)
                except:
                    dst_txt = os.path.basename(dst)
                col = "#55ff55" # Green
            elif action == "Rename Folder":
                src_txt = os.path.basename(src)
                dst_txt = os.path.basename(dst)
                col = "#ffff55" # Yellow
            else:
                src_txt = src
                dst_txt = dst
                col = "white"
                
            customtkinter.CTkLabel(row, text=action, width=120, anchor="w", text_color=col).pack(side="left", padx=5)
            customtkinter.CTkLabel(row, text=src_txt, width=300, anchor="w").pack(side="left", padx=5)
            customtkinter.CTkLabel(row, text=f"{dst_txt} ({reason})", width=300, anchor="w").pack(side="left", padx=5)



    def start_renaming(self):
        # Update scanned_files status based on current data
        updated_files = []
        for item in self.scanned_files:
            # item is (original, new_name, full_new_path, status, options)
            original = item[0]
            new_name = item[1]
            full_new_path = item[2]
            status = item[3]
            options = item[4] if len(item) > 4 else []
            
            if new_name and new_name != "Unknown":
                # Ensure full_new_path matches new_name (it should, but safety check)
                dirname = os.path.dirname(original)
                expected_path = os.path.join(dirname, new_name)
                
                updated_files.append((original, new_name, expected_path, "Ready", options))
            else:
                updated_files.append((original, None, None, "Skipped", options))
        
        self.scanned_files = updated_files
        self.run_button.configure(state="disabled")
        threading.Thread(target=self.rename_thread, daemon=True).start()

    def rename_thread(self):
        success_count = 0
        directories_to_check = set()
        
        rename_enabled = self.settings.get("rename_files", True)
        
        for i, (original, new_name, full_new_path, status, options) in enumerate(self.scanned_files):
            if status == "Skipped":
                continue

            # Check for exact match (File is already named correctly)
            if original == full_new_path:
                self.scanned_files[i] = (original, new_name, full_new_path, "File OK", options)
                directories_to_check.add(os.path.dirname(original))
                continue

            if full_new_path and original != full_new_path:
                if rename_enabled:
                    if self.renamer.rename_file(original, full_new_path):
                        self.scanned_files[i] = (original, new_name, full_new_path, "Renamed", options)
                        success_count += 1
                        # Add parent directory of the NEW path (which is same as old usually) to check list
                        directories_to_check.add(os.path.dirname(original))
                    else:
                        self.scanned_files[i] = (original, new_name, full_new_path, "Error", options)
                else:
                    # Rename disabled, just treat as "Renamed" (logically ready) for organization
                    self.scanned_files[i] = (original, new_name, original, "Skipped Rename", options)
                    directories_to_check.add(os.path.dirname(original))
        
        # Clean up and organize folders based on renamed files
        # We pass the entire list because we need to know status and paths
        # PASS SETTINGS HERE
        org_stats = self.renamer.organize_files(self.scanned_files, self.current_directory, self.settings)
        
        self.after(0, lambda: self.finish_renaming(success_count, org_stats))

    def finish_renaming(self, count, org_stats):
         msg = f"Renamed {count} files."
         
         # Append organization stats if any activity
         details = []
         if org_stats.get("folders_created", 0) > 0:
             details.append(f"Created {org_stats['folders_created']} folders.")
         if org_stats.get("folders_renamed", 0) > 0:
             details.append(f"Renamed {org_stats['folders_renamed']} folders.")
         if org_stats.get("folders_moved", 0) > 0:
             details.append(f"Moved {org_stats['folders_moved']} folders.")
         if org_stats.get("files_moved", 0) > 0:
             details.append(f"Moved {org_stats['files_moved']} files.")
             
         if details:
             msg += "\n\nOrganization Updates:\n" + "\n".join(details)
         
         tk_mb = tkinter.messagebox.showinfo("Finished", msg)
         self.run_button.configure(state="disabled") # Disable after run
         # Refresh the UI with the final statuses
         self.display_results()
