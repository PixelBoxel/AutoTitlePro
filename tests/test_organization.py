import os
import shutil
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from renamer import AutoRenamer

def test_organization():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), 'sandbox_org'))
    if os.path.exists(base): shutil.rmtree(base)
    os.makedirs(base)
    
    # Setup: "Downloads/Adventure Time - S01E01.mkv" (Loose file scenario)
    # We want it to become "Downloads/Adventure Time/Adventure Time - Season 1/..."
    
    downloads_dir = os.path.join(base, "Downloads")
    os.makedirs(downloads_dir)
    
    filename = "Adventure Time - S01E01.mkv"
    file_path = os.path.join(downloads_dir, filename)
    with open(file_path, 'w') as f: f.write("dummy")
    
    renamer = AutoRenamer()
    
    # Simulate Scanned Files list (already renamed state)
    scanned = [
        (file_path, filename, file_path, "Renamed", [])
    ]
    
    print("--- Organizing Loose File ---")
    renamer.organize_files(scanned, downloads_dir)
    
    target_path = os.path.join(downloads_dir, "Adventure Time", "Adventure Time - Season 1", filename)
    if os.path.exists(target_path):
        print("SUCCESS: Loose file moved to deep structure.")
    else:
        print(f"FAILURE: File not at {target_path}")
        # Debug tree
        for root, dirs, files in os.walk(base):
            for name in files:
                print(os.path.join(root, name))

    # Test 2: "Downloads/Season 1/Adventure Time - S01E02.mkv"
    # Should become "Downloads/Adventure Time/Adventure Time - Season 1/..."
    
    season_dir = os.path.join(downloads_dir, "Season 1")
    os.makedirs(season_dir)
    slug = "Adventure Time - S01E02.mkv"
    f2 = os.path.join(season_dir, slug)
    with open(f2, 'w') as f: f.write("dummy")
    
    scanned2 = [(f2, slug, f2, "Renamed", [])]
    
    print("\n--- Organizing Season Folder ---")
    renamer.organize_files(scanned2, downloads_dir)
    
    target2 = os.path.join(downloads_dir, "Adventure Time", "Adventure Time - Season 1", slug)
    if os.path.exists(target2):
        print("SUCCESS: Generic Season folder renamed and moved.")
    else:
        # Note: logic might merge it into the folder created in Test 1!
        # If "Adventure Time/Adventure Time - Season 1" exists, it should move content/merge.
        # My implementation mainly uses 'rename'. If target exists, it tries to move file?
        pass
        
    # Let's check manually
    if os.path.exists(target2):
        print("SUCCESS verified.")
    else:
        print("FAILURE 2")
        for root, dirs, files in os.walk(base):
            for name in files:
                print(os.path.join(root, name))

if __name__ == "__main__":
    test_organization()
