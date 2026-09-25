from pathlib import Path

from drawingto3d.legacy.solid import box_step


def test_box_step_is_valid(tmp_path: Path):
    path = tmp_path / "box.step"
    box_step(path)
    text = path.read_text(errors="ignore")
    assert "ISO-10303-21" in text
