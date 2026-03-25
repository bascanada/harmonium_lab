"""MusPy-based music quality metrics.

Computes standard generation evaluation metrics using the MusPy library.
These metrics are fast and work directly on MIDI files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import muspy


def load_music(midi_path: Path | str) -> muspy.Music:
    """Load a MIDI file as a MusPy Music object."""
    return muspy.read_midi(str(midi_path))


def compute_muspy_metrics(midi_path: Path | str) -> dict[str, Any]:
    """Compute all MusPy metrics for a MIDI file.

    Args:
        midi_path: Path to .mid file

    Returns:
        dict with all MusPy metric values
    """
    music = load_music(midi_path)
    return compute_metrics_from_music(music)


def compute_metrics_from_music(music: muspy.Music) -> dict[str, Any]:
    """Compute all MusPy metrics from a loaded Music object.

    Returns:
        dict with:
          - pitch_class_entropy: float (0 = one pitch, ~3.58 = uniform 12 classes)
          - scale_consistency: float (0-1, fraction of notes in detected scale)
          - pitch_range: int (semitones between lowest and highest note)
          - n_pitch_classes_used: int (unique pitch classes, 1-12)
          - groove_consistency: float (0-1, rhythmic regularity)
          - empty_beat_rate: float (0-1, fraction of beats with no notes)
          - empty_measure_rate: float (0-1, fraction of empty measures)
          - polyphony: float (average simultaneous notes)
          - polyphony_rate: float (0-1, fraction of time with >1 note)
          - pitch_in_scale_rate: float (0-1, same as scale_consistency)
          - n_pitches_used: int (unique MIDI pitches)
          - drum_in_pattern_rate: float (0-1, drum pattern regularity)
          - drum_pattern_consistency: float (0-1)
    """
    metrics: dict[str, Any] = {}

    # Pitch metrics
    try:
        metrics["pitch_class_entropy"] = round(muspy.pitch_class_entropy(music), 4)
    except Exception:
        metrics["pitch_class_entropy"] = None

    try:
        metrics["scale_consistency"] = round(muspy.scale_consistency(music), 4)
    except Exception:
        metrics["scale_consistency"] = None

    try:
        metrics["pitch_range"] = muspy.pitch_range(music)
    except Exception:
        metrics["pitch_range"] = None

    try:
        metrics["n_pitch_classes_used"] = muspy.n_pitch_classes_used(music)
    except Exception:
        metrics["n_pitch_classes_used"] = None

    try:
        metrics["n_pitches_used"] = muspy.n_pitches_used(music)
    except Exception:
        metrics["n_pitches_used"] = None

    # Rhythm metrics
    try:
        metrics["groove_consistency"] = round(muspy.groove_consistency(music), 4)
    except Exception:
        metrics["groove_consistency"] = None

    try:
        metrics["empty_beat_rate"] = round(muspy.empty_beat_rate(music), 4)
    except Exception:
        metrics["empty_beat_rate"] = None

    try:
        metrics["empty_measure_rate"] = round(muspy.empty_measure_rate(music), 4)
    except Exception:
        metrics["empty_measure_rate"] = None

    # Polyphony metrics
    try:
        metrics["polyphony"] = round(muspy.polyphony(music), 4)
    except Exception:
        metrics["polyphony"] = None

    try:
        metrics["polyphony_rate"] = round(muspy.polyphony_rate(music), 4)
    except Exception:
        metrics["polyphony_rate"] = None

    # Drum metrics
    try:
        metrics["drum_in_pattern_rate"] = round(muspy.drum_in_pattern_rate(music), 4)
    except Exception:
        metrics["drum_in_pattern_rate"] = None

    try:
        metrics["drum_pattern_consistency"] = round(muspy.drum_pattern_consistency(music), 4)
    except Exception:
        metrics["drum_pattern_consistency"] = None

    return metrics
