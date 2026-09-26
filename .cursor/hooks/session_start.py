#!/usr/bin/env python3
"""Inject .cursor/handoff.md into a new Agent session."""

import json
import os
import sys
from pathlib import Path

MAX_CHARS = 12000


def emit(payload: dict) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


def main() -> None:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        event = {}

    # Ask and edit chats should stay free of the standing build orders.
    if event.get("composer_mode") in ("ask", "edit"):
        emit({})
        return

    root = Path(os.environ.get("CURSOR_PROJECT_DIR") or Path(__file__).resolve().parents[2])
    handoff = root / ".cursor" / "handoff.md"
    if not handoff.is_file():
        emit({})
        return

    text = handoff.read_text(encoding="utf-8").strip()
    if not text:
        emit({})
        return

    note = (
        "Önceki oturumlardan kalan görev ve dersler (.cursor/handoff.md). "
        "Yeni bir denemeye başlamadan önce bunu oku. Burada geri alındığı yazan "
        "yolu tekrarlama. Her anlamlı turdan sonra aynı dosyaya ekle; dosyanın "
        "üstünü silme. Görev satırında dur yazıyorsa yeni işe başlama."
    )
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS].rstrip()
        note += " Dosya uzun olduğu için bağlam kesildi; tam metin .cursor/handoff.md içinde."

    emit({"additional_context": note + "\n\n" + text})


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.stdout.write("{}\n")
        sys.exit(0)
