import tkinter
import customtkinter
import threading
import os
import tkinter.messagebox
import re
from renamer import AutoRenamer, __version__

class AutoTitleApp(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("AutoTitlePro")
        self.geometry("1200x800")
        
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

        # Content Area - Tab View
        self.tab_view = customtkinter.CTkTabview(self)
        self.tab_view.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        self.tab_files = self.tab_view.add("Files")
        self.tab_folders = self.tab_view.add("Folders")
        
        # Configure Grid Weights for tabs
        self.tab_files.grid_columnconfigure(0, weight=1)
        self.tab_folders.grid_columnconfigure(0, weight=1)
        
        self.status_label = customtkinter.CTkLabel(self.tab_files, text="Select a directory to start scanning.")
        self.status_label.pack(pady=20)

        # Footer
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
        
        # Clear previous results
        for widget in self.tab_files.winfo_children():
            widget.destroy()
        for widget in self.tab_folders.winfo_children():
            widget.destroy()
        
        self.status_label = customtkinter.CTkLabel(self.tab_files, text="Scanning directory and fetching metadata...")
        self.status_label.pack(pady=20)
        
        self.current_label.pack(side="bottom", pady=2)
        self.progress_bar.pack(side="bottom", fill="x", padx=10, pady=5)
        self.progress_bar.start()

        # Run in thread
        threading.Thread(target=self.scan_thread, args=(directory,), daemon=True).start()

    def update_progress_label(self, text):
        self.current_label.configure(text=text)

    def scan_thread(self, directory):
        files = self.renamer.scan_directory(directory)
        results = []
        
        # Cache for folder -> Show Title to speed up parsing
        known_dirs = {}
        
        # Get Format Setting
        fmt = self.settings.get("rename_format")
        
        for i, file_path in enumerate(files):
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
                # Heuristic: If context title is significantly different or filename title is very short (e.g. "GoT" vs "Game of Thrones")
                # Or just always trust folder context if it exists and looks like a title?
                # Let's trust it if it's not None.
                # However, ensure we don't overwrite if filename had something specific like "Game of Thrones (2011)"
                # But guessing usually returns raw string.
                print(f"DEBUG: Context title found: '{context_title}' (overriding '{filename_title}')")
                guess['title'] = context_title
            
            # 1. FAST PATH: Local Parse
            local_name = self.renamer.generate_name_from_guess(guess, ext, format_string=fmt)
            
            if local_name:
                dirname = os.path.dirname(file_path)
                full_new_path = os.path.join(dirname, local_name)
                # Parse out the title to cache it
                # We need to robustly extract title regardless of format?
                # Actually, extracting from `guess` is safer.
                if guess.get('title'):
                    known_dirs[dirname] = guess['title'].strip().title()
                
                print(f"DEBUG: Local parse success: {local_name}")
                
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
                    
                    print(f"DEBUG: Cache hit for {dirname}: {inferred_name}")
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
        results = self.renamer.infer_missing_titles(results)

        self.scanned_files = results
        self.after(0, self.display_results)

    def display_results(self):
        self.is_scanning = False
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.current_label.pack_forget()
        self.select_button.configure(state="normal")
        
        # Clear loading labels
        for widget in self.tab_files.winfo_children():
            widget.destroy()

        if not self.scanned_files:
            lbl = customtkinter.CTkLabel(self.tab_files, text="No video files found.")
            lbl.pack(pady=20)
            return

        # Sort results: Unknowns/Failures first, then by filename
        self.scanned_files.sort(key=lambda x: (x[1] != "Unknown" and x[1] is not None, os.path.basename(x[0])))

        self.run_button.configure(state="normal")
        self.comboboxes = {} # Map index to combobox widget
        
        # 1. Fixed Header (Grid)
        header_frame = customtkinter.CTkFrame(self.tab_files, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=5)
        header_frame.grid_columnconfigure(0, weight=1) # Orig
        header_frame.grid_columnconfigure(1, weight=0) # Arrow
        header_frame.grid_columnconfigure(2, weight=1) # New
        
        customtkinter.CTkLabel(header_frame, text="Original Names", font=customtkinter.CTkFont(size=14, weight="bold"), anchor="w").grid(row=0, column=0, padx=10, sticky="ew")
        customtkinter.CTkLabel(header_frame, text="", width=20).grid(row=0, column=1) # spacer
        customtkinter.CTkLabel(header_frame, text="New Names", font=customtkinter.CTkFont(size=14, weight="bold"), anchor="w").grid(row=0, column=2, padx=10, sticky="ew")

        # 2. Scrollable Content Area
        scroll_frame = customtkinter.CTkScrollableFrame(self.tab_files, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        scroll_frame.grid_columnconfigure(0, weight=1)
        scroll_frame.grid_columnconfigure(1, weight=0)
        scroll_frame.grid_columnconfigure(2, weight=1)

        visible_row_count = 0
        for i, (original, new_name, _, status, options) in enumerate(self.scanned_files):
            # FILTER: Hide if new_name matches original exactly (Quality of Life)
            # Unless status has error? No, if error new_name likely different or None.
            orig_name = os.path.basename(original)
            if new_name == orig_name and "Unknown" not in status:
                continue
                
            row_idx = visible_row_count * 2
            visible_row_count += 1
            
            # Original Name
            # orig_name already calc above
            
            # Color coding
            color = "white" # System default often adapts, but explicit white in dark mode is safe or let None do work.  
            # Actually, let's use standard text colors but highlighting is good.
            text_color_val = "text_color" # Special token? No, just use None for default
            
            if "Unknown" in status or "Skipped" in status:
                color = "#ff5555" # Red
                if not new_name: new_name = "Unknown"
            elif "Cached" in status: 
                color = "#55ff55" # Green
            
            # Use color only if set
            lbl_orig = customtkinter.CTkLabel(scroll_frame, text=orig_name, anchor="w", text_color=color if color != "white" else None)
            lbl_orig.grid(row=row_idx, column=0, padx=10, pady=5, sticky="ew")
            
            # Arrow
            customtkinter.CTkLabel(scroll_frame, text="➜", text_color="gray").grid(row=row_idx, column=1, padx=5)
            
            # New Name (Combobox)
            if not options: options = ["Unknown"]
            
            # Ensure new_name is in options
            if new_name and new_name not in options:
                options.insert(0, new_name)
                
            combo = customtkinter.CTkComboBox(scroll_frame, values=options)
            if new_name:
                combo.set(new_name)
            else:
                combo.set("Unknown")
                
            combo.grid(row=row_idx, column=2, padx=10, pady=5, sticky="ew")
            self.comboboxes[i] = combo
            
            # Separator Line
            sep = customtkinter.CTkFrame(scroll_frame, height=2, fg_color=("gray85", "gray25"))
            sep.grid(row=row_idx+1, column=0, columnspan=3, sticky="ew", padx=10, pady=0)
            
        if visible_row_count == 0:
             customtkinter.CTkLabel(scroll_frame, text="All files matched their expected names! No changes needed.").pack(pady=20)
            
        # Update Folders Tab
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
        # Update scanned_files with current selections from comboboxes
        updated_files = []
        for i, (original, default_new_name, _, status, options) in enumerate(self.scanned_files):
            combo = self.comboboxes.get(i)
            if combo:
                # User visible row
                selected_name = combo.get()
            else:
                # Hidden row (filtered out), use default
                selected_name = default_new_name
                
            if selected_name and selected_name != "Unknown":
                dirname = os.path.dirname(original)
                full_new_path = os.path.join(dirname, selected_name)
                # FIX: Append 5th element (options) to satisfy unpack in organize_files
                updated_files.append((original, selected_name, full_new_path, "Ready", options))
            else:
                updated_files.append((original, None, None, "Skipped", []))
        
        # Overwrite scan list
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
                    # But we must update the PATH in the tuple to the ORIGINAL path if we didn't rename
                    # Wait, if we don't rename, the file is still at 'original'.
                    # For organization to work, it expects the file at its current location.
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
         self.display_updated_results()

    def display_updated_results(self):
        # Refresh the list to show "Renamed" status (Simple text now, no combos needed)
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        for item in self.scanned_files:
             # Unpack safely (handle 4 or 5 elements)
             if len(item) == 5:
                 original, new_name, full_new_path, status, _ = item
             else:
                 original, new_name, full_new_path, status = item
             row_frame = customtkinter.CTkFrame(self.scrollable_frame)
             row_frame.pack(fill="x", padx=5, pady=2)
             
             orig_name = os.path.basename(original)
             # Match widths
             lbl_orig = customtkinter.CTkLabel(row_frame, text=orig_name, width=450, anchor="w")
             lbl_orig.pack(side="left", padx=5)
             
             status_lbl = customtkinter.CTkLabel(row_frame, text=status, text_color="green" if status == "Renamed" else "red")
             status_lbl.pack(side="right", padx=10)
