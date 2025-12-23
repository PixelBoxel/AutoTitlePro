from guessit import guessit
import os

def test_path(path):
    print(f"\n--- Testing Path: {path} ---")
    
    # Test 1: Filename only
    filename = os.path.basename(path)
    g_file = guessit(filename)
    print(f"Filename only guess: title='{g_file.get('title')}' season={g_file.get('season')} episode={g_file.get('episode')}")

    # Test 2: Full path
    # guessit behaves differently if you pass it 'files' (filename) vs strings that look like paths
    g_path = guessit(path)
    print(f"Full path guess:     title='{g_path.get('title')}' season={g_path.get('season')} episode={g_path.get('episode')}")

paths_to_test = [
    r"C:\TV Shows\Adventure Time Fionna and Cake\Season 1\S01E01.mkv",
    r"C:\TV Shows\Adventure Time Fionna and Cake - Season 1\episode 1.mkv",
    r"C:\Downloads\New Girl\Season 4\New.Girl.4x14.mkv",
    # Ambiguous filename, clear folder
    r"C:\TV Shows\Breaking Bad\Season 5\01.mkv" 
]

for p in paths_to_test:
    test_path(p)
