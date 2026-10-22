"""Сервисный слой: обработка загруженного MusicXML без привязки к HTTP."""

from __future__ import annotations

import base64
import binascii
import copy
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from .analysis import analyze
from .export import export_midi, export_musicxml
from .levels import get_level
from .parser import MUSICXML_EXTENSIONS, load_score
from .report import build_report
from .simplify import simplify_score
from .validate import validate

MAX_FILE_BYTES = int(os.getenv("MAX_FILE_BYTES", str(3 * 1024 * 1024)))  # 3 МБ по умолчанию


def _safe_filename(filename: str) -> str:
    name = Path(filename or "upload.musicxml").name
    if not name:
        name = "upload.musicxml"
    suffix = Path(name).suffix.lower()
    if suffix not in MUSICXML_EXTENSIONS:
        allowed = ", ".join(sorted(MUSICXML_EXTENSIONS))
        raise ValueError(f"Неподдерживаемый формат. Загрузите файл: {allowed}.")
    return name


def _decode_content(content_base64: str) -> bytes:
    if not content_base64:
        raise ValueError("Файл пустой.")
    try:
        data = base64.b64decode(content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Не удалось прочитать файл: повреждён формат загрузки.") from exc
    if not data:
        raise ValueError("Файл пустой.")
    if len(data) > MAX_FILE_BYTES:
        megabytes = MAX_FILE_BYTES / (1024 * 1024)
        raise ValueError(f"Файл слишком большой. Максимальный размер — {megabytes:g} МБ.")
    return data


def _note_event_count(score) -> int:
    return sum(len(list(part.recurse().notes)) for part in score.parts)


def process_musicxml(filename: str, content_base64: str, level: str | None = None) -> dict:
    """Упростить MusicXML и вернуть JSON-совместимый результат.

    Исключения ``ValueError`` означают ошибку пользователя (битый файл,
    неподдерживаемый формат и т.п.).
    """
    config = get_level(level)
    safe_name = _safe_filename(filename)
    data = _decode_content(content_base64)

    with tempfile.TemporaryDirectory(prefix="music-simplifier-") as tmp:
        source = Path(tmp) / safe_name
        source.write_bytes(data)

        try:
            score = load_score(str(source))
            info = analyze(score)
        except Exception as exc:
            raise ValueError(
                "Не удалось прочитать ноты. Проверьте, что файл корректный MusicXML."
            ) from exc

        simplified = copy.deepcopy(score)
        log = simplify_score(simplified, config)
        validation = validate(score, simplified, log)

        output = Path(tmp) / "simplified.musicxml"
        export_musicxml(simplified, str(output))
        musicxml_text = output.read_text(encoding="utf-8")

        midi_base64: str | None = None
        try:
            midi_path = Path(tmp) / "simplified.mid"
            export_midi(simplified, str(midi_path))
            midi_base64 = base64.b64encode(midi_path.read_bytes()).decode("ascii")
        except Exception:
            # MIDI — приятный бонус; если экспорт не удался, отдаём хотя бы MusicXML.
            midi_base64 = None

        report_text = build_report(info, log, validation, config.key)
        notes_before = _note_event_count(score)
        notes_after = _note_event_count(simplified)

        return {
            "filename": safe_name,
            "level": config.key,
            "level_label": config.label,
            "musicxml": musicxml_text,
            "midi_base64": midi_base64,
            "report": report_text,
            "info": asdict(info),
            "validation": {
                "ok": validation.ok,
                "errors": validation.errors,
                "warnings": validation.warnings,
            },
            "stats": {
                "changes": log.total,
                "chord_reductions": log.count("chord_reduction"),
                "range_shifts": log.count("fit_to_range"),
                "parts": len(score.parts),
                "note_events_before": notes_before,
                "note_events_after": notes_after,
            },
        }
