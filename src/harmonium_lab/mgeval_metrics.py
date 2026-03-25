"""MGEval-style corpus comparison metrics.

Implements pitch class histogram overlap and note length distribution
comparison between generated and reference MIDI files.
Based on the MGEval framework (Dong et al., 2018).

Since mgeval is not available on PyPI, we implement the core metrics
directly using numpy and pretty_midi.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pretty_midi


# ---------------------------------------------------------------------------
# Histogram extraction
# ---------------------------------------------------------------------------


def pitch_class_histogram(midi_path: Path | str) -> np.ndarray:
    """Extract a 12-bin pitch class histogram from a MIDI file.

    Each bin counts the total duration (in seconds) of notes
    belonging to that pitch class (C=0, C#=1, ..., B=11).

    Returns:
        numpy array of shape (12,), normalized to sum to 1.
    """
    pm = pretty_midi.PrettyMIDI(str(midi_path))
    hist = np.zeros(12, dtype=np.float64)

    for instrument in pm.instruments:
        for note in instrument.notes:
            pc = note.pitch % 12
            duration = note.end - note.start
            hist[pc] += duration

    total = hist.sum()
    if total > 0:
        hist /= total
    return hist


def note_length_histogram(
    midi_path: Path | str,
    num_bins: int = 12,
    max_duration: float = 4.0,
) -> np.ndarray:
    """Extract a histogram of note durations from a MIDI file.

    Bins note durations from 0 to max_duration seconds into num_bins
    equally spaced bins. Notes longer than max_duration are placed
    in the last bin.

    Returns:
        numpy array of shape (num_bins,), normalized to sum to 1.
    """
    pm = pretty_midi.PrettyMIDI(str(midi_path))
    durations = []

    for instrument in pm.instruments:
        for note in instrument.notes:
            dur = note.end - note.start
            durations.append(min(dur, max_duration))

    if not durations:
        return np.zeros(num_bins, dtype=np.float64)

    hist, _ = np.histogram(
        durations,
        bins=num_bins,
        range=(0.0, max_duration),
    )
    hist = hist.astype(np.float64)
    total = hist.sum()
    if total > 0:
        hist /= total
    return hist


def onset_histogram(
    midi_path: Path | str,
    resolution: int = 16,
) -> np.ndarray:
    """Extract a histogram of note onset positions within a beat.

    Quantizes each note onset to the nearest 1/resolution of a beat
    and counts occurrences.

    Returns:
        numpy array of shape (resolution,), normalized to sum to 1.
    """
    pm = pretty_midi.PrettyMIDI(str(midi_path))
    hist = np.zeros(resolution, dtype=np.float64)

    beats = pm.get_beats()
    if len(beats) < 2:
        return hist

    for instrument in pm.instruments:
        for note in instrument.notes:
            onset = note.start
            # Find which beat interval this onset falls in
            beat_idx = np.searchsorted(beats, onset, side="right") - 1
            if beat_idx < 0 or beat_idx >= len(beats) - 1:
                continue
            beat_start = beats[beat_idx]
            beat_end = beats[beat_idx + 1]
            beat_duration = beat_end - beat_start
            if beat_duration <= 0:
                continue
            # Position within beat (0-1)
            position = (onset - beat_start) / beat_duration
            bin_idx = min(int(position * resolution), resolution - 1)
            hist[bin_idx] += 1

    total = hist.sum()
    if total > 0:
        hist /= total
    return hist


# ---------------------------------------------------------------------------
# Comparison metrics
# ---------------------------------------------------------------------------


def overlap_area(hist_a: np.ndarray, hist_b: np.ndarray) -> float:
    """Compute the overlap area between two normalized histograms.

    OA = sum(min(a_i, b_i)) for each bin i.
    Returns a value in [0, 1]: 1 = identical distributions, 0 = no overlap.
    """
    return float(np.minimum(hist_a, hist_b).sum())


def kl_divergence(hist_p: np.ndarray, hist_q: np.ndarray, epsilon: float = 1e-10) -> float:
    """Compute KL divergence D_KL(P || Q) between two distributions.

    Uses epsilon smoothing to avoid log(0).
    Returns a non-negative float (0 = identical, higher = more different).
    """
    p = hist_p + epsilon
    q = hist_q + epsilon
    # Re-normalize after smoothing
    p = p / p.sum()
    q = q / q.sum()
    return float(np.sum(p * np.log(p / q)))


# ---------------------------------------------------------------------------
# Corpus comparison
# ---------------------------------------------------------------------------


def compare_to_reference(
    generated_midi: Path | str,
    reference_midis: list[Path | str],
) -> dict[str, Any]:
    """Compare a generated MIDI file against a reference corpus.

    Computes pitch class histogram, note length histogram, and onset
    histogram for the generated file, then compares each against
    the average histogram of the reference corpus.

    Args:
        generated_midi: Path to generated .mid file
        reference_midis: List of paths to reference .mid files

    Returns:
        dict with per-metric overlap_area and kl_divergence values
    """
    if not reference_midis:
        return {
            "pitch_class": {"overlap_area": None, "kl_divergence": None},
            "note_length": {"overlap_area": None, "kl_divergence": None},
            "onset": {"overlap_area": None, "kl_divergence": None},
            "reference_count": 0,
        }

    # Generated histograms
    gen_pc = pitch_class_histogram(generated_midi)
    gen_nl = note_length_histogram(generated_midi)
    gen_onset = onset_histogram(generated_midi)

    # Reference corpus average histograms
    ref_pcs = []
    ref_nls = []
    ref_onsets = []
    for ref_path in reference_midis:
        try:
            ref_pcs.append(pitch_class_histogram(ref_path))
            ref_nls.append(note_length_histogram(ref_path))
            ref_onsets.append(onset_histogram(ref_path))
        except Exception:
            continue

    if not ref_pcs:
        return {
            "pitch_class": {"overlap_area": None, "kl_divergence": None},
            "note_length": {"overlap_area": None, "kl_divergence": None},
            "onset": {"overlap_area": None, "kl_divergence": None},
            "reference_count": 0,
        }

    avg_pc = np.mean(ref_pcs, axis=0)
    avg_nl = np.mean(ref_nls, axis=0)
    avg_onset = np.mean(ref_onsets, axis=0)

    return {
        "pitch_class": {
            "overlap_area": round(overlap_area(gen_pc, avg_pc), 4),
            "kl_divergence": round(kl_divergence(gen_pc, avg_pc), 4),
        },
        "note_length": {
            "overlap_area": round(overlap_area(gen_nl, avg_nl), 4),
            "kl_divergence": round(kl_divergence(gen_nl, avg_nl), 4),
        },
        "onset": {
            "overlap_area": round(overlap_area(gen_onset, avg_onset), 4),
            "kl_divergence": round(kl_divergence(gen_onset, avg_onset), 4),
        },
        "reference_count": len(ref_pcs),
    }
