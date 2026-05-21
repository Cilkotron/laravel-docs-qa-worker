"""
clone_docs.py — Clone or update the Laravel docs repository.

Usage:
    python clone_docs.py
"""

from pathlib import Path
from git import Repo, GitCommandError

# Configuration
REPO_URL = "https://github.com/laravel/docs.git"
BRANCH = "13.x"  # Latest stable Laravel docs branch as of May 2026
CACHE_DIR = Path(__file__).parent / "cache" / "laravel-docs"


def clone_or_update():
    """Clone the Laravel docs repo, or pull latest if it already exists."""
    
    if CACHE_DIR.exists():
        print(f"Repository already exists at {CACHE_DIR}")
        print("Pulling latest changes...")
        repo = Repo(CACHE_DIR)
        origin = repo.remotes.origin
        origin.pull()
        print(f"Updated to latest commit on branch '{BRANCH}'")
    else:
        print(f"Cloning {REPO_URL} (branch: {BRANCH})...")
        CACHE_DIR.parent.mkdir(parents=True, exist_ok=True)
        Repo.clone_from(REPO_URL, CACHE_DIR, branch=BRANCH, depth=1)
        print(f"Cloned to {CACHE_DIR}")
    
    # Count markdown files
    md_files = list(CACHE_DIR.glob("*.md"))
    print(f"\nFound {len(md_files)} markdown files in the docs.")


if __name__ == "__main__":
    try:
        clone_or_update()
    except GitCommandError as e:
        print(f"Git error: {e}")
        exit(1)