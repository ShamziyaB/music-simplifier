"""Правила упрощения.

Каждое правило — отдельная функция. Она меняет партию «на месте»
и записывает в журнал (ChangeLog), что именно было изменено.

Уровни:
  * easy        — трезвучия, без удвоений, удобный диапазон.
  * medium      — до четырёх звуков в аккорде, без удвоений.
  * medium_hard — до пяти звуков, удвоения сохраняются.

Ритм и фактура пока не упрощаются: это следующий этап проекта.
"""

from dataclasses import dataclass, field

from music21 import chord, note, stream

from .analysis import mean_pitch
from .levels import LevelConfig, get_level

# Диапазоны в MIDI-номерах (60 = до первой октавы, C4).
RIGHT_HAND_RANGE = (60, 79)  # C4 – G5
LEFT_HAND_RANGE = (43, 60)   # G2 – C4


@dataclass
class ChangeLog:
    entries: list[str] = field(default_factory=list)
    ranges: dict[int, tuple[int, int]] = field(default_factory=dict)
    level: str = "medium"

    def add(self, rule: str, part_name: str, measure, detail: str) -> None:
        where = f"такт {measure}" if measure is not None else "такт ?"
        self.entries.append(f"[{rule}] {part_name}, {where}: {detail}")

    def count(self, rule: str) -> int:
        return sum(1 for e in self.entries if e.startswith(f"[{rule}]"))

    @property
    def total(self) -> int:
        return len(self.entries)


def _part_name(part: stream.Stream) -> str:
    return str(part.partName or part.id or "Part")


# --------------------------------------------------------------------------
# Правило 1: упрощение аккордов
# --------------------------------------------------------------------------

# Чем меньше число, тем важнее звук для простого аккорда.
# 0 — основной тон, 1 — терция, 2 — квинта, 3 — септима, 4 — остальные.
_INTERVAL_PRIORITY = {
    0: 0,
    3: 1,
    4: 1,
    6: 2,
    7: 2,
    8: 2,
    10: 3,
    11: 3,
    1: 4,
    2: 4,
    5: 4,
    9: 4,
}


def _root_pitch_class(ch: chord.Chord) -> int | None:
    try:
        return ch.root().pitchClass
    except Exception:
        # Для нестандартных созвучий считаем основным самый низкий звук.
        if not ch.pitches:
            return None
        return min(ch.pitches, key=lambda p: p.ps).pitchClass


def reduce_chords(
    part: stream.Stream,
    log: ChangeLog,
    max_notes: int = 3,
    remove_doublings: bool = True,
) -> int:
    """Оставить в аккордах не больше ``max_notes`` важных звуков.

    Основной тон, терция и квинта имеют приоритет. Если ``remove_doublings``
    включено, из нескольких нот с одинаковым названием остаётся самая низкая.
    Возвращает число изменённых аккордов.
    """
    changed = 0
    for ch in list(part.recurse().getElementsByClass(chord.Chord)):
        if len(ch.pitches) < 2:
            continue

        root_pc = _root_pitch_class(ch)
        if root_pc is None:
            continue

        candidates = []
        for p in ch.pitches:
            interval = (p.pitchClass - root_pc) % 12
            candidates.append((_INTERVAL_PRIORITY.get(interval, 4), p.ps, p.pitchClass, p))

        if remove_doublings:
            by_pitch_class: dict[int, tuple[int, float, int, object]] = {}
            for candidate in candidates:
                _, ps, pc, _pitch = candidate
                if pc not in by_pitch_class or ps < by_pitch_class[pc][1]:
                    by_pitch_class[pc] = candidate
            candidates = list(by_pitch_class.values())

        candidates.sort(key=lambda item: (item[0], item[1]))
        new_pitches = sorted((item[3] for item in candidates[:max_notes]), key=lambda p: p.ps)

        if len(new_pitches) < 2:
            continue
        if [p.ps for p in new_pitches] == sorted(p.ps for p in ch.pitches):
            continue

        before = " ".join(p.nameWithOctave for p in ch.pitches)
        ch.pitches = tuple(new_pitches)
        after = " ".join(p.nameWithOctave for p in ch.pitches)
        log.add("chord_reduction", _part_name(part), ch.measureNumber, f"{before} -> {after}")
        changed += 1
    return changed


def chords_to_triads(part: stream.Stream, log: ChangeLog) -> int:
    """Совместимый вариант правила: сложные аккорды -> трезвучия."""
    return reduce_chords(part, log, max_notes=3, remove_doublings=True)


# --------------------------------------------------------------------------
# Правило 2: перенос в удобный диапазон
# --------------------------------------------------------------------------

def _octave_shift(bottom: float, top: float, low: int, high: int) -> int:
    """Сколько октав (целое число) надо прибавить, чтобы уложиться в диапазон."""
    shift = 0
    while top + shift * 12 > high:
        shift -= 1
    while bottom + shift * 12 < low:
        shift += 1
    return shift


def fit_to_range(part: stream.Stream, low: int, high: int, log: ChangeLog) -> int:
    """Сдвинуть на октаву(ы) ноты и аккорды, выходящие за диапазон [low, high].

    Возвращает число сдвинутых нот/аккордов.
    """
    changed = 0
    for el in list(part.recurse().notes):
        pitches = el.pitches
        bottom = min(p.ps for p in pitches)
        top = max(p.ps for p in pitches)
        if bottom >= low and top <= high:
            continue
        shift = _octave_shift(bottom, top, low, high)
        if shift == 0:
            continue
        if isinstance(el, note.Note):
            before = el.pitch.nameWithOctave
        else:
            before = " ".join(p.nameWithOctave for p in el.pitches)
        el.transpose(shift * 12, inPlace=True)
        if isinstance(el, note.Note):
            after = el.pitch.nameWithOctave
        else:
            after = " ".join(p.nameWithOctave for p in el.pitches)
        log.add("fit_to_range", _part_name(part), el.measureNumber,
                f"{before} -> {after} ({shift:+d} окт.)")
        changed += 1
    return changed


def range_for_part(part: stream.Stream) -> tuple[int, int]:
    """Определить, какая это рука, по средней высоте нот."""
    mean = mean_pitch(part)
    if mean is not None and mean < 60:
        return LEFT_HAND_RANGE
    return RIGHT_HAND_RANGE


# --------------------------------------------------------------------------
# Всё вместе
# --------------------------------------------------------------------------

def simplify_score(
    score: stream.Score,
    level: str | LevelConfig | None = None,
) -> ChangeLog:
    """Применить правила выбранного уровня ко всем партиям.

    Меняет ``score`` на месте. Исходный объект нужно предварительно скопировать.
    """
    config = level if isinstance(level, LevelConfig) else get_level(level)
    log = ChangeLog(level=config.key)

    for index, part in enumerate(score.parts):
        low, high = range_for_part(part)
        log.ranges[index] = (low, high)
        reduce_chords(part, log, config.max_chord_notes, config.remove_doublings)
        fit_to_range(part, low, high, log)

    return log
