"""Создаёт короткие тестовые MusicXML-файлы в папке samples/.

Запуск:  python tests/make_samples.py
"""

from pathlib import Path

from music21 import chord, clef, key, meter, note, stream

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


def _new_part(part_id: str, bass: bool) -> stream.Part:
    part = stream.Part(id=part_id)
    part.partName = part_id
    part.append(clef.BassClef() if bass else clef.TrebleClef())
    part.append(key.Key("C"))
    part.append(meter.TimeSignature("4/4"))
    return part


def build_scale() -> stream.Score:
    """Гамма до мажор, одна партия, одна октава выше нужного диапазона."""
    score = stream.Score()
    part = _new_part("Melody", bass=False)
    for name in ["C6", "D6", "E6", "F6", "G6", "A6", "B6", "C7"]:
        part.append(note.Note(name, quarterLength=1))
    score.insert(0, part)
    return score


def build_piano_sample() -> stream.Score:
    """Мелодия (правая рука) + сложные аккорды (левая рука), 2 такта."""
    score = stream.Score()
    rh = _new_part("Right hand", bass=False)
    lh = _new_part("Left hand", bass=True)

    # Такт 1–2: мелодия слишком высоко
    for name in ["C6", "E6", "G6", "E6", "D6", "F6", "A6", "F6"]:
        rh.append(note.Note(name, quarterLength=1))

    # Такт 1: C9 (5 звуков), такт 2: G7 (4 звука), слишком низко
    lh.append(chord.Chord(["C2", "E2", "G2", "B-2", "D3"], quarterLength=4))
    lh.append(chord.Chord(["G1", "B1", "D2", "F2"], quarterLength=4))

    score.insert(0, rh)
    score.insert(0, lh)
    return score


def main() -> None:
    SAMPLES_DIR.mkdir(exist_ok=True)
    build_scale().write("musicxml", fp=str(SAMPLES_DIR / "scale.musicxml"))
    build_piano_sample().write("musicxml", fp=str(SAMPLES_DIR / "piano_sample.musicxml"))
    print(f"Тестовые файлы созданы в {SAMPLES_DIR}")


if __name__ == "__main__":
    main()
