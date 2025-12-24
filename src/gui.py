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
            # Fix: Pass watchdog kick callback to prevent timeout during long file enumeration
            kick_callback = lambda: self.watchdog.kick() if hasattr(self, 'watchdog') else None
            files = self.renamer.scan_directory(directory, progress_callback=kick_callback)
            print(f"DEBUG: Found {len(files)} files in directory.")
            results = []
            
            # Cache for folder -> Show Title to speed up parsing
            known_dirs = {}
            
            # Get Format Setting
            fmt = self.settings.get("rename_format")
            
            for i, file_path in enumerate(files):
                # Watchdog Kick (I'm alive!)
                if hasattr(self, 'watchdog'): self.watchdog.kick()
                
                # Update UI for progress
                filename = os.path.basename(file_path)
                dirname = os.path.dirname(file_path)
                self.current_label.configure(text=f"Processing: {filename}")
                
                guess = self.renamer.parse_filename(file_path)
                _, ext = os.path.splitext(file_path)
            
                # --- CONTEXTUAL TITLE INFERENCE (NEW) ---
                # Try to get a better title from parent folders logic if filename short/generic
                # Rule: If folder title is found and is longer/different than filename title, use it.
                context_title = self.renamer.extract_context_title(file_path)
                if context_title:
                    filename_title = guess.get('title', '')
                    # Heuristic: If context title is significantly different or filename title is very short
                    # Debug print reduced to avoid spam on 3800 files, or keep it? Keep it for now.
                    # print(f"DEBUG: Context title found: '{context_title}'")
                    guess['title'] = context_title
                
                # 1. FAST PATH: Local Parse
                local_name = self.renamer.generate_name_from_guess(guess, ext, format_string=fmt)
                
                if local_name:
                    dirname = os.path.dirname(file_path)
                    full_new_path = os.path.join(dirname, local_name)
                    # Parse out the title to cache it
                    if guess.get('title'):
                        known_dirs[dirname] = guess['title'].strip().title()
                    
                    # Check for perfect match
                    if local_name == filename:
                         results.append((file_path, local_name, full_new_path, "Ready (Organize Only)", [local_name]))
                    else:
                         results.append((file_path, local_name, full_new_path, "Ready (Local)", [local_name]))
                
                # 2. CACHE PATH: Use known show title from siblings
                elif dirname in known_dirs:
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
                        results.append((file_path, inferred_name, full_new_path, "Ready (Cached)", [inferred_name]))
                    else:
                        # Missing number info, can't infer name even with title
                         results.append((file_path, "Unknown", None, "Skipped", []))
                         
                else:
                    # 3. SLOW PATH: Fetch online metadata
                    print(f"DEBUG: Local parse insufficient for {filename}, fetching online...")
                    metadata_list = self.renamer.fetch_metadata(guess, file_path)
                    proposed_names = self.renamer.propose_rename(file_path, guess, metadata_list, format_string=fmt)
                    
                    if proposed_names:
                        # Default to first
                        best_name = proposed_names[0]
                        dirname = os.path.dirname(file_path)
                        full_new_path = os.path.join(dirname, best_name)
                        
                        # Cache the title
                        if guess.get('title'):
                            known_dirs[dirname] = guess['title'].strip().title()
                            
                        results.append((file_path, best_name, full_new_path, "Ready (Online)", proposed_names))
                    else:
                         results.append((file_path, "Unknown", None, "Skipped", []))
    
                # GAP FILLING STEP: Infer titles for unknown files if siblings have matches
                # Actually, infer_missing_titles runs on the WHOLE list, not one by one.
                # So we must wait until loop finishes.
            
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

        # Sort results
        self.scanned_files.sort(key=lambda x: (x[1] != "Unknown" and x[1] is not None, os.path.basename(x[0])))
        self.run_button.configure(state="normal")

        # FILTER PHASE
        self.filtered_indices = []
        show_all = self.show_all_var.get()
        
        print(f"DEBUG: Filtering results. Show All = {show_all}")
        
        for i, (original, new_name, _, status, _) in enumerate(self.scanned_files):
            orig_name = os.path.basename(original)
            
            should_show = True
            if not show_all:
                if new_name == orig_name and "Unknown" not in status:
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
            entry = self.scanned_files[real_index]
            # Tuple: (original, new_name, full_new_path, status, options)
             # Update new_name (index 1) and full_new_path (index 2)
            original = entry[0]
            dirname = os.path.dirname(original)
            full_new_path = os.path.join(dirname, new_value)
            
            # Construct new tuple
            new_entry = (original, new_value, full_new_path, entry[3], entry[4])
            self.scanned_files[real_index] = new_entry
            print(f"DEBUG: Updated index {real_index} -> {new_value}")


        
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
        header_frame.grid_columnconfigure(1, weight=0) 
        header_frame.grid_columnconfigure(2, weight=1)
        header_frame.grid_columnconfigure(3, weight=0)
        
        customtkinter.CTkLabel(header_frame, text="Original Names", font=customtkinter.CTkFont(size=14, weight="bold"), anchor="w").grid(row=0, column=0, padx=10, sticky="ew")
        customtkinter.CTkLabel(header_frame, text="", width=20).grid(row=0, column=1)
        customtkinter.CTkLabel(header_frame, text="New Names", font=customtkinter.CTkFont(size=14, weight="bold"), anchor="w").grid(row=0, column=2, padx=10, sticky="ew")
        
        # Checkbox for Show All (Re-create since frame cleared)
        chk = customtkinter.CTkCheckBox(header_frame, text="Show Unchanged Files", variable=self.show_all_var, command=self.display_results)
        chk.grid(row=0, column=3, padx=10)

        # Scrollable Content
        scroll_frame = customtkinter.CTkScrollableFrame(self.file_list_frame, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        scroll_frame.grid_columnconfigure(0, weight=1)
        scroll_frame.grid_columnconfigure(1, weight=0)
        scroll_frame.grid_columnconfigure(2, weight=1)
        
        for visual_row_idx, real_index in enumerate(page_indices):
            entry = self.scanned_files[real_index]
            original, new_name, _, status, options = entry
            orig_name = os.path.basename(original)
            
            # Color logic
            color = "white"
            if "Unknown" in status or "Skipped" in status:
                color = "#ff5555" 
                if not new_name: new_name = "Unknown"
            elif "Cached" in status or "Renamed" in status or "File OK" in status:
                color = "#55ff55"
            elif "Ready" in status: 
                # Ready is neutral/white usually, or maybe slight green? Keep white.
                pass
            
            # Render Row
            row_idx = visual_row_idx * 2
            
            lbl_orig = customtkinter.CTkLabel(scroll_frame, text=orig_name, anchor="w", text_color=color if color != "white" else None)
            lbl_orig.grid(row=row_idx, column=0, padx=10, pady=5, sticky="ew")
            
            customtkinter.CTkLabel(scroll_frame, text="➜", text_color="gray").grid(row=row_idx, column=1, padx=5)
            
            if not options: options = ["Unknown"]
            if new_name and new_name not in options: options.insert(0, new_name)
                
            combo = customtkinter.CTkComboBox(scroll_frame, values=options, command=lambda val, idx=real_index: self.update_choice(idx, val))
            if new_name: combo.set(new_name)
            else: combo.set("Unknown")
                
            combo.grid(row=row_idx, column=2, padx=10, pady=5, sticky="ew")
            
            # Separator
            sep = customtkinter.CTkFrame(scroll_frame, height=2, fg_color=("gray85", "gray25"))
            sep.grid(row=row_idx+1, column=0, columnspan=3, sticky="ew", padx=10, pady=0)
            
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
