"""Symbolic music analysis using music21.

Analyzes harmonium's MIDI output at the note/interval/chord level
without requiring audio rendering.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import music21
from music21 import (
    analysis,
    converter,
    interval,
    key,
    roman,
    stream,
)


def load_score(midi_path: Path | str) -> music21.stream.Score:
    """Load a MIDI file as a music21 Score."""
    return converter.parse(str(midi_path))


# ---------------------------------------------------------------------------
# A. Consonance Analysis
# ---------------------------------------------------------------------------


def analyze_consonance(score: music21.stream.Score) -> dict[str, Any]:
    """Analyze consonance ratio across all simultaneous note pairs.

    Returns:
        dict with:
          - consonance_ratio: float (0-1), fraction of consonant intervals
          - total_intervals: int
          - dissonant_count: int
    """
    consonant = 0
    dissonant = 0

    for chord_obj in score.recurse().getElementsByClass("Chord"):
        pitches = chord_obj.pitches
        for i in range(len(pitches)):
            for j in range(i + 1, len(pitches)):
                itv = interval.Interval(pitches[i], pitches[j])
                if itv.isConsonant():
                    consonant += 1
                else:
                    dissonant += 1

    # Also check simultaneous notes across parts
    chordified = score.chordify()
    for chord_obj in chordified.recurse().getElementsByClass("Chord"):
        pitches = chord_obj.pitches
        for i in range(len(pitches)):
            for j in range(i + 1, len(pitches)):
                itv = interval.Interval(pitches[i], pitches[j])
                if itv.isConsonant():
                    consonant += 1
                else:
                    dissonant += 1

    total = consonant + dissonant
    ratio = consonant / total if total > 0 else 1.0

    return {
        "consonance_ratio": round(ratio, 4),
        "total_intervals": total,
        "dissonant_count": dissonant,
    }


# ---------------------------------------------------------------------------
# B. Voice Leading Quality
# ---------------------------------------------------------------------------


def analyze_voice_leading(score: music21.stream.Score) -> dict[str, Any]:
    """Analyze voice leading quality between lead and bass parts.

    Detects parallel fifths, parallel octaves, and voice crossings
    by examining consecutive vertical sonorities.

    Returns:
        dict with parallel_fifths, parallel_octaves, voice_crossings counts
    """
    parallel_fifths = 0
    parallel_octaves = 0
    voice_crossings = 0

    chordified = score.chordify()
    chords = list(chordified.recurse().getElementsByClass("Chord"))

    for i in range(1, len(chords)):
        prev_pitches = sorted(chords[i - 1].pitches)
        curr_pitches = sorted(chords[i].pitches)

        if len(prev_pitches) < 2 or len(curr_pitches) < 2:
            continue

        # Check outer voices (lowest and highest)
        prev_bass, prev_top = prev_pitches[0], prev_pitches[-1]
        curr_bass, curr_top = curr_pitches[0], curr_pitches[-1]

        # Voice crossing: bass goes above top or top goes below bass
        if curr_bass.midi > curr_top.midi:
            voice_crossings += 1

        # Parallel motion detection
        try:
            prev_interval = interval.Interval(prev_bass, prev_top)
            curr_interval = interval.Interval(curr_bass, curr_top)

            # Both moving in same direction?
            bass_motion = curr_bass.midi - prev_bass.midi
            top_motion = curr_top.midi - prev_top.midi

            if bass_motion != 0 and top_motion != 0:
                same_direction = (bass_motion > 0) == (top_motion > 0)
                if same_direction:
                    semis = curr_interval.semitones % 12
                    if semis == 7:  # Perfect fifth
                        prev_semis = prev_interval.semitones % 12
                        if prev_semis == 7:
                            parallel_fifths += 1
                    elif semis == 0:  # Octave/unison
                        prev_semis = prev_interval.semitones % 12
                        if prev_semis == 0:
                            parallel_octaves += 1
        except Exception:
            continue

    return {
        "parallel_fifths": parallel_fifths,
        "parallel_octaves": parallel_octaves,
        "voice_crossings": voice_crossings,
    }


# ---------------------------------------------------------------------------
# C. Key Stability (Windowed)
# ---------------------------------------------------------------------------


def analyze_key_stability(
    score: music21.stream.Score,
    window_measures: int = 4,
) -> dict[str, Any]:
    """Analyze key stability using windowed Krumhansl-Schmuckler analysis.

    Args:
        score: music21 Score
        window_measures: number of measures per analysis window

    Returns:
        dict with:
          - detected_key: str (e.g., "C major")
          - avg_correlation: float (0-1)
          - window_results: list of per-window (key, correlation)
          - key_change_count: int
    """
    # Global key detection
    detected = score.analyze("key")
    global_key = str(detected)
    global_correlation = detected.correlationCoefficient

    # Windowed analysis
    measures = list(score.recurse().getElementsByClass("Measure"))
    if not measures:
        # Try parts
        all_measures = []
        for part in score.parts:
            all_measures.extend(part.getElementsByClass("Measure"))
        measures = all_measures

    window_results = []
    correlations = []
    prev_key = None
    key_changes = 0

    # Group measures into windows
    for start in range(0, len(measures), window_measures):
        window = stream.Stream()
        for m in measures[start : start + window_measures]:
            for el in m.recurse().notesAndRests:
                window.append(el)

        if len(list(window.recurse().getElementsByClass("Note"))) == 0:
            continue

        try:
            window_key = window.analyze("key")
            window_results.append({
                "key": str(window_key),
                "correlation": round(window_key.correlationCoefficient, 4),
            })
            correlations.append(window_key.correlationCoefficient)

            if prev_key is not None and str(window_key) != prev_key:
                key_changes += 1
            prev_key = str(window_key)
        except Exception:
            continue

    avg_corr = sum(correlations) / len(correlations) if correlations else global_correlation

    return {
        "detected_key": global_key,
        "global_correlation": round(global_correlation, 4),
        "avg_correlation": round(avg_corr, 4),
        "key_change_count": key_changes,
        "window_count": len(window_results),
        "window_results": window_results,
    }


# ---------------------------------------------------------------------------
# D. Melodic Contour
# ---------------------------------------------------------------------------


def analyze_contour(score: music21.stream.Score, part_index: int = 0) -> dict[str, Any]:
    """Analyze melodic contour of a specific part.

    Args:
        score: music21 Score
        part_index: which part to analyze (0=first, typically lead)

    Returns:
        dict with step_ratio, leap_ratio, direction_changes, pitch_range, avg_interval
    """
    parts = list(score.parts)
    if not parts:
        return _empty_contour()

    # Use the specified part, or first available
    idx = min(part_index, len(parts) - 1)
    part = parts[idx]
    notes = list(part.recurse().getElementsByClass("Note"))

    if len(notes) < 2:
        return _empty_contour()

    steps = 0  # semitone distance <= 2
    leaps = 0  # semitone distance > 2
    direction_changes = 0
    intervals_abs = []
    prev_direction = None

    for i in range(1, len(notes)):
        itv = interval.Interval(notes[i - 1], notes[i])
        semitones = abs(itv.semitones)
        intervals_abs.append(semitones)

        if semitones <= 2:
            steps += 1
        else:
            leaps += 1

        # Track direction changes
        if itv.semitones > 0:
            direction = 1
        elif itv.semitones < 0:
            direction = -1
        else:
            direction = 0

        if prev_direction is not None and direction != 0 and prev_direction != 0:
            if direction != prev_direction:
                direction_changes += 1

        if direction != 0:
            prev_direction = direction

    total_intervals = steps + leaps
    pitches = [n.pitch.midi for n in notes]

    return {
        "step_ratio": round(steps / total_intervals, 4) if total_intervals > 0 else 0.0,
        "leap_ratio": round(leaps / total_intervals, 4) if total_intervals > 0 else 0.0,
        "direction_changes": direction_changes,
        "pitch_range": max(pitches) - min(pitches) if pitches else 0,
        "avg_interval": round(sum(intervals_abs) / len(intervals_abs), 2) if intervals_abs else 0.0,
        "note_count": len(notes),
    }


def _empty_contour() -> dict[str, Any]:
    return {
        "step_ratio": 0.0,
        "leap_ratio": 0.0,
        "direction_changes": 0,
        "pitch_range": 0,
        "avg_interval": 0.0,
        "note_count": 0,
    }


# ---------------------------------------------------------------------------
# Full symbolic analysis
# ---------------------------------------------------------------------------


def full_symbolic_analysis(
    midi_path: Path | str,
    window_measures: int = 4,
) -> dict[str, Any]:
    """Run all music21 symbolic analyses on a MIDI file.

    Args:
        midi_path: Path to .mid file
        window_measures: measures per window for key stability analysis

    Returns:
        dict with consonance, voice_leading, key_stability, contour sections
    """
    score = load_score(midi_path)

    return {
        "consonance": analyze_consonance(score),
        "voice_leading": analyze_voice_leading(score),
        "key_stability": analyze_key_stability(score, window_measures),
        "contour": analyze_contour(score, part_index=1),  # Part 1 = Lead (Part 0 = Bass)
    }
