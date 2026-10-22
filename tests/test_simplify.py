import copy
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from music21 import chord, note, stream

from simplifier.analysis import analyze
from simplifier.parser import load_score
from simplifier.simplify import (
    ChangeLog,
    LEFT_HAND_RANGE,
    RIGHT_HAND_RANGE,
    chords_to_triads,
    fit_to_range,
    simplify_score,
)
from simplifier.validate import validate

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_samples  # noqa: E402


def _part_with(*elements) -> stream.Part:
    part = stream.Part()
    for el in elements:
        part.append(el)
    return part


def _score_with(part: stream.Part) -> stream.Score:
    score = stream.Score()
    score.insert(0, part)
    return score


# ---- правило 1: аккорды -> трезвучия ---------------------------------------

def test_c9_becomes_c_major_triad():
    ch = chord.Chord(["C3", "E3", "G3", "B-3", "D4"], quarterLength=4)
    part = _part_with(ch)
    log = ChangeLog()
    assert chords_to_triads(part, log) == 1
    names = sorted(p.name for p in ch.pitches)
    assert names == ["C", "E", "G"]


def test_triad_is_left_untouched():
    ch = chord.Chord(["C3", "E3", "G3"], quarterLength=4)
    part = _part_with(ch)
    assert chords_to_triads(part, ChangeLog()) == 0


def test_octave_doublings_removed():
    ch = chord.Chord(["C2", "G2", "C3", "E3"], quarterLength=4)
    part = _part_with(ch)
    chords_to_triads(part, ChangeLog())
    assert len(ch.pitches) == 3


# ---- правило 2: диапазон ----------------------------------------------------

def test_high_note_moves_down_into_range():
    n = note.Note("C7", quarterLength=1)
    part = _part_with(n)
    low, high = RIGHT_HAND_RANGE
    assert fit_to_range(part, low, high, ChangeLog()) == 1
    assert low <= n.pitch.ps <= high
    assert n.pitch.name == "C"  # название ноты сохранилось, поменялась только октава


def test_low_note_moves_up_into_range():
    n = note.Note("C1", quarterLength=1)
    part = _part_with(n)
    low, high = LEFT_HAND_RANGE
    fit_to_range(part, low, high, ChangeLog())
    assert low <= n.pitch.ps <= high


def test_note_in_range_not_changed():
    n = note.Note("E4", quarterLength=1)
    part = _part_with(n)
    low, high = RIGHT_HAND_RANGE
    assert fit_to_range(part, low, high, ChangeLog()) == 0


# ---- весь конвейер на тестовых файлах --------------------------------------

def test_pipeline_on_piano_sample(tmp_path):
    path = tmp_path / "piano.musicxml"
    make_samples.build_piano_sample().write("musicxml", fp=str(path))

    score = load_score(str(path))
    info = analyze(score)
    assert info.time_signature == "4/4"
    assert len(info.parts) == 2

    simplified = copy.deepcopy(score)
    log = simplify_score(simplified, "easy")
    report = validate(score, simplified, log)

    assert report.ok, report.errors
    assert log.count("chord_reduction") == 2
    assert log.count("fit_to_range") > 0
    assert log.level == "easy"

    for i, part in enumerate(simplified.parts):
        low, high = log.ranges[i]
        for el in part.recurse().notes:
            assert all(low <= p.ps <= high for p in el.pitches)


# ---- уровни сложности -------------------------------------------------------

def test_easy_reduces_to_triad():
    ch = chord.Chord(["C3", "E3", "G3", "B-3", "D4"], quarterLength=4)
    part = _part_with(ch)
    simplify_score(_score_with(part), "easy")
    assert sorted(p.name for p in ch.pitches) == ["C", "E", "G"]


def test_medium_keeps_fourth_sound():
    ch = chord.Chord(["C3", "E3", "G3", "B-3", "D4"], quarterLength=4)
    part = _part_with(ch)
    simplify_score(_score_with(part), "medium")
    assert sorted(p.name for p in ch.pitches) == ["B-", "C", "E", "G"]


def test_medium_hard_keeps_five_sounds():
    ch = chord.Chord(["C3", "E3", "G3", "B-3", "D4"], quarterLength=4)
    part = _part_with(ch)
    simplify_score(_score_with(part), "medium_hard")
    assert len(ch.pitches) == 5


def test_unknown_level_raises():
    with pytest.raises(ValueError):
        simplify_score(_score_with(stream.Part()), "unknown")
