import tkinter
import customtkinter
import threading
import os
import tkinter.messagebox
from renamer import AutoRenamer

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
        self.label.pack(pady=10)

        # Content Area - Scrollable Frame for file list
        self.scrollable_frame = customtkinter.CTkScrollableFrame(self, label_text="Files Found")
        self.scrollable_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = customtkinter.CTkLabel(self.scrollable_frame, text="Select a directory to start scanning.")
        self.status_label.pack(pady=20)

        # Footer
        self.footer_frame = customtkinter.CTkFrame(self)
        self.footer_frame.grid(row=2, column=0, padx=20, pady=20, sticky="ew")

        self.select_button = customtkinter.CTkButton(self.footer_frame, text="Select Directory", command=self.select_directory)
        self.select_button.pack(side="left", padx=10, pady=10)

        self.run_button = customtkinter.CTkButton(self.footer_frame, text="Start Renaming", state="disabled", command=self.start_renaming)
        self.run_button.pack(side="right", padx=10, pady=10)
        
        self.current_label = customtkinter.CTkLabel(self.footer_frame, text="")
        
        self.progress_bar = customtkinter.CTkProgressBar(self.footer_frame)
        self.progress_bar.set(0)

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
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.status_label = customtkinter.CTkLabel(self.scrollable_frame, text="Scanning directory and fetching metadata...")
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
        
        for i, file_path in enumerate(files):
            # Update UI for progress
            filename = os.path.basename(file_path)
            self.current_label.configure(text=f"Processing: {filename}")
            
            guess = self.renamer.parse_filename(file_path)
            
            # FAST PATH: Try to generate name locally first
            _, ext = os.path.splitext(file_path)
            local_name = self.renamer.generate_name_from_guess(guess, ext)
            
            if local_name:
                dirname = os.path.dirname(file_path)
                full_new_path = os.path.join(dirname, local_name)
                # We can still add local_name as the ONLY option for now to be fast
                print(f"DEBUG: Local parse success: {local_name}")
                
                # Check for perfect match
                if local_name == filename:
                     results.append((file_path, local_name, full_new_path, "Ready (Organize Only)", [local_name]))
                else:
                     results.append((file_path, local_name, full_new_path, "Ready (Local)", [local_name]))
            else:
                # SLOW PATH: Fetch online metadata
                print(f"DEBUG: Local parse insufficient for {filename}, fetching online...")
                metadata_list = self.renamer.fetch_metadata(guess)
                proposed_names = self.renamer.propose_rename(file_path, guess, metadata_list)
                
                if proposed_names:
                    # Default to first
                    best_name = proposed_names[0]
                    dirname = os.path.dirname(file_path)
                    full_new_path = os.path.join(dirname, best_name)
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
        
        # Clear loading label
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if not self.scanned_files:
            lbl = customtkinter.CTkLabel(self.scrollable_frame, text="No video files found.")
            lbl.pack(pady=20)
            return

        # Sort results: Unknowns/Failures first, then by filename
        # key tuple: (is_known (bool), filename)
        # We want is_known=False (Unknown) to be first. False < True.
        # So we sort by (is_known, filename).
        # Actually better to sort by status "Unknown" or empty new_name.
        
        self.scanned_files.sort(key=lambda x: (x[1] != "Unknown" and x[1] is not None, os.path.basename(x[0])))

        self.run_button.configure(state="normal")
        self.comboboxes = {} # Map index to combobox widget

        # Create table-like rows
        for i, (original, new_name, _, status, options) in enumerate(self.scanned_files):
            row_frame = customtkinter.CTkFrame(self.scrollable_frame)
            row_frame.pack(fill="x", padx=5, pady=2)
            
            orig_name = os.path.basename(original)
            
            # WIDENED COLUMNS
            lbl_orig = customtkinter.CTkLabel(row_frame, text=orig_name, width=450, anchor="w")
            lbl_orig.pack(side="left", padx=5)
            
            arrow = customtkinter.CTkLabel(row_frame, text="->", width=30)
            arrow.pack(side="left")
            
            if options:
                # Use Combobox - WIDENED
                combo = customtkinter.CTkComboBox(row_frame, values=options, width=500)
                combo.set(new_name) # Default
                combo.pack(side="left", padx=5)
                self.comboboxes[i] = combo
            else:
                lbl_new = customtkinter.CTkLabel(row_frame, text="Unknown/No Match", width=500, anchor="w", text_color="red")
                lbl_new.pack(side="left", padx=5)
                self.comboboxes[i] = None

    def start_renaming(self):
        # Update scanned_files with current selections from comboboxes
        updated_files = []
        for i, (original, _, _, status, options) in enumerate(self.scanned_files):
            combo = self.comboboxes.get(i)
            if combo:
                selected_name = combo.get()
                if selected_name and selected_name != "Unknown":
                    dirname = os.path.dirname(original)
                    full_new_path = os.path.join(dirname, selected_name)
                    # FIX: Append 5th element (options) to satisfy unpack in organize_files
                    updated_files.append((original, selected_name, full_new_path, "Ready", options))
                else:
                    updated_files.append((original, None, None, "Skipped", []))
            else:
                updated_files.append((original, None, None, "Skipped", []))
        
        # Overwrite scan list
        self.scanned_files = updated_files
        
        self.run_button.configure(state="disabled")
        threading.Thread(target=self.rename_thread, daemon=True).start()

    def rename_thread(self):
        success_count = 0
        directories_to_check = set()
        
        for i, (original, new_name, full_new_path, status, options) in enumerate(self.scanned_files):
            if status == "Skipped":
                continue

            # Check for exact match (File is already named correctly)
            if original == full_new_path:
                self.scanned_files[i] = (original, new_name, full_new_path, "File OK", options)
                # Still count as success/processed? Yes.
                # success_count += 1
                # Must check folder organization still!
                directories_to_check.add(os.path.dirname(original))
                continue

            if full_new_path and original != full_new_path:
                if self.renamer.rename_file(original, full_new_path):
                    self.scanned_files[i] = (original, new_name, full_new_path, "Renamed", options)
                    success_count += 1
                    # Add parent directory of the NEW path (which is same as old usually) to check list
                    directories_to_check.add(os.path.dirname(original))
                else:
                    self.scanned_files[i] = (original, new_name, full_new_path, "Error", options)
        
        # Clean up and organize folders based on renamed files
        # We pass the entire list because we need to know status and paths
        org_stats = self.renamer.organize_files(self.scanned_files, self.current_directory)
        
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
