# Python — Automation: File Organizer

Sorts a cluttered folder such as `~/Downloads` into category subfolders. It
detects duplicates by content hash, never overwrites files, and keeps an undo log.
You can run it once, in watch mode, or on a schedule.

It uses only the standard library, so there is nothing to install for normal use.

## Run

```bash
python organize.py ~/Downloads --dry-run    # preview only
python organize.py ~/Downloads              # organize
python organize.py ~/Downloads --undo       # revert the last run
python organize.py ~/Downloads --watch 10   # keep organizing every 10 seconds
```

## Schedule it (cron, every hour)

```
0 * * * * /usr/bin/python3 /path/to/organize.py ~/Downloads >> ~/organize.log 2>&1
```

## Test

```bash
pip install pytest && pytest -q
```

## Concepts shown
- `pathlib` file operations and safe moves
- SHA-256 duplicate detection with streamed, chunked reads
- Collision-safe naming (`file (1).ext`)
- Dry-run mode and a JSON undo log
- A CLI with `argparse`, logging, and tests built on `tmp_path`

---

Portfolio reference implementation by [Zaid Mubbashar](https://github.com/ranazaid) · [zaid-mubbashar.vercel.app](https://zaid-mubbashar.vercel.app)
