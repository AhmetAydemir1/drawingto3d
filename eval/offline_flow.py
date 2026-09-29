"""Cevrimdisi akis, etiket karsilastirmasiyla: read -> soru -> incele -> build -> 'dogru parca mi'.

Review6 ve kontrat ayni seyi istiyor: uretilen dosya urun basarisi degildir. Bu arac her v2 girdi icin urun
zincirini gercekten kosturur ve insa edilen kati vaka etiketleriyle karsilastirir:

* `bbox`   : en/boy/yukseklik kumesi (siralanmis, %1 tolerans)
* `hacim`  : etikete gore oran
* `delik`  : silindir sayisi ve caplari (etiketin delik ozellikleri)
* `cep`    : hacim farki cebin var olup olmadigini gosterir; program satirlari da yazilir

Sorularin cevabi burada **olcum icin** uygulanir (olcekten gelen tam sayi adayi) ve hangi cevabin
uygulandigi kayda gecer: cevrimdisi akista o adimi kullanici yapar, arac yalnizca olcmek icin taklit eder.
Incelenmemis tabloyla kurulumun reddedildigi de olculur (kapi tutuyor mu).

Kullanim: `python eval/offline_flow.py [vaka ...]`
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "out/lab/data/v2"
OUT = ROOT / "out/lab/product-goal/offline-flow"
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src")}


def _cli(*args: str, timeout: int = 900) -> dict:
    proc = subprocess.run([sys.executable, "-m", "drawingto3d", *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=timeout, env=ENV)
    text = ((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()
    return {"exit": proc.returncode, "tail": text[-3:]}


def _compare(geometry: dict, labels: dict) -> dict:
    """Insa edilen kati etiketlerle: bbox kumesi, hacim orani, delik sayisi ve caplari."""
    built_box = sorted(round(float(value), 3) for value in geometry.get("size") or [])
    label_box = sorted(round(float(value), 3) for value in labels.get("bbox_size") or [])
    box_ok = (len(built_box) == len(label_box) == 3
              and all(abs(a - b) <= 0.01 * max(b, 1.0) for a, b in zip(built_box, label_box)))
    volume = float(geometry.get("volume") or 0.0)
    label_volume = float(labels.get("volume_mm3") or 0.0)
    diameter = sorted(round(float(row[0]), 3) for row in geometry.get("cylinders") or [])
    label_holes = sorted(round(float(f["diameter_mm"]), 3) for f in labels.get("features") or []
                         if f.get("kind") == "hole" and f.get("diameter_mm"))
    return {
        "bbox_insa": built_box, "bbox_etiket": label_box, "bbox_uyuyor": box_ok,
        "hacim_insa": round(volume, 2), "hacim_etiket": round(label_volume, 2),
        "hacim_orani": round(volume / label_volume, 4) if label_volume else None,
        "delik_caplari_insa": diameter, "delik_caplari_etiket": label_holes,
        "delik_sayisi_insa": len(diameter), "delik_sayisi_etiket": len(label_holes),
        "cep_etiket": [f for f in labels.get("features") or [] if f.get("kind") == "pocket"],
    }


def _case(name: str) -> dict:
    case_dir = DATA / name
    drawing = case_dir / "drawing.png"
    labels = json.loads((case_dir / "labels.json").read_text(encoding="utf-8"))
    work = OUT / name
    work.mkdir(parents=True, exist_ok=True)
    row: dict = {"case": name, "labels": {"bbox": labels.get("bbox_size"), "volume": labels.get("volume_mm3")}}

    row["read"] = _cli("read", str(drawing), str(work))
    records = json.loads((work / "records.json").read_text(encoding="utf-8")) if \
        (work / "records.json").exists() else []
    questions = json.loads((work / "questions.json").read_text(encoding="utf-8")) if \
        (work / "questions.json").exists() else []
    row["kayitlar"] = [[r["span_id"], r["text"], r["value"]] for r in records]
    row["sorular"] = questions

    # Incelenmemis tabloyla kurulum reddedilmeli: kapi tutuyor mu?
    row["incelenmemis_kurulum"] = _cli("build", str(drawing), str(work / "records.json"),
                                       str(work / "build-unreviewed"))

    # Kullanicinin yaptigi is: sorulari cevapla, tabloyu incele.
    answered = []
    by_id = {r["span_id"]: r for r in records}
    for question in questions:
        record = by_id.get(question["span_id"])
        if record is not None and question.get("tam_sayi_adayi") is not None:
            answered.append([question["span_id"], record["text"], question["tam_sayi_adayi"]])
            record["text"], record["value"] = f"{question['tam_sayi_adayi']:g}", float(question["tam_sayi_adayi"])
    for record in records:
        record["source"] = "user"
    reviewed = work / "records-reviewed.json"
    reviewed.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    row["cevaplar"] = answered

    build_dir = work / "build"
    row["kurulum"] = _cli("build", str(drawing), str(reviewed), str(build_dir))
    geometry_path = build_dir / "geometry.json"
    program_path = build_dir / "program.py"
    if geometry_path.exists():
        geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
        row["geometri"] = _compare(geometry, labels)
        row["program"] = program_path.read_text(encoding="utf-8").strip().splitlines() if \
            program_path.exists() else []
        row["step"] = [str(p.relative_to(ROOT)) for p in sorted(build_dir.glob("*.step"))]
        row["step_bytes"] = [p.stat().st_size for p in sorted(build_dir.glob("*.step"))]
    else:
        row["geometri"] = None
    return row


def main(argv: list[str]) -> int:
    names = argv or sorted(path.name for path in DATA.glob("pilot-*"))
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [_case(name) for name in names]
    (OUT / "offline-flow.json").write_text(json.dumps({"cases": rows}, ensure_ascii=False, indent=2) + "\n",
                                           encoding="utf-8")
    print(f"{'vaka':<16} {'kayit':>5} {'soru':>4} {'kapi':>5} {'step':>4} {'bbox':>6} {'hacim':>7}  program")
    for row in rows:
        geometry = row.get("geometri") or {}
        program = " | ".join(row.get("program") or [])[:64]
        print(f"{row['case']:<16} {len(row['kayitlar']):>5} {len(row['sorular']):>4} "
              f"{'RED' if row['incelenmemis_kurulum']['exit'] else 'GECTI':>5} "
              f"{len(row.get('step') or []):>4} "
              f"{('ok' if geometry.get('bbox_uyuyor') else 'FARKLI'):>6} "
              f"{str(geometry.get('hacim_orani')):>7}  {program}")
    print(f"\nkayit: {OUT / 'offline-flow.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
