"""Reference profile building and management.

Runs the analysis pipeline on all MIDI files in a reference corpus category
and computes per-metric distributions (mean, std, min, max).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .loader import list_reference_midis
from .muspy_metrics import compute_muspy_metrics
from .scorer import MetricStats, ReferenceProfile, flatten_metrics
from .symbolic import full_symbolic_analysis


def build_profile(
    references_dir: Path | str,
    category: str,
) -> ReferenceProfile:
    """Build a reference profile by analyzing all MIDI files in a category.

    Runs symbolic + MusPy analysis on each reference MIDI, then computes
    per-metric distributions across the corpus.

    Args:
        references_dir: Root references/ directory
        category: Category name (e.g., "ambient", "jazz-calm")

    Returns:
        ReferenceProfile with per-metric stats
    """
    midi_paths = list_reference_midis(references_dir, category)
    if not midi_paths:
        return ReferenceProfile(category=category)

    # Collect metrics from all reference files
    all_metrics: dict[str, list[float]] = {}

    for midi_path in midi_paths:
        try:
            symbolic = full_symbolic_analysis(midi_path)
            muspy = compute_muspy_metrics(midi_path)
            flat = flatten_metrics(symbolic=symbolic, muspy=muspy)

            for k, v in flat.items():
                if v is not None:
                    all_metrics.setdefault(k, []).append(float(v))
        except Exception as e:
            print(f"Warning: failed to analyze {midi_path.name}: {e}")
            continue

    # Compute stats
    profile = ReferenceProfile(category=category)
    for metric_name, values in all_metrics.items():
        arr = np.array(values)
        profile.metrics[metric_name] = MetricStats(
            mean=round(float(arr.mean()), 6),
            std=round(float(arr.std()), 6),
            min=round(float(arr.min()), 6),
            max=round(float(arr.max()), 6),
            count=len(values),
        )

    return profile


def build_profile_from_midis(
    midi_paths: list[Path],
    category: str,
) -> ReferenceProfile:
    """Build a reference profile from an explicit list of MIDI files.

    Useful for building profiles from generated harmonium output
    (self-referencing) or custom file lists.
    """
    all_metrics: dict[str, list[float]] = {}

    for midi_path in midi_paths:
        try:
            symbolic = full_symbolic_analysis(midi_path)
            muspy = compute_muspy_metrics(midi_path)
            flat = flatten_metrics(symbolic=symbolic, muspy=muspy)

            for k, v in flat.items():
                if v is not None:
                    all_metrics.setdefault(k, []).append(float(v))
        except Exception as e:
            print(f"Warning: failed to analyze {midi_path.name}: {e}")
            continue

    profile = ReferenceProfile(category=category)
    for metric_name, values in all_metrics.items():
        arr = np.array(values)
        profile.metrics[metric_name] = MetricStats(
            mean=round(float(arr.mean()), 6),
            std=round(float(arr.std()), 6),
            min=round(float(arr.min()), 6),
            max=round(float(arr.max()), 6),
            count=len(values),
        )

    return profile


def save_profile(profile: ReferenceProfile, path: Path | str) -> None:
    """Save a reference profile to a JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(profile.to_dict(), f, indent=2)


def load_profile(path: Path | str) -> ReferenceProfile:
    """Load a reference profile from a JSON file."""
    with Path(path).open() as f:
        data = json.load(f)
    return ReferenceProfile.from_dict(data)
