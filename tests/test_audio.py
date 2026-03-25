"""Tests for Phase 3: audio analysis module."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from harmonium_lab.audio import (
    _check_fluidsynth,
    analyze_dissonance,
    analyze_dynamics,
    analyze_rhythm,
    analyze_spectral,
    analyze_tonal,
    full_audio_analysis,
)

# Sample rate for all tests
SR = 22050


# ---------------------------------------------------------------------------
# Synthetic audio fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sine_440() -> np.ndarray:
    """Pure 440 Hz sine wave, 2 seconds."""
    t = np.linspace(0, 2.0, 2 * SR, endpoint=False)
    return (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


@pytest.fixture
def chord_c_major() -> np.ndarray:
    """C major chord (C4 + E4 + G4), 3 seconds."""
    t = np.linspace(0, 3.0, 3 * SR, endpoint=False)
    c4 = np.sin(2 * np.pi * 261.63 * t)
    e4 = np.sin(2 * np.pi * 329.63 * t)
    g4 = np.sin(2 * np.pi * 392.00 * t)
    return (0.3 * (c4 + e4 + g4)).astype(np.float32)


@pytest.fixture
def noise() -> np.ndarray:
    """White noise, 2 seconds."""
    rng = np.random.default_rng(42)
    return (0.3 * rng.standard_normal(2 * SR)).astype(np.float32)


@pytest.fixture
def rhythmic_clicks() -> np.ndarray:
    """Rhythmic clicks at 120 BPM, 4 seconds."""
    y = np.zeros(4 * SR, dtype=np.float32)
    # 120 BPM = 2 beats/sec = click every 0.5s
    for beat in range(8):
        idx = int(beat * 0.5 * SR)
        # Short click
        click_len = min(int(0.01 * SR), len(y) - idx)
        y[idx : idx + click_len] = 0.8
    return y


# ---------------------------------------------------------------------------
# Spectral analysis tests
# ---------------------------------------------------------------------------


class TestSpectralAnalysis:
    def test_sine_wave(self, sine_440: np.ndarray) -> None:
        result = analyze_spectral(sine_440, SR)

        assert "spectral_centroid_mean" in result
        assert "spectral_bandwidth_mean" in result
        assert "spectral_flatness_mean" in result
        assert "spectral_rolloff_mean" in result

        # Pure sine → low flatness (tonal)
        assert result["spectral_flatness_mean"] < 0.1

    def test_noise_high_flatness(self, noise: np.ndarray) -> None:
        result = analyze_spectral(noise, SR)
        # Noise → high flatness
        assert result["spectral_flatness_mean"] > 0.1


# ---------------------------------------------------------------------------
# Tonal analysis tests
# ---------------------------------------------------------------------------


class TestTonalAnalysis:
    def test_sine_440_detects_a(self, sine_440: np.ndarray) -> None:
        result = analyze_tonal(sine_440, SR)

        assert "estimated_key" in result
        assert "key_strength" in result
        assert "tonal_power_ratio" in result
        # 440 Hz = A4
        assert result["estimated_key"] == "A"
        assert result["key_strength"] > 1.0  # dominant pitch class

    def test_c_major_chord(self, chord_c_major: np.ndarray) -> None:
        result = analyze_tonal(chord_c_major, SR)
        # Should detect C or a related pitch class
        assert result["estimated_key"] in ("C", "E", "G")
        assert result["tonal_power_ratio"] > 0.3


# ---------------------------------------------------------------------------
# Rhythm analysis tests
# ---------------------------------------------------------------------------


class TestRhythmAnalysis:
    def test_rhythmic_clicks(self, rhythmic_clicks: np.ndarray) -> None:
        result = analyze_rhythm(rhythmic_clicks, SR)

        assert "detected_tempo" in result
        assert "beat_count" in result
        assert "onset_rate" in result
        assert "tempo_stability" in result
        assert "duration" in result

        assert result["duration"] > 3.0
        assert result["onset_rate"] > 0

    def test_sine_has_low_onset_rate(self, sine_440: np.ndarray) -> None:
        result = analyze_rhythm(sine_440, SR)
        # Continuous tone → few onsets
        assert result["onset_rate"] < 5.0


# ---------------------------------------------------------------------------
# Dynamics analysis tests
# ---------------------------------------------------------------------------


class TestDynamicsAnalysis:
    def test_sine_dynamics(self, sine_440: np.ndarray) -> None:
        result = analyze_dynamics(sine_440, SR)

        assert "rms_mean" in result
        assert "rms_std" in result
        assert "dynamic_range_db" in result
        assert result["rms_mean"] > 0

    def test_noise_broader_dynamics(self, noise: np.ndarray) -> None:
        result = analyze_dynamics(noise, SR)
        assert result["rms_std"] > 0


# ---------------------------------------------------------------------------
# Dissonance analysis tests
# ---------------------------------------------------------------------------


class TestDissonanceAnalysis:
    def test_sine_harmonic(self, sine_440: np.ndarray) -> None:
        result = analyze_dissonance(sine_440, SR)

        assert "harmonic_ratio" in result
        assert "percussive_ratio" in result
        assert "dissonance_proxy" in result
        # Pure tone → mostly harmonic
        assert result["harmonic_ratio"] > 0.5

    def test_noise_dissonant(self, noise: np.ndarray) -> None:
        result = analyze_dissonance(noise, SR)
        # Noise → higher dissonance proxy
        assert result["dissonance_proxy"] > 0.01


# ---------------------------------------------------------------------------
# Full audio analysis
# ---------------------------------------------------------------------------


class TestFullAudioAnalysis:
    def test_full_analysis_structure(self, chord_c_major: np.ndarray) -> None:
        result = full_audio_analysis(chord_c_major, SR)

        assert "spectral" in result
        assert "rhythm" in result
        assert "tonal" in result
        assert "dynamics" in result
        assert "dissonance" in result

    def test_all_sections_populated(self, chord_c_major: np.ndarray) -> None:
        result = full_audio_analysis(chord_c_major, SR)
        for section_name, section in result.items():
            assert isinstance(section, dict), f"{section_name} should be a dict"
            assert len(section) > 0, f"{section_name} should not be empty"


# ---------------------------------------------------------------------------
# MIDI rendering (requires FluidSynth system library)
# ---------------------------------------------------------------------------


class TestMidiRendering:
    @pytest.fixture(autouse=True)
    def _require_fluidsynth(self) -> None:
        if not _check_fluidsynth():
            pytest.skip(
                "FluidSynth not installed "
                "(install with: sudo dnf install fluidsynth fluid-soundfont-gm)"
            )

    def test_render_and_analyze(self, generated_music_dir: Path) -> None:
        from harmonium_lab.audio import analyze_midi_file

        midi = generated_music_dir / "lab_calm_ambient.mid"
        if not midi.exists():
            pytest.skip("Lab MIDI not found")

        result = analyze_midi_file(midi)
        assert "spectral" in result
        assert "tonal" in result
        assert result["rhythm"]["duration"] > 10.0  # 32 bars should be > 10s


# ---------------------------------------------------------------------------
# Scorer integration (audio metrics in flatten_metrics)
# ---------------------------------------------------------------------------


class TestAudioScorerIntegration:
    def test_flatten_with_audio(self) -> None:
        from harmonium_lab.scorer import flatten_metrics

        audio = {
            "tonal": {"key_strength": 1.5},
            "dissonance": {"harmonic_ratio": 0.85, "dissonance_proxy": 0.02},
            "rhythm": {"tempo_stability": 0.92},
            "dynamics": {"dynamic_range_db": 18.5, "rms_std": 0.003},
        }
        flat = flatten_metrics(audio=audio)

        assert flat["audio_key_strength"] == 1.5
        assert flat["audio_harmonic_ratio"] == 0.85
        assert flat["audio_dissonance_proxy"] == 0.02
        assert flat["audio_tempo_stability"] == 0.92
        assert flat["audio_dynamic_range_db"] == 18.5
        assert flat["audio_rms_std"] == 0.003

    def test_flatten_without_audio_still_works(self) -> None:
        from harmonium_lab.scorer import flatten_metrics

        flat = flatten_metrics(
            symbolic={"key_stability": {"avg_correlation": 0.8},
                      "consonance": {}, "contour": {}, "voice_leading": {}},
        )
        assert "music21_key_correlation" in flat
        assert "audio_key_strength" not in flat
