"""Load harmonium output (MIDI, JSON) and reference corpus files."""

from __future__ import annotations

import json
from pathlib import Path

from .types import MeasureData, NoteData, Scenario, StateParams

# ---------------------------------------------------------------------------
# JSON loaders (MeasureSnapshot format from harmonium_core)
# ---------------------------------------------------------------------------


def load_measures_json(path: Path | str) -> list[MeasureData]:
    """Load a MeasureSnapshot JSON array (golden test format).

    Args:
        path: Path to JSON file containing an array of MeasureSnapshot objects.

    Returns:
        List of MeasureData objects.
    """
    path = Path(path)
    with path.open() as f:
        raw = json.load(f)

    measures: list[MeasureData] = []
    for m in raw:
        notes = tuple(
            NoteData(
                track=n["track"],
                pitch=n["pitch"],
                start_step=n["start_step"],
                duration_steps=n["duration_steps"],
                velocity=n["velocity"],
            )
            for n in m.get("notes", [])
        )
        measures.append(
            MeasureData(
                index=m["index"],
                tempo=m["tempo"],
                time_sig_numerator=m["time_sig_numerator"],
                time_sig_denominator=m["time_sig_denominator"],
                steps=m["steps"],
                chord_name=m["chord_name"],
                chord_root_offset=m["chord_root_offset"],
                chord_is_minor=m["chord_is_minor"],
                notes=notes,
                composition_bpm=m.get("composition_bpm", m["tempo"]),
            )
        )
    return measures


def load_scenario_json(
    measures_path: Path | str,
    metadata_path: Path | str | None = None,
) -> Scenario:
    """Load a complete scenario from JSON files.

    Args:
        measures_path: Path to MeasureSnapshot JSON array.
        metadata_path: Optional path to scenario metadata JSON.
            If None, infers name from filename and uses defaults.

    Returns:
        Scenario with measures and metadata.
    """
    measures_path = Path(measures_path)
    measures = load_measures_json(measures_path)

    if metadata_path is not None:
        metadata_path = Path(metadata_path)
        with metadata_path.open() as f:
            meta = json.load(f)
        params = StateParams(**meta.get("params", {}))
        return Scenario(
            name=meta.get("scenario", measures_path.stem),
            params=params,
            bars=meta.get("bars", len(measures)),
            seed=meta.get("seed", 0),
            measures=measures,
        )

    return Scenario(
        name=measures_path.stem,
        params=StateParams(),
        bars=len(measures),
        seed=0,
        measures=measures,
    )


# ---------------------------------------------------------------------------
# MIDI loaders
# ---------------------------------------------------------------------------


def load_midi_music21(path: Path | str):
    """Load a MIDI file as a music21 Score.

    Args:
        path: Path to .mid file.

    Returns:
        music21.stream.Score
    """
    import music21

    return music21.converter.parse(str(path))


def load_midi_muspy(path: Path | str):
    """Load a MIDI file as a MusPy Music object.

    Args:
        path: Path to .mid file.

    Returns:
        muspy.Music
    """
    import muspy

    return muspy.read_midi(str(path))


def load_midi_pretty(path: Path | str):
    """Load a MIDI file as a PrettyMIDI object.

    Args:
        path: Path to .mid file.

    Returns:
        pretty_midi.PrettyMIDI
    """
    import pretty_midi

    return pretty_midi.PrettyMIDI(str(path))


# ---------------------------------------------------------------------------
# Reference corpus
# ---------------------------------------------------------------------------


def load_corpus_meta(references_dir: Path | str, category: str) -> dict:
    """Load meta.json for a reference corpus category.

    Args:
        references_dir: Root references/ directory.
        category: Category name (e.g., "ambient", "jazz-calm").

    Returns:
        Parsed meta.json dict.
    """
    meta_path = Path(references_dir) / category / "meta.json"
    with meta_path.open() as f:
        return json.load(f)


def list_reference_midis(references_dir: Path | str, category: str) -> list[Path]:
    """List all MIDI files for a reference corpus category.

    Args:
        references_dir: Root references/ directory.
        category: Category name.

    Returns:
        List of Path objects to .mid files.
    """
    cat_dir = Path(references_dir) / category
    return sorted(cat_dir.glob("*.mid")) + sorted(cat_dir.glob("*.midi"))
