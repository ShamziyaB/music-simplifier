"""Сохранение результата.

Этап 1: MusicXML и текстовый отчёт. MIDI — опционально.
PDF (через MuseScore CLI или Verovio) — Этап 3.
"""

from pathlib import Path

from music21 import stream


def export_musicxml(score: stream.Score, path: str) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return str(score.write("musicxml", fp=path))


def export_midi(score: stream.Score, path: str) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return str(score.write("midi", fp=path))


def write_report(text: str, path: str) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")
    return path
