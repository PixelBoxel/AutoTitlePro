from guessit import guessit

filenames = [
    "01 A Nightmare On Elm Street - Horror 1984 Eng Subs 1080p [H264-mp4].mp4",
    "02 A Nightmare On Elm Street 2 Freddys Revenge - Horror 1985 Eng Subs 1080p [H264-mp4].mp4",
    "10 Cloverfield Lane (2016)(0).mkv",
    "1917.2019.1080p.WEB-DL.H264.AC3-EVO.mkv",
    "2001 A Space Odyssey (1968)(0).mp4"
]

print(f"{'Filename':<80} | {'Title':<40} | {'Guessit Output'}")
print("-" * 150)

for f in filenames:
    g = guessit(f)
    print(f"{f:<80} | {str(g.get('title')):<40} | {g}")
