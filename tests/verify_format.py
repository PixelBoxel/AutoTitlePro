import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from renamer import AutoRenamer

def test_formats():
    renamer = AutoRenamer()
    
    # Fake guess data
    guess = {
        'title': 'adventure time',
        'season': 1,
        'episode': 5,
        'type': 'episode',
        'year': 2010
    }
    ext = ".mkv"
    
    # Test Cases
    formats = [
        "{Title} - S{season}E{episode}",       # Default
        "{Title} {season}x{episode}",          # 1x05
        "{Title} - {season}x{episode}",        # - 1x05
        "{title} s{season}e{episode}",         # lowercase title
        "{Title} ({year}) - S{season}E{episode}" # With Year
    ]
    
    print(f"Original Guess: {guess}")
    
    for fmt in formats:
        result = renamer.generate_name_from_guess(guess, ext, format_string=fmt)
        print(f"Format: '{fmt}' -> Result: '{result}'")
        
        # Basic assertions
        if "{Title}" in fmt: assert "Adventure Time" in result
        if "x" in fmt: assert "x" in result

if __name__ == "__main__":
    test_formats()
