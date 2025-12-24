import PyInstaller.__main__
import os
import shutil
import customtkinter

# Get location of customtkinter to bundle its assets (json, themes)
ctk_path = os.path.dirname(customtkinter.__file__)

print("Building AutoTitlePro...")
print(f"CustomTkinter Path: {ctk_path}")

PyInstaller.__main__.run([
    'src/main.py',
    '--name=AutoTitlePro',
    '--onefile',
    '--windowed',  # No console window
    '--icon=NONE', # TODO: Add icon if user provides one
    '--add-data', f'{ctk_path};customtkinter/', # Include CTK assets
    '--hidden-import=imdb',
    '--hidden-import=guessit',
    '--hidden-import=PIL._tkinter_finder',
    '--clean',
    '--noconfirm',
])

print("Build Complete! Check 'dist/AutoTitlePro.exe'")
