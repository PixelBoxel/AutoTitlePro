# AutoTitlePro

**The Ultimate Video Library Librarian.**

AutoTitlePro is a powerful Windows utility that automatically identifies, renames, and organizes your video files (Movies & TV Shows) using a combination of local heuristics, context inference, and IMDb metadata.

**Version**: v2025.12.24.11

## 🚀 Key Features

### 🧠 Smart Identificaton & Hierarchy
*   **Massive Batch Processing**: Designed to handle `TV Show` root folders with hundreds of shows. It caches directory structures to ensure lightning-fast processing without repeated disk scans.
*   **Contextual Title Inference (Rich Titles)**: Automatically detects "Rich Titles" from folder names (e.g. `Game of Thrones/GoT S01E01` -> `Game of Thrones`). It even cleans up suffixes like " - Season 1" to get the pure show title.
*   **Recursive Parent Standardization**: Identifies parent folder naming issues (`halo/season 1` -> `Halo/Season 1`) and standardizes the entire tree.

### 🎨 Visuals & Usability
*   **Split Result View**: A clean, two-column layout ("Original" vs "New") with valid row separators makes verification effortless.
*   **Smart Filter**: Automatically hides files that are already named correctly, so you only see what *actually* needs renaming.
*   **Status Indicators**: Always know if "older organization" is active with the header status ("Folder Sort: ON").

### ⚙️ Ultimate Customization
*   **Custom Rename Formats**: Define exactly how you want your files named using tokens like `{Title}`, `{season}`, `{year}` (e.g. `Show - S01E01` or `Show 1x01`).
*   **Custom Folder Formats**: Control your season folder structure (e.g. `Season 1`, `Series 1`, `S1`).

### 📂 Deep Organization & Hygiene
*   **Strict Flattening**: Enforces a clean `Show Name` > `Show Name - Season X` > `Files` hierarchy. It detects and fixes recursive/nested folders by pulling files up to the correct level.
*   **Universal Standardization**: Enforces **Title Case** on EVERY filename and folder.
*   **Companion File Support**: Automatically renames and moves subtitles (`.srt`, `.vtt`), artwork/posters (`.jpg`), and metadata (`.nfo`) along with video files.

### 🛡️ Crash Protection & Stability
*   **Active Watchdog**: A background monitor detecting hangs during large scans. If the app freezes for >30s, it automatically dumps a crash log for debugging.
*   **Large Library Support**: Optimized for libraries with 10,000+ files using smart pagination and non-blocking scanning.

### 👓 Visibility & Control
*   **Show Unchanged Files**: Toggle visibility of files that are already named correctly to verify your entire library.
*   **Folder Preview Tab**: A dedicated tab that shows you **Folder Renames** (Yellow) and **Folder Creations** (Green) *before* you click process.
*   **Review First**: "Unknown" or low-confidence matches are automatically sorted to the top for review.
*   **Non-Destructive**: Files marked "Unknown" are skipped by default.

## 📝 Naming Conventions

*   **Files**: `Show Name - SXXEXX.ext` (e.g., `Adventure Time - S01E01.mkv`)
*   **Movies**: `Title (Year).ext` (e.g., `The Matrix (1999).mp4`)
*   **Folders**: `Show Name - Season X` (e.g., `Adventure Time - Season 1`)

## 📦 Installation


1.  **Download**: [**Click here to download AutoTitlePro.exe**](https://github.com/PixelBoxel/AutoTitlePro/releases/download/v2025.12.24.11/AutoTitlePro.exe)
2.  **No Installation Required**: Just double-click the `.exe` to launch.
    *   *Note: First launch might be slower as it extracts resources.*

### 🛠️ Build from Source

1.  **Install Python 3.10+**.
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run**:
    ```bash
    python src/main.py
    ```
    *Or build your own .exe:*
    ```bash
    python build.py
    ```

## 🎮 Usage

1.  **Run the App**:
    ```bash
    python src/main.py
    ```
2.  **Select Directory**: Point it at your root `TV Shows` folder for a full library cleanup, or a specific show folder.
3.  **Review**:
    *   **Green**: Ready to rename/organize.
    *   **Ready (Cached)**: Instantly identified using folder context.
    *   **Red**: Unknown (will be skipped).
4.  **Start Renaming**: Click the button and watch the magic happen.
