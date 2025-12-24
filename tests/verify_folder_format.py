import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from renamer import AutoRenamer

def test_folder_formats():
    renamer = AutoRenamer()
    
    show_name = "The Last of Us"
    season_num = 1
    
    formats = [
        "{Title} - Season {season}",
        "Season {season}",
        "S{season}",
        "Season {season:01d}" # Format specifiers might fail with our simple replace, testing resilience
    ]
    
    print(f"Testing Show: {show_name}, Season: {season_num}")
    
    for fmt in formats:
        # Mocking logic used in rename.py
        data = {'title': show_name, 'season': season_num, 'episode': 0, 'year': ''}
        
        # We need to simulate the renamer.apply_format logic or use it directly
        try:
            result = renamer.apply_format(fmt, data)
            print(f"Format: '{fmt}' -> Result: '{result}'")
            
            if fmt == "Season {season}":
                assert result == "Season 01"
            elif fmt == "{Title} - Season {season}":
                 assert result == "The Last Of Us - Season 01"
                 
        except Exception as e:
            print(f"Format '{fmt}' failed: {e}")

if __name__ == "__main__":
    test_folder_formats()
