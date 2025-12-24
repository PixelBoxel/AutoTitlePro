# AutoTitlePro

**The Ultimate Video Library Librarian.**

AutoTitlePro is a powerful Windows utility that automatically identifies, renames, and organizes your video files (Movies & TV Shows) using a combination of local heuristics, context inference, and IMDb metadata.

**Version**: v2025.12.24.05

## 🚀 Key Features

### 🧠 Smart Identificaton & Comparison
*   **Massive Batch Processing**: Designed to handle `TV Show` root folders with hundreds of shows. It caches directory structures to ensure lightning-fast processing without repeated disk scans.
*   **Context Awareness**: "Learns" the show title from one successful file in a folder and instantly applies it to all siblings (e.g. `01.mkv` -> `Lost s01e01` -> all other files know they are `Lost`).
*   **Parent Fallback**: If a file is named `Video.mp4`, the app intelligently looks at the **Parent Folder** to identify the show.

### 📂 Deep Organization & Hygiene
*   **Strict Flattening**: Enforces a clean `Show Name` > `Show Name - Season X` > `Files` hierarchy. It detects and fixes recursive/nested folders (e.g. `Halo/halo - season 2/Halo...`) by pulling files up to the top level.
*   **Universal Standardization**: Enforces **Title Case** on EVERY filename and folder (e.g. `breaking bad` -> `Breaking Bad`, `season 1` -> `Season 1`) for a perfectly uniform library.
*   **Loose File Cleanup**: Moves files from generic folders (like `Downloads`) into their correct Show/Season directories.

### 🛡️ Safety & Control
*   **Review First**: "Unknown" or low-confidence matches are automatically sorted to the top for review.
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
2.  **Select Directory**: Point it at your root `TV Shows` folder for a full library cleanup, or a specific show folder.
3.  **Review**:
    *   **Green**: Ready to rename/organize.
    *   **Ready (Cached)**: Instantly identified using folder context.
    *   **Red**: Unknown (will be skipped).
4.  **Start Renaming**: Click the button and watch the magic happen.
