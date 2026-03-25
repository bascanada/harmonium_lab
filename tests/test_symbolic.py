"""Tests for Phase 2: symbolic analysis modules."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

LAB_MIDI_SCENARIOS = [
    "lab_calm_ambient",
    "lab_jazz_ballad",
    "lab_jazz_medium",
    "lab_practice_easy",
    "lab_dramatic_high",
]


@pytest.fixture
def lab_midi_path(generated_music_dir: Path) -> Path:
    """Return path to a known lab MIDI file (calm ambient)."""
    path = generated_music_dir / "lab_calm_ambient.mid"
    if not path.exists():
        pytest.skip("Lab MIDI not found (run `make test/lab-export`)")
    return path


@pytest.fixture
def all_lab_midis(generated_music_dir: Path) -> list[Path]:
    """Return paths to all lab MIDI files."""
    paths = []
    for name in LAB_MIDI_SCENARIOS:
        p = generated_music_dir / f"{name}.mid"
        if not p.exists():
            pytest.skip("Lab MIDI files not found (run `make test/lab-export`)")
        paths.append(p)
    return paths


# ---------------------------------------------------------------------------
# music21 symbolic analysis tests
# ---------------------------------------------------------------------------


class TestSymbolicAnalysis:
    """Test harmonium_lab.symbolic module."""

    def test_consonance(self, lab_midi_path: Path) -> None:
        from harmonium_lab.symbolic import analyze_consonance, load_score

        score = load_score(lab_midi_path)
        result = analyze_consonance(score)

        assert "consonance_ratio" in result
        assert 0.0 <= result["consonance_ratio"] <= 1.0
        assert result["total_intervals"] > 0

    def test_voice_leading(self, lab_midi_path: Path) -> None:
        from harmonium_lab.symbolic import analyze_voice_leading, load_score

        score = load_score(lab_midi_path)
        result = analyze_voice_leading(score)

        assert "parallel_fifths" in result
        assert "parallel_octaves" in result
        assert "voice_crossings" in result
        assert result["parallel_fifths"] >= 0
        assert result["parallel_octaves"] >= 0

    def test_key_stability(self, lab_midi_path: Path) -> None:
        from harmonium_lab.symbolic import analyze_key_stability, load_score

        score = load_score(lab_midi_path)
        result = analyze_key_stability(score)

        assert "detected_key" in result
        assert "avg_correlation" in result
        assert result["avg_correlation"] > 0
        assert isinstance(result["detected_key"], str)
        assert result["key_change_count"] >= 0

    def test_contour(self, lab_midi_path: Path) -> None:
        from harmonium_lab.symbolic import analyze_contour, load_score

        score = load_score(lab_midi_path)
        result = analyze_contour(score)

        assert "step_ratio" in result
        assert "leap_ratio" in result
        assert "direction_changes" in result
        assert "pitch_range" in result
        assert result["note_count"] > 0
        # step_ratio + leap_ratio should approximately equal 1.0
        assert abs(result["step_ratio"] + result["leap_ratio"] - 1.0) < 0.01

    def test_full_symbolic_analysis(self, lab_midi_path: Path) -> None:
        from harmonium_lab.symbolic import full_symbolic_analysis

        result = full_symbolic_analysis(lab_midi_path)

        assert "consonance" in result
        assert "voice_leading" in result
        assert "key_stability" in result
        assert "contour" in result

    def test_all_scenarios(self, all_lab_midis: list[Path]) -> None:
        """Smoke test: run full analysis on every scenario."""
        from harmonium_lab.symbolic import full_symbolic_analysis

        for path in all_lab_midis:
            result = full_symbolic_analysis(path)
            assert result["consonance"]["total_intervals"] > 0, (
                f"{path.stem}: no intervals found"
            )
            assert result["key_stability"]["avg_correlation"] > 0, (
                f"{path.stem}: key correlation is 0"
            )


# ---------------------------------------------------------------------------
# MusPy metrics tests
# ---------------------------------------------------------------------------


class TestMuspyMetrics:
    """Test harmonium_lab.muspy_metrics module."""

    def test_compute_metrics(self, lab_midi_path: Path) -> None:
        from harmonium_lab.muspy_metrics import compute_muspy_metrics

        result = compute_muspy_metrics(lab_midi_path)

        assert "pitch_class_entropy" in result
        assert "scale_consistency" in result
        assert "pitch_range" in result
        assert "groove_consistency" in result
        assert "empty_beat_rate" in result

        # Sanity checks
        if result["pitch_class_entropy"] is not None:
            assert 0.0 <= result["pitch_class_entropy"] <= 4.0  # log2(12) ≈ 3.58
        if result["scale_consistency"] is not None:
            assert 0.0 <= result["scale_consistency"] <= 1.0
        if result["pitch_range"] is not None:
            assert result["pitch_range"] >= 0
        if result["groove_consistency"] is not None:
            assert 0.0 <= result["groove_consistency"] <= 1.0
        if result["empty_beat_rate"] is not None:
            assert 0.0 <= result["empty_beat_rate"] <= 1.0

    def test_all_scenarios(self, all_lab_midis: list[Path]) -> None:
        """Smoke test MusPy metrics on all scenarios."""
        from harmonium_lab.muspy_metrics import compute_muspy_metrics

        for path in all_lab_midis:
            result = compute_muspy_metrics(path)
            assert result["pitch_range"] is not None and result["pitch_range"] > 0, (
                f"{path.stem}: pitch range is 0 or None"
            )


# ---------------------------------------------------------------------------
# MGEval metrics tests
# ---------------------------------------------------------------------------


class TestMgevalMetrics:
    """Test harmonium_lab.mgeval_metrics module."""

    def test_pitch_class_histogram(self, lab_midi_path: Path) -> None:
        from harmonium_lab.mgeval_metrics import pitch_class_histogram

        hist = pitch_class_histogram(lab_midi_path)
        assert hist.shape == (12,)
        assert abs(hist.sum() - 1.0) < 1e-6  # normalized
        assert np.all(hist >= 0)

    def test_note_length_histogram(self, lab_midi_path: Path) -> None:
        from harmonium_lab.mgeval_metrics import note_length_histogram

        hist = note_length_histogram(lab_midi_path)
        assert hist.shape == (12,)
        assert abs(hist.sum() - 1.0) < 1e-6
        assert np.all(hist >= 0)

    def test_onset_histogram(self, lab_midi_path: Path) -> None:
        from harmonium_lab.mgeval_metrics import onset_histogram

        hist = onset_histogram(lab_midi_path)
        assert hist.shape == (16,)
        assert abs(hist.sum() - 1.0) < 1e-6
        assert np.all(hist >= 0)

    def test_overlap_area(self) -> None:
        from harmonium_lab.mgeval_metrics import overlap_area

        a = np.array([0.5, 0.3, 0.2])
        b = np.array([0.5, 0.3, 0.2])
        assert abs(overlap_area(a, b) - 1.0) < 1e-6  # identical

        c = np.array([1.0, 0.0, 0.0])
        d = np.array([0.0, 1.0, 0.0])
        assert abs(overlap_area(c, d)) < 1e-6  # no overlap

    def test_kl_divergence(self) -> None:
        from harmonium_lab.mgeval_metrics import kl_divergence

        a = np.array([0.5, 0.3, 0.2])
        assert kl_divergence(a, a) < 1e-4  # identical → ~0

        b = np.array([0.1, 0.8, 0.1])
        assert kl_divergence(a, b) > 0  # different → positive

    def test_self_comparison(self, lab_midi_path: Path) -> None:
        """Compare a MIDI file against itself — should yield perfect overlap."""
        from harmonium_lab.mgeval_metrics import compare_to_reference

        result = compare_to_reference(lab_midi_path, [lab_midi_path])

        assert result["reference_count"] == 1
        assert result["pitch_class"]["overlap_area"] > 0.99
        assert result["pitch_class"]["kl_divergence"] < 0.01
        assert result["note_length"]["overlap_area"] > 0.99

    def test_cross_comparison(self, all_lab_midis: list[Path]) -> None:
        """Compare one scenario against others as pseudo-reference."""
        from harmonium_lab.mgeval_metrics import compare_to_reference

        generated = all_lab_midis[0]
        references = all_lab_midis[1:]
        result = compare_to_reference(generated, references)

        assert result["reference_count"] == len(references)
        # Overlap should be > 0 (they're all harmonium output)
        assert result["pitch_class"]["overlap_area"] > 0.0
        assert result["note_length"]["overlap_area"] > 0.0
