import os
import time
import sys
# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from renamer import AutoRenamer

def verify_speed():
    renamer = AutoRenamer()
    
    # Test Case 1: Clean file (Fast Path)
    # This should be instant and NOT hit DDG
    filename = "Adventure.Time.Fionna.Cake.S02E06.mkv"
    ext = ".mkv"
    
    print("--- Test 1: Fast Path ---")
    start = time.time()
    
    # Simulate what GUI does
    guess = renamer.parse_filename(filename) # Uses full path logic usually, but here string ok
    local_name = renamer.generate_name_from_guess(guess, ext)
    
    end = time.time()
    
    print(f"Guess: {guess}")
    print(f"Local Name: {local_name}")
    print(f"Time Taken: {end - start:.4f}s")
    
    if local_name == "Adventure Time Fionna Cake - S02E06.mkv":
        print("SUCCESS: Fast path generated correct name.")
    else:
        print(f"FAILURE: Expected 'Adventure Time Fionna Cake - S02E06.mkv', got '{local_name}'")

    # Test Case 2: Tricky file (Slow Path check)
    # "01.mkv" alone usually fails local unless folder context is good. 
    # But here we just want to ensure generate_name_from_guess returns None for it.
    
    print("\n--- Test 2: Incomplete Info ---")
    guess_bad = renamer.parse_filename("01.mkv")
    local_name_bad = renamer.generate_name_from_guess(guess_bad, ".mkv")
    
    if local_name_bad is None:
        print("SUCCESS: Correctly identified need for fallback.")
    else:
        print(f"FAILURE: Should be None, got {local_name_bad}")

if __name__ == "__main__":
    verify_speed()
