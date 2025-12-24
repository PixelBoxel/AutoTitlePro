import os
import sys
import shutil
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from renamer import AutoRenamer

def test_context_inference():
    renamer = AutoRenamer()
    
    # Mock file structure
    # /tmp/Game of Thrones/Season 1/GoT S01E01.mkv
    
    base = os.path.abspath("test_context_env")
    show_dir = os.path.join(base, "Game of Thrones - Season 1")
    file_path = os.path.join(show_dir, "GoT S01E01.mkv")
    
    # Setup
    if os.path.exists(base): shutil.rmtree(base)
    os.makedirs(show_dir)
    with open(file_path, 'w') as f: f.write("dummy")
    
    print(f"Testing Context Inference on: {file_path}")
    
    # Test Extraction
    context_title = renamer.extract_context_title(file_path)
    print(f"Directory Structure: {file_path}")
    print(f"Extracted Context Title: '{context_title}'")
    
    # Should be cleaned to just "Game of Thrones"
    if context_title == "Game of Thrones":
        print("PASS: Correctly cleaned show title from mixed folder.")
    else:
        print(f"FAIL: Expected 'Game of Thrones', got '{context_title}'")
        
    # Cleanup
    shutil.rmtree(base)

if __name__ == "__main__":
    test_context_inference()
