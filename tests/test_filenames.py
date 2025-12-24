from guessit import guessit

filenames = [
    "Adventure Time Fionna Cake S02E06 The Bird in the Clock 1080p AMZN WEB-DL DDP5 1 H 264-NTb.mkv",
    "Adventure Time Fionna and Cake S02E02 1080p AMZN WEB-DL DDP5 1 H 264 DUAL-BiOMA.mkv",
    "Adventure.Time.Fionna.Cake.S02E01.The.Hare.and.the.Sprout.1080p.HEVC.x265-MeGusta.mkv",
    "Adventure.Time.Fionna.Cake.S02E08.The.Insect.That.Sang.1080p.HEVC.x265-MeGusta.mkv"
]

print("--- Guessit Parsing Test ---")
for fn in filenames:
    g = guessit(fn)
    print(f"\nFile: {fn}")
    print(f"Title: {g.get('title')}")
    print(f"Season: {g.get('season')}")
    print(f"Episode: {g.get('episode')}")
    print(f"Type: {g.get('type')}")
