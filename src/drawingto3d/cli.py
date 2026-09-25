"""Command line: drawingto3d sayfa.png out/"""

from __future__ import annotations

import argparse
import json

from drawingto3d.pipeline import convert_drawing


def main() -> None:
    parser = argparse.ArgumentParser(description="PDF veya PNG teknik çizimden STEP")
    parser.add_argument("drawing")
    parser.add_argument("out_dir")
    parser.add_argument("--answers", help="rol=değer çiftleri, virgülle")
    args = parser.parse_args()
    answers = {}
    if args.answers:
        for item in args.answers.split(","):
            role, value = item.split("=")
            answers[role.strip()] = float(value)
    result = convert_drawing(args.drawing, args.out_dir, answers=answers or None)
    print(json.dumps({"accepted": result.audit.accepted, "questions": [q.model_dump() for q in result.questions], "step": result.step_path}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
