# AutoTitlePro

**The Ultimate Video Library Librarian.**

AutoTitlePro is a powerful Windows utility that automatically identifies, renames, and organizes your video files (Movies & TV Shows) using a combination of local heuristics, context inference, and IMDb metadata.

**Version**: v2025.12.24.13

## 🚀 Key Features

### 🧠 Smart Identificaton & Comparison
*   **Massive Batch Processing**: Designed to handle `TV Show` root folders with hundreds of shows. It caches directory structures to ensure lightning-fast processing without repeated disk scans.
*   **Context Awareness**: "Learns" the show title from one successful file in a folder and instantly applies it to all siblings (e.g. `01.mkv` -> `Lost s01e01` -> all other files know they are `Lost`).
*   **Recursive Parent Standardization**: If a file is named `Video.mp4` inside `season 1` inside `halo`, the app intelligently looks UP to the **Parent Folder**, identifies it as `Halo`, and renames the folder hierarchy to match.

### 📂 Deep Organization & Hygiene
*   **Strict Flattening**: Enforces a clean `Show Name` > `Show Name - Season X` > `Files` hierarchy. It detects and fixes recursive/nested folders (e.g. `Halo/halo - season 2/Halo...`) by pulling files up to the top level.
*   **Universal Standardization**: Enforces **Title Case** on EVERY filename and folder (e.g. `breaking bad` -> `Breaking Bad`, `season 1` -> `Season 1`) for a perfectly uniform library.
*   **Companion File Support**: Automatically detects, renames, and moves subtitles (`.srt`, `.vtt`), artwork (`.jpg`, `.png`), and metadata (`.nfo`) files along with your videos. No orphan left behind!

### 🛡️ Safety & Control
*   **Folder Preview Tab**: A dedicated tab that shows you **Folder Renames** (Yellow) and **Folder Creations** (Green) *before* you click process.
*   **Settings Dashboard**: Fine-tune your experience. Toggle **Rename Files**, **Organize Folders**, **Title Case**, or **Dark Mode**.
*   **Review First**: "Unknown" or low-confidence matches are automatically sorted to the top for review.
*   **Non-Destructive**: Files marked "Unknown" are skipped by default.

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
2.  **Select Directory**: Point it at your root `TV Shows` folder for a full library cleanup, or a specific show folder.
3.  **Review**:
    *   **Green**: Ready to rename/organize.
    *   **Ready (Cached)**: Instantly identified using folder context.
    *   **Red**: Unknown (will be skipped).
4.  **Start Renaming**: Click the button and watch the magic happen.
