"""Чтение нотных файлов.

Этап 1: только MusicXML. MIDI и распознавание PDF/картинок — позже.
"""

from pathlib import Path

from music21 import converter, stream

MUSICXML_EXTENSIONS = {".musicxml", ".xml", ".mxl"}
MIDI_EXTENSIONS = {".mid", ".midi"}
IMAGE_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


def load_score(path: str) -> stream.Score:
    """Загрузить ноты из файла и вернуть объект music21 Score."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    ext = file_path.suffix.lower()

    if ext in MUSICXML_EXTENSIONS:
        parsed = converter.parse(str(file_path))
        # Иногда music21 возвращает Part или Opus вместо Score — приводим к Score.
        if isinstance(parsed, stream.Opus):
            parsed = parsed.scores[0]
        if isinstance(parsed, stream.Part):
            score = stream.Score()
            score.insert(0, parsed)
            return score
        return parsed

    if ext in MIDI_EXTENSIONS:
        raise NotImplementedError(
            "MIDI пока не поддерживается (запланировано на следующие этапы). "
            "Используйте MusicXML."
        )

    if ext in IMAGE_EXTENSIONS:
        raise NotImplementedError(
            "Распознавание PDF/картинок (OMR) пока не реализовано (Этап 4). "
            "Внимание: распознавание нот может ошибаться, результат нужно проверять вручную. "
            "Пока экспортируйте ноты в MusicXML из MuseScore или другого редактора."
        )

    raise ValueError(f"Неизвестный формат файла: {ext}")
