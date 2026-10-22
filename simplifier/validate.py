"""Автоматическая проверка результата упрощения."""

from dataclasses import dataclass, field

from music21 import meter, stream

from .analysis import analyze
from .simplify import ChangeLog


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)    # серьёзные проблемы
    warnings: list[str] = field(default_factory=list)  # места, требующие внимания человека

    @property
    def ok(self) -> bool:
        return not self.errors


def _time_signature(score: stream.Score) -> str | None:
    ts = score.recurse().getElementsByClass(meter.TimeSignature).first()
    return ts.ratioString if ts else None


def _event_count(part: stream.Stream) -> int:
    return len(part.recurse().notes)


def validate(original: stream.Score, simplified: stream.Score, log: ChangeLog) -> ValidationReport:
    report = ValidationReport()

    # 1. Размер должен сохраниться.
    if _time_signature(original) != _time_signature(simplified):
        report.errors.append("Размер изменился.")

    # 2. Тональность: небольшие отличия возможны, поэтому это предупреждение.
    key_before = analyze(original).key
    key_after = analyze(simplified).key
    if key_before != key_after:
        report.warnings.append(
            f"Определённая тональность изменилась: {key_before} -> {key_after}. Проверьте гармонию."
        )

    # 3. Количество тактов и нотных событий не должно меняться.
    if len(original.parts) != len(simplified.parts):
        report.errors.append("Изменилось число партий.")
    else:
        for i, (po, ps) in enumerate(zip(original.parts, simplified.parts)):
            name = po.partName or po.id or f"Part {i}"
            if len(po.getElementsByClass(stream.Measure)) != len(ps.getElementsByClass(stream.Measure)):
                report.errors.append(f"{name}: изменилось число тактов.")
            if _event_count(po) != _event_count(ps):
                report.errors.append(f"{name}: изменилось число нот/аккордов (потеряна часть музыки?).")

            # 4. Диапазон.
            low, high = log.ranges.get(i, (0, 127))
            for el in ps.recurse().notes:
                if any(p.ps < low or p.ps > high for p in el.pitches):
                    report.warnings.append(
                        f"{name}, такт {el.measureNumber}: нота вне удобного диапазона "
                        "(аккорд шире диапазона руки?)."
                    )

            # 5. Слишком широкие аккорды для начинающего (больше октавы).
            for el in ps.recurse().notes:
                ps_values = [p.ps for p in el.pitches]
                if len(ps_values) > 1 and max(ps_values) - min(ps_values) > 12:
                    report.warnings.append(
                        f"{name}, такт {el.measureNumber}: аккорд шире октавы — может быть неудобно."
                    )

    return report
