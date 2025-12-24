import os
import shutil
import sys
# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from renamer import AutoRenamer

def create_environment(base_dir):
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    os.makedirs(base_dir)
    
    # Structure:
    # Root
    #   -> Adventure Time
    #      -> Season 2
    #         -> Adventure Time Fionna Cake S02E06... .mkv
    
    show_dir = os.path.join(base_dir, "Adventure Time")
    season_dir = os.path.join(show_dir, "Season 2")
    os.makedirs(season_dir)
    
    filename = "Adventure Time Fionna Cake S02E06 The Bird in the Clock 1080p AMZN WEB-DL DDP5 1 H 264-NTb.mkv"
    file_path = os.path.join(season_dir, filename)
    with open(file_path, 'w') as f: f.write("dummy")
    
    return season_dir, file_path

def verify():
    sandbox = os.path.abspath(os.path.join(os.path.dirname(__file__), 'sandbox_format'))
    print(f"Creating environment in {sandbox}...")
    season_dir, file_path = create_environment(sandbox)
    
    renamer = AutoRenamer()
    
    # 1. Test Rename Logic
    # We mock fetch_metadata to return a known good result to test FORMATTING only
    # (We already tested search in other scripts, and we know it might fail on empty result)
    
    mock_metadata = [
        {'title': 'Adventure Time: Fionna & Cake', 'kind': 'tv series'}
    ]
    
    print("\n--- Testing Parsing & Renaming ---")
    guess = renamer.parse_filename(file_path)
    print(f"Guess: {guess}")
    
    proposed_names = renamer.propose_rename(file_path, guess, mock_metadata)
    print(f"Proposed: {proposed_names}")
    
    expected_name = "Adventure Time Fionna & Cake - S02E06.mkv"
    if proposed_names and proposed_names[0] == expected_name:
        print("SUCCESS: File format matches request.")
    else:
        print(f"FAILURE: Expected '{expected_name}', got '{proposed_names[0] if proposed_names else None}'")

    # 2. Simulate File Rename
    if proposed_names:
        new_name = proposed_names[0]
        new_full_path = os.path.join(season_dir, new_name)
        renamer.rename_file(file_path, new_full_path)
        
        # 3. Test Folder Rename
        print("\n--- Testing Folder Rename ---")
        # We need to run rename_folders on the season directory
        renamer.rename_folders([season_dir])
        
        # Check if folder is renamed to "Show Name - Season X"
        parent_dir = os.path.dirname(season_dir)
        new_season_dir_name = "Adventure Time Fionna & Cake - Season 2"
        new_season_dir_path = os.path.join(parent_dir, new_season_dir_name)
        
        if os.path.exists(new_season_dir_path):
             print(f"SUCCESS: Folder renamed to '{new_season_dir_name}'")
        else:
             print(f"FAILURE: Folder not found at '{new_season_dir_path}'")
             print(f"Current folders: {os.listdir(parent_dir)}")

if __name__ == "__main__":
    verify()
