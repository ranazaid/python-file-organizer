"""File-organizer automation.

Sorts a messy folder (e.g. ~/Downloads) into category subfolders by file type.
It detects exact duplicates by content hash, writes an undo log, and can be
scheduled (cron/launchd) or run in --watch mode to organize new files as they
land.

Usage:
    python organize.py ~/Downloads --dry-run        # preview, change nothing
    python organize.py ~/Downloads                  # organize
    python organize.py ~/Downloads --watch 10       # re-scan every 10 seconds
    python organize.py ~/Downloads --undo           # revert the last run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
import time
from datetime import datetime
from pathlib import Path

CATEGORIES: dict[str, set[str]] = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".svg"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".pages"},
    "Spreadsheets": {".xls", ".xlsx", ".csv", ".numbers"},
    "Slides": {".ppt", ".pptx", ".key"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "Audio": {".mp3", ".wav", ".m4a", ".flac"},
    "Video": {".mp4", ".mov", ".mkv", ".avi"},
    "Code": {".py", ".js", ".ts", ".json", ".html", ".css", ".php", ".kt", ".java"},
    "Installers": {".dmg", ".pkg", ".exe", ".apk"},
}
OTHER = "Other"
DUPLICATES = "_Duplicates"
LOG_NAME = ".organize-log.json"

log = logging.getLogger("organize")


def category_for(path: Path) -> str:
    ext = path.suffix.lower()
    return next((cat for cat, exts in CATEGORIES.items() if ext in exts), OTHER)


def file_hash(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def unique_destination(dest: Path) -> Path:
    """Avoid overwriting: report.pdf → report (1).pdf → report (2).pdf …"""
    if not dest.exists():
        return dest
    n = 1
    while True:
        candidate = dest.with_name(f"{dest.stem} ({n}){dest.suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def known_hashes(root: Path) -> dict[str, Path]:
    """Hashes of files already sorted into category folders, used for duplicate detection."""
    seen: dict[str, Path] = {}
    for folder in [*CATEGORIES, OTHER]:
        d = root / folder
        if d.is_dir():
            for f in d.iterdir():
                if f.is_file():
                    seen.setdefault(file_hash(f), f)
    return seen


def organize(root: Path, dry_run: bool = False) -> list[dict[str, str]]:
    moves: list[dict[str, str]] = []
    seen = known_hashes(root)

    for item in sorted(root.iterdir()):
        if not item.is_file() or item.name.startswith(".") or item.suffix in {".part", ".crdownload"}:
            continue  # skip hidden files and in-progress downloads
        digest = file_hash(item)
        target_dir = root / (DUPLICATES if digest in seen else category_for(item))
        dest = unique_destination(target_dir / item.name)

        log.info("%s %s → %s/", "[dry-run]" if dry_run else "move", item.name, target_dir.name)
        if not dry_run:
            target_dir.mkdir(exist_ok=True)
            shutil.move(str(item), dest)
            seen.setdefault(digest, dest)
        moves.append({"from": str(item), "to": str(dest)})

    if moves and not dry_run:
        (root / LOG_NAME).write_text(
            json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "moves": moves}, indent=2)
        )
    return moves


def undo(root: Path) -> int:
    log_file = root / LOG_NAME
    if not log_file.exists():
        log.warning("Nothing to undo.")
        return 0
    moves = json.loads(log_file.read_text())["moves"]
    restored = 0
    for m in reversed(moves):
        src, original = Path(m["to"]), Path(m["from"])
        if src.exists() and not original.exists():
            shutil.move(str(src), original)
            restored += 1
    log_file.unlink()
    # Tidy up category folders that the undo left empty.
    for folder in [*CATEGORIES, OTHER, DUPLICATES]:
        d = root / folder
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    return restored


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("folder", type=Path)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--undo", action="store_true")
    p.add_argument("--watch", type=int, metavar="SECONDS", help="re-scan every N seconds")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    root = args.folder.expanduser().resolve()
    if not root.is_dir():
        p.error(f"{root} is not a directory")

    if args.undo:
        print(f"Restored {undo(root)} file(s).")
        return

    if args.watch:
        log.info("Watching %s every %ss (Ctrl+C to stop)", root, args.watch)
        try:
            while True:
                organize(root, args.dry_run)
                time.sleep(args.watch)
        except KeyboardInterrupt:
            return

    moves = organize(root, args.dry_run)
    print(f"{'Would move' if args.dry_run else 'Moved'} {len(moves)} file(s).")


if __name__ == "__main__":
    main()
