# AutoTitlePro

**The Ultimate Video Library Librarian.**

AutoTitlePro is a powerful Windows utility that automatically identifies, renames, and organizes your video files (Movies & TV Shows) using a combination of local heuristics, context inference, and IMDb metadata.

**Version**: v2025.12.24.01

## 🚀 Key Features

### 🧠 Smart Identificaton
*   **Fast Path (Local)**: Instantly renames files that already contain valid Title/Season/Episode data, removing "garbage" tags (1080p, x265, etc.) without waiting for online search.
*   **Online Search**: Uses `duckduckgo-search` + `IMDb` to find metadata for ambiguous filenames (e.g., `01.mkv`).
*   **Context Inference**: If internet search fails for a file, it intelligently "fills in the gaps" using successful matches from neighbor files in the same folder.

### 📂 Deep Organization & Hygiene
*   **Strict Flattening**: Enforces a clean `Show Name` > `Show Name - Season X` > `Files` hierarchy. It detects and fixes recursive/nested folders (e.g. `Halo/halo - season 2/Halo...`) by pulling files up to the top level.
*   **Uniform Capitalization**: Automatically renames folders to **Title Case** (e.g. `halo` -> `Halo`, `season 1` -> `Season 1`) to ensure your library looks professional and consistent.
*   **Loose File Cleanup**: Moves files from generic folders (like `Downloads`) into their correct Show/Season directories.
*   **Merging**: Consolidates scattered files into existing show folders seamlessly.

### 🛡️ Safety & Control
*   **Review First**: "Unknown" or low-confidence matches are automatically sorted to the top for review.
*   **Manual Selection**: Use dropdown menus to choose from multiple metadata candidates if the default guess is wrong.
*   **Non-Destructive**: Files marked "Unknown" are skipped by default.
*   **Organize Only**: If a file is already named correctly, the app skips renaming (saving time) but *still* fixes its folder structure and casing.

## 📝 Naming Conventions

*   **Files**: `Show Name - SXXEXX.ext` (e.g., `Adventure Time - S01E01.mkv`)
*   **Movies**: `Title (Year).ext` (e.g., `The Matrix (1999).mp4`)
*   **Folders**: `Show Name - Season X` (e.g., `Adventure Time - Season 1`)

## 📦 Installation

1.  **Install Python 3.10+**.
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## 🎮 Usage

1.  **Run the App**:
    ```bash
    python src/main.py
    ```
2.  **Select Directory**: Choose the folder containing your chaotic video files.
3.  **Review**:
    *   **Green**: Ready to rename/organize.
    *   **Red**: Unknown (will be skipped). use the dropdown to fix if needed.
    *   **Ready (Organize Only)**: Filename is perfect; will only move/fix folders.
4.  **Start Renaming**: Click the button and watch the magic happen.
5.  **Report**: A detailed stats popup will tell you how many files were moved, folders created, or **folders renamed (capitalization fixes)**.
