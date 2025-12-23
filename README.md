# AutoTitlePro

A Windows utility to rename video files using metadata from IMDb.

**Version**: v2025.12.23.22 (Reflects build date)

## Features
- Scans directories for video files.
- Uses `guessit` to extract filenames and `duckduckgo-search` to find IMDb metadata.
- Renames files to:
  - Movies: `Title (Year).ext`
  - TV Shows: `Title SxxExx.ext`

## Installation

1. Install Python 3.10+.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the application:
```bash
python src/main.py
```

1. Click "Select Directory" to choose a folder.
2. Wait for scanning and metadata fetching.
3. Review the proposed changes.
4. Click "Start Renaming".
