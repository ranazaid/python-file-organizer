"""Run with: pytest -q  (uses only the standard library + pytest)."""
from pathlib import Path

import organize


def make(root: Path, name: str, content: bytes = b"x") -> Path:
    p = root / name
    p.write_bytes(content)
    return p


def test_sorts_by_category(tmp_path):
    make(tmp_path, "photo.JPG", b"img")
    make(tmp_path, "notes.pdf", b"doc")
    make(tmp_path, "weird.xyz", b"???")
    organize.organize(tmp_path)
    assert (tmp_path / "Images" / "photo.JPG").exists()
    assert (tmp_path / "Documents" / "notes.pdf").exists()
    assert (tmp_path / "Other" / "weird.xyz").exists()


def test_dry_run_changes_nothing(tmp_path):
    make(tmp_path, "a.png")
    moves = organize.organize(tmp_path, dry_run=True)
    assert len(moves) == 1
    assert (tmp_path / "a.png").exists()
    assert not (tmp_path / "Images").exists()


def test_duplicates_detected(tmp_path):
    make(tmp_path, "one.png", b"same")
    make(tmp_path, "two.png", b"same")
    organize.organize(tmp_path)
    assert (tmp_path / "Images" / "one.png").exists()
    assert (tmp_path / "_Duplicates" / "two.png").exists()


def test_name_collision_gets_suffix(tmp_path):
    (tmp_path / "Images").mkdir()
    make(tmp_path / "Images", "pic.png", b"old")
    make(tmp_path, "pic.png", b"new")
    organize.organize(tmp_path)
    assert (tmp_path / "Images" / "pic (1).png").read_bytes() == b"new"


def test_undo_restores(tmp_path):
    make(tmp_path, "a.png")
    make(tmp_path, "b.pdf")
    organize.organize(tmp_path)
    assert organize.undo(tmp_path) == 2
    assert (tmp_path / "a.png").exists() and (tmp_path / "b.pdf").exists()
    assert not (tmp_path / "Images").exists()
