import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.renamer import AutoRenamer
import time

renamer = AutoRenamer()

filenames = [
    "Hustle.avi",
    "Nobody.1080p.WEB-DL.DD5.1.H.264-EVO.mkv",
    "A.Quite.Place.Part.II.1080p.WEB-DL.DDP5.1.Atmos.H.264-CMRG.mkv",
    "The.Ice.Age.Adventures.of.Buck.Wild.1080p.DSNP.WEB-DL.DDP5.1.H.264-EVO.mkv",
    "Tesla.1080p.WEB-DL.DD5.1.H.264-EVO.mkv"
]

print(f"Testing {len(filenames)} filenames with AutoRenamer...")

for fname in filenames:
    print(f"\n--- Processing: {fname} ---")
    
    # 1. Parse
    guess = renamer.parse_filename(fname, media_type_hint='movie')
    print(f"Guess: {guess}")
    
    # 2. Sanitize
    # (This is called inside fetch_metadata now, but let's see what it does)
    if guess.get('title'):
        clean = renamer.sanitize_title(guess['title'])
        print(f"Sanitized Title: '{clean}'")
    else:
        # Fallback to sanitized filename
        clean = renamer.sanitize_title(fname)
        print(f"Sanitized Filename: '{clean}'")

    # 3. Fetch Metadata
    start = time.time()
    results = renamer.fetch_metadata(guess, file_path=fname)
    duration = time.time() - start
    
    print(f"Found {len(results)} results in {duration:.2f}s")
    for res in results[:3]:
        print(f" - {res.get('title')} ({res.get('year')}) [ID: {res.movieID}]")
