import os
import sys
import shutil

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from renamer import AutoRenamer

def create_dummies(base_dir):
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    os.makedirs(base_dir)
    
    # List of messy filenames to test
    # Structure: Root -> [Show Name Folder] -> [Season Folder] -> File
    
    # Case 1: Ambiguous filename, clear folder structure
    show_dir = os.path.join(base_dir, "Breaking Bad")
    season_dir = os.path.join(show_dir, "Season 5") # Should become Season 05
    os.makedirs(season_dir, exist_ok=True)
    
    file_path = os.path.join(season_dir, "01.mkv") # Ambiguous name "01.mkv"
    with open(file_path, 'w') as f: f.write("dummy")
    
    paths = [file_path]
    return paths

def verify():
    sandbox = os.path.abspath(os.path.join(os.path.dirname(__file__), 'sandbox'))
    print(f"Creating dummy files in {sandbox}...")
    create_dummies(sandbox)
    
    renamer = AutoRenamer()
    print("Scanner starting...")
    files = renamer.scan_directory(sandbox)
    print(f"Found {len(files)} files.")
    
    for f in files:
        print(f"\nProcessing: {f}")
        guess = renamer.parse_filename(f)
        print(f"Guess: {guess}")
        
        metadata_list = renamer.fetch_metadata(guess)
        if metadata_list:
            print(f"Metadata Found: {len(metadata_list)} candidates")
            for m in metadata_list:
                print(f" - {m['title']} ({m.get('year')}) Kind: {m.get('kind')}")
            
            proposed_names = renamer.propose_rename(f, guess, metadata_list)
            print(f"Proposed Names: {proposed_names}")
            
            # Simulate Rename with first choice
            if proposed_names:
                new_name = proposed_names[0]
                dirname = os.path.dirname(f)
                new_full = os.path.join(dirname, new_name)
                renamer.rename_file(f, new_full)
                
                # Test Folder Rename
                print("Testing folder rename...")
                renamer.rename_folders([dirname])
                
        else:
            print("No metadata found.")

if __name__ == "__main__":
    verify()
