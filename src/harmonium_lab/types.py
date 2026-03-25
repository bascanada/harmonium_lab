"""Data types mirroring harmonium_core Rust structs.

These dataclasses match the JSON serialization of MeasureSnapshot/NoteSnapshot
from harmonium_core/src/report.rs and StateSnapshot from timeline/mod.rs.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class NoteData:
    """A single note event within a measure.

    Mirrors harmonium_core::report::NoteSnapshot.
    """

    track: int  # 0=Bass, 1=Lead, 2=Snare, 3=Hat
    pitch: int  # MIDI note 0-127
    start_step: int  # Position within measure (0-based)
    duration_steps: int  # 0 = trigger-only (percussion)
    velocity: int  # 0-127


@dataclass(frozen=True, slots=True)
class MeasureData:
    """A complete measure of generated music.

    Mirrors harmonium_core::report::MeasureSnapshot.
    """

    index: int  # 1-based measure number
    tempo: float
    time_sig_numerator: int
    time_sig_denominator: int
    steps: int  # Steps per measure (e.g., 16 for 4/4)
    chord_name: str  # Display name (e.g., "Imaj7", "iv")
    chord_root_offset: int  # Semitones from key root
    chord_is_minor: bool
    notes: tuple[NoteData, ...] = field(default_factory=tuple)
    composition_bpm: float = 120.0


@dataclass(frozen=True, slots=True)
class StateParams:
    """Engine state at generation time.

    Mirrors harmonium_core::timeline::StateSnapshot.
    """

    bpm: float = 120.0
    density: float = 0.5
    tension: float = 0.3
    smoothness: float = 0.7
    valence: float = 0.2
    arousal: float = 0.5


@dataclass(slots=True)
class Scenario:
    """A complete generated scenario with metadata and measures."""

    name: str
    params: StateParams
    bars: int
    seed: int
    measures: list[MeasureData] = field(default_factory=list)
