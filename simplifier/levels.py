"""Уровни упрощения и их настройки."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LevelConfig:
    key: str
    label: str
    tagline: str
    description: str
    max_chord_notes: int
    remove_doublings: bool


LEVELS: dict[str, LevelConfig] = {
    "easy": LevelConfig(
        key="easy",
        label="Легко",
        tagline="Для самых первых шагов",
        description=(
            "Аккорды сводятся к трезвучиям, удвоения убираются, "
            "ноты переносятся в удобный диапазон. Самый чистый и простой вариант."
        ),
        max_chord_notes=3,
        remove_doublings=True,
    ),
    "medium": LevelConfig(
        key="medium",
        label="Средне",
        tagline="Баланс простоты и звучания",
        description=(
            "Убираются лишние надстройки и удвоения, но аккорд может сохранить "
            "четвёртый звук. Подходит, когда хочется играть ближе к оригиналу."
        ),
        max_chord_notes=4,
        remove_doublings=True,
    ),
    "medium_hard": LevelConfig(
        key="medium_hard",
        label="Средне-сложно",
        tagline="Ближе к оригиналу",
        description=(
            "Минимальные вмешательства: убираются только самые перегруженные аккорды, "
            "удвоения сохраняются, диапазон по-прежнему остаётся удобным."
        ),
        max_chord_notes=5,
        remove_doublings=False,
    ),
}

ALIASES = {
    "easy": "easy",
    "легко": "easy",
    "medium": "medium",
    "средне": "medium",
    "medium_hard": "medium_hard",
    "medium-hard": "medium_hard",
    "medium hard": "medium_hard",
    "средне-сложно": "medium_hard",
    "средне сложно": "medium_hard",
}

DEFAULT_LEVEL = "medium"


def get_level(value: str | None = None) -> LevelConfig:
    """Вернуть настройки уровня по ключу или человекочитаемому названию."""
    if value is None or str(value).strip() == "":
        return LEVELS[DEFAULT_LEVEL]
    key = str(value).strip().lower()
    key = ALIASES.get(key, key)
    if key not in LEVELS:
        raise ValueError(
            f"Неизвестный уровень: {value}. Доступны: easy, medium, medium_hard."
        )
    return LEVELS[key]


def levels_payload() -> list[dict]:
    """Список уровней для API и интерфейса."""
    return [
        {
            "key": level.key,
            "label": level.label,
            "tagline": level.tagline,
            "description": level.description,
        }
        for level in LEVELS.values()
    ]
