"""Анализ нот: тональность, размер, темп, диапазоны партий."""

from dataclasses import dataclass, field

from music21 import meter, stream, tempo


@dataclass
class PartInfo:
    name: str
    note_count: int
    lowest: str | None
    highest: str | None
    mean_ps: float | None  # средняя высота звука (MIDI-номер), нужна чтобы отличить правую руку от левой


@dataclass
class ScoreInfo:
    key: str
    time_signature: str | None
    tempo_bpm: float | None
    parts: list[PartInfo] = field(default_factory=list)


def _all_pitches(part: stream.Stream):
    """Все высоты звуков партии (аккорды разворачиваются в отдельные звуки)."""
    result = []
    for el in part.recurse().notes:
        result.extend(el.pitches)
    return result


def mean_pitch(part: stream.Stream) -> float | None:
    pitches = _all_pitches(part)
    if not pitches:
        return None
    return sum(p.ps for p in pitches) / len(pitches)


def analyze_part(part: stream.Stream) -> PartInfo:
    pitches = _all_pitches(part)
    name = part.partName or part.id or "Part"
    if not pitches:
        return PartInfo(str(name), 0, None, None, None)
    low = min(pitches, key=lambda p: p.ps)
    high = max(pitches, key=lambda p: p.ps)
    return PartInfo(
        name=str(name),
        note_count=len(pitches),
        lowest=low.nameWithOctave,
        highest=high.nameWithOctave,
        mean_ps=sum(p.ps for p in pitches) / len(pitches),
    )


def analyze(score: stream.Score) -> ScoreInfo:
    """Определить тональность, размер, темп и диапазон каждой партии."""
    key = score.analyze("key")  # алгоритм Креншоу–Шмуклера в music21

    ts = score.recurse().getElementsByClass(meter.TimeSignature).first()
    mm = score.recurse().getElementsByClass(tempo.MetronomeMark).first()

    return ScoreInfo(
        key=f"{key.tonic.name} {key.mode}",
        time_signature=ts.ratioString if ts else None,
        tempo_bpm=float(mm.getQuarterBPM()) if mm and mm.getQuarterBPM() else None,
        parts=[analyze_part(p) for p in score.parts],
    )
