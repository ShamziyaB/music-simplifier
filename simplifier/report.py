"""Формирование текстового отчёта об упрощении."""

from .analysis import ScoreInfo
from .levels import get_level
from .simplify import ChangeLog
from .validate import ValidationReport

COPYRIGHT_NOTICE = (
    "Только для личного учебного использования. Не распространяйте ноты, "
    "защищённые авторским правом, без разрешения правообладателя. "
    "Упрощение — это помощь, а не замена преподавателю."
)


def build_report(
    info: ScoreInfo,
    log: ChangeLog,
    validation: ValidationReport,
    level: str | None = None,
) -> str:
    config = get_level(level or log.level)
    lines = ["ОТЧЁТ ОБ УПРОЩЕНИИ", "=" * 40, ""]
    lines.append(f"Уровень: {config.label} ({config.key})")
    lines.append(f"Тональность: {info.key}")
    lines.append(f"Размер: {info.time_signature or 'не указан'}")
    lines.append(f"Темп: {info.tempo_bpm or 'не указан'}")
    lines.append("")
    lines.append("Партии (до упрощения):")
    for part in info.parts:
        lines.append(f"  - {part.name}: нот {part.note_count}, диапазон {part.lowest}–{part.highest}")
    lines.append("")
    lines.append(f"Сделано изменений: {log.total}")
    lines.append(f"  упрощений аккордов: {log.count('chord_reduction')}")
    lines.append(f"  переносов в диапазон: {log.count('fit_to_range')}")
    lines.append("")
    lines.append("Подробности:")
    if log.entries:
        lines.extend(f"  {entry}" for entry in log.entries)
    else:
        lines.append("  (изменений нет)")
    lines.append("")
    lines.append("Результат проверки: " + ("OK" if validation.ok else "ЕСТЬ ОШИБКИ"))
    for error in validation.errors:
        lines.append(f"  ОШИБКА: {error}")
    if validation.warnings:
        lines.append("Места, требующие внимания человека:")
        lines.extend(f"  ! {warning}" for warning in validation.warnings)
    lines.append("")
    lines.append(COPYRIGHT_NOTICE)
    return "\n".join(lines)
