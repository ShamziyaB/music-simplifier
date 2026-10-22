"""Командная строка: python -m simplifier входной_файл.musicxml"""

import argparse
import copy
from pathlib import Path

from .analysis import analyze
from .export import export_midi, export_musicxml, write_report
from .levels import LEVELS, get_level
from .parser import load_score
from .report import COPYRIGHT_NOTICE, build_report
from .simplify import simplify_score
from .validate import validate


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Упрощение нот для начинающих.")
    parser.add_argument("input", help="Входной файл (.musicxml, .xml, .mxl)")
    parser.add_argument(
        "-o",
        "--output",
        help="Куда сохранить результат (по умолчанию рядом с входным файлом)",
    )
    parser.add_argument(
        "--level",
        choices=sorted(LEVELS),
        default="medium",
        help="Уровень сложности: easy, medium или medium_hard (по умолчанию medium)",
    )
    parser.add_argument("--midi", action="store_true", help="Дополнительно сохранить MIDI")
    args = parser.parse_args(argv)

    print(COPYRIGHT_NOTICE, "\n")

    try:
        score = load_score(args.input)
    except (FileNotFoundError, NotImplementedError, ValueError) as exc:
        print(f"Ошибка: {exc}")
        return 1

    config = get_level(args.level)
    info = analyze(score)
    simplified = copy.deepcopy(score)  # оригинал не трогаем
    log = simplify_score(simplified, config)
    validation = validate(score, simplified, log)

    src = Path(args.input)
    out = Path(args.output) if args.output else src.with_name(
        f"{src.stem}_{config.key}_simplified.musicxml"
    )
    export_musicxml(simplified, str(out))
    if args.midi:
        export_midi(simplified, str(out.with_suffix(".mid")))

    report_text = build_report(info, log, validation, config.key)
    report_path = out.with_suffix(".report.txt")
    write_report(report_text, str(report_path))

    print(report_text)
    print(f"\nНоты сохранены: {out}")
    print(f"Отчёт сохранён: {report_path}")
    return 0 if validation.ok else 2
