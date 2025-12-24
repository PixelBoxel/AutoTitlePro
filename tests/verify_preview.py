import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from renamer import AutoRenamer

def test_preview():
    renamer = AutoRenamer()
    
    scan_root = "C:\\FakeRoot\\TV Shows"
    
    # Scenario: 
    # File: C:\FakeRoot\TV Shows\halo\season 1\halo.s01e01.mkv
    # Target: C:\FakeRoot\TV Shows\Halo\Halo - Season 1\Halo - S01E01.mkv
    # Operations:
    # 1. Rename Folder: ...\halo -> ...\Halo (Parent Fix)
    # 2. Rename Folder: ...\Halo\season 1 -> ...\Halo\Halo - Season 1 (Season Fix - unlikely to hit existing, so maybe Create?)
    # or just Create Folder ..\Halo\Halo - Season 1
    
    file_path = os.path.join(scan_root, "halo", "season 1", "halo.s01e01.mkv")
    
    scanned_files = [
        (file_path, "Halo - S01E01.mkv", "C:\\FakeRoot\\TV Shows\\Halo\\Halo - Season 1\\Halo - S01E01.mkv", "Ready (Local)", ["Halo - S01E01.mkv"])
    ]
    
    settings = {"organize": True, "title_case": True}
    
    ops = renamer.preview_folder_changes(scanned_files, scan_root, settings)
    
    print("--- Operations ---")
    for op in ops:
        print(f"Action: {op['action']}")
        print(f"Src: {op['src']}")
        print(f"Dst: {op['dst']}")
        print(f"Reason: {op.get('reason')}")
        print("-" * 20)
        
    # Check assertions
    has_rename = any(op['action'] == "Rename Folder" and "Halo" in op['dst'] for op in ops)
    # Actually, logic might be "Create Folder" if it thinks "season 1" isn't the same.
    # But Parent Fix "halo -> Halo" should appear.
    
    if any(op['reason'] == "New Show" for op in ops):
         # If "halo" exists in scan_root, we might expect Rename
         pass

if __name__ == "__main__":
    test_preview()
