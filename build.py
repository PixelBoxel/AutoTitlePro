import PyInstaller.__main__
import os
import shutil
import customtkinter
import babelfish
import guessit

# Get location of packages to bundle their assets
ctk_path = os.path.dirname(customtkinter.__file__)
babel_path = os.path.dirname(babelfish.__file__)
guessit_path = os.path.dirname(guessit.__file__)

print("Building AutoTitlePro...")
print(f"CustomTkinter Path: {ctk_path}")
print(f"Babelfish Path: {babel_path}")
print(f"Guessit Path: {guessit_path}")

PyInstaller.__main__.run([
    'src/main.py',
    '--name=AutoTitlePro',
    '--onefile',
    '--windowed',  # No console window
    '--icon=assets/icon.ico', 
    '--add-data', f'{ctk_path};customtkinter/', # Include CTK assets
    '--add-data', f'{babel_path};babelfish/',   # Include Babelfish data (fixes 'iso-3166-1.txt' error)
    '--add-data', f'{guessit_path};guessit/',   # Include Guessit data (fixes 'options.json' error)
    '--add-data', 'assets/icon.ico;assets/',    # Include Icon
    '--hidden-import=imdb',
    '--hidden-import=guessit',
    '--hidden-import=babelfish',
    '--hidden-import=PIL._tkinter_finder',
    '--clean',
    '--noconfirm',
])

print("Build Complete! Check 'dist/AutoTitlePro.exe'")
