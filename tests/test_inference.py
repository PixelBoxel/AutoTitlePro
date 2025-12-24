import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from renamer import AutoRenamer

def test_inference():
    renamer = AutoRenamer()
    
    # Simulate a directory scan result
    # Format: (original_path, new_name, full_new_path, status, options)
    
    dir_path = r"C:\Runs\Adventure Time\Season 2"
    
    # File 1: Successful Match
    f1_orig = os.path.join(dir_path, "ep1.mkv")
    f1_new = "Adventure Time Fionna & Cake - S02E01.mkv"
    f1_full = os.path.join(dir_path, f1_new)
    
    # File 2: Failed Match (but guessit works)
    f2_orig = os.path.join(dir_path, "ep2.mkv")
    f2_new = "Unknown"
    f2_full = None
    
    # We must ensure renamer.parse_filename(f2_orig) returns valid season/episode for inference to work
    # Since these are dummy paths, we better make sure they don't crash parse_filename or we rely on filename parsing
    # The current implementation of infer_missing_titles calls parse_filename(original)
    
    # We need actual files if parse_filename checks for existence? 
    # guessit works on strings, so usually okay, unless parse_filename has os calls.
    # renamer.parse_filename calls guessit(file_path), which works on string.
    
    scanned_files = [
        (f1_orig, f1_new, f1_full, "Ready", [f1_new]),
        (f2_orig, f2_new, f2_full, "Skipped", [])
    ]
    
    print("--- Before Inference ---")
    for item in scanned_files:
        print(f"{os.path.basename(item[0])} -> {item[1]}")
        
    updated = renamer.infer_missing_titles(scanned_files)
    
    print("\n--- After Inference ---")
    for item in updated:
        print(f"{os.path.basename(item[0])} -> {item[1]}")
        
    # Check
    inferred_item = updated[1]
    expected_name = "Adventure Time Fionna & Cake - S02E02.mkv"
    
    if inferred_item[1] == expected_name:
        print("\nSUCCESS: Inference worked correcty.")
    else:
        print(f"\nFAILURE: Expected {expected_name}, got {inferred_item[1]}")

if __name__ == "__main__":
    test_inference()
