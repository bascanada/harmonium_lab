"""Tests for Phase 4: composite scoring and reference profiles."""

from __future__ import annotations

from pathlib import Path

import pytest

from harmonium_lab.scorer import (
    MetricStats,
    ReferenceProfile,
    ZScoreResult,
    composite_score,
    compute_concern_scores,
    compute_z_scores,
    deviation_report,
    flatten_metrics,
    quality_report,
)


# ---------------------------------------------------------------------------
# Synthetic reference profile for testing
# ---------------------------------------------------------------------------


def make_synthetic_profile() -> ReferenceProfile:
    """Create a synthetic reference profile with known values."""
    profile = ReferenceProfile(category="test")
    profile.metrics = {
        "music21_key_correlation": MetricStats(mean=0.80, std=0.05, min=0.70, max=0.90, count=10),
        "music21_consonance_ratio": MetricStats(mean=0.75, std=0.08, min=0.60, max=0.90, count=10),
        "music21_step_ratio": MetricStats(mean=0.60, std=0.10, min=0.40, max=0.80, count=10),
        "music21_direction_changes": MetricStats(mean=15.0, std=3.0, min=8.0, max=22.0, count=10),
        "music21_parallel_errors": MetricStats(mean=2.0, std=1.0, min=0.0, max=5.0, count=10),
        "muspy_scale_consistency": MetricStats(mean=0.88, std=0.04, min=0.80, max=0.95, count=10),
        "muspy_pitch_class_entropy": MetricStats(mean=2.8, std=0.3, min=2.2, max=3.4, count=10),
        "muspy_pitch_range": MetricStats(mean=18.0, std=4.0, min=10.0, max=26.0, count=10),
        "muspy_groove_consistency": MetricStats(mean=0.72, std=0.08, min=0.55, max=0.85, count=10),
        "muspy_empty_beat_rate": MetricStats(mean=0.20, std=0.05, min=0.10, max=0.30, count=10),
        "mgeval_pc_overlap": MetricStats(mean=0.80, std=0.06, min=0.65, max=0.90, count=10),
        "mgeval_note_length_overlap": MetricStats(mean=0.75, std=0.07, min=0.60, max=0.85, count=10),
        # Audio metrics
        "audio_key_strength": MetricStats(mean=1.5, std=0.3, min=1.0, max=2.0, count=10),
        "audio_harmonic_ratio": MetricStats(mean=0.85, std=0.05, min=0.70, max=0.95, count=10),
        "audio_dissonance_proxy": MetricStats(mean=0.02, std=0.01, min=0.005, max=0.05, count=10),
        "audio_tempo_stability": MetricStats(mean=0.90, std=0.05, min=0.80, max=0.98, count=10),
        "audio_dynamic_range_db": MetricStats(mean=20.0, std=5.0, min=10.0, max=30.0, count=10),
        "audio_rms_std": MetricStats(mean=0.003, std=0.001, min=0.001, max=0.005, count=10),
    }
    return profile


# ---------------------------------------------------------------------------
# Z-Score tests
# ---------------------------------------------------------------------------


class TestZScores:
    def test_exact_match_z_zero(self) -> None:
        profile = make_synthetic_profile()
        # Metrics exactly at reference mean → z = 0
        metrics = {k: v.mean for k, v in profile.metrics.items()}
        z = compute_z_scores(metrics, profile)

        for name, result in z.items():
            assert abs(result.z_score) < 0.01, f"{name}: z should be ~0"
            assert result.status == "ok"

    def test_one_sigma_deviation(self) -> None:
        profile = make_synthetic_profile()
        # mean=0.80, std=0.05, value=0.86 → z=1.2 (in warn range)
        metrics = {"music21_key_correlation": 0.86}
        z = compute_z_scores(metrics, profile)

        assert abs(z["music21_key_correlation"].z_score - 1.2) < 0.01
        assert z["music21_key_correlation"].status == "warn"

    def test_large_deviation_flagged(self) -> None:
        profile = make_synthetic_profile()
        metrics = {"music21_key_correlation": 0.65}  # z = (0.65-0.80)/0.05 = -3.0
        z = compute_z_scores(metrics, profile)

        assert abs(z["music21_key_correlation"].z_score - (-3.0)) < 0.01
        assert z["music21_key_correlation"].status == "flag"

    def test_inverted_metric(self) -> None:
        profile = make_synthetic_profile()
        # empty_beat_rate: higher is worse (inverted)
        # Value 0.30 with mean=0.20, std=0.05 → raw z=2.0, inverted → -2.0
        metrics = {"muspy_empty_beat_rate": 0.30}
        z = compute_z_scores(metrics, profile)

        assert z["muspy_empty_beat_rate"].z_score < 0  # inverted

    def test_missing_metrics_ignored(self) -> None:
        profile = make_synthetic_profile()
        metrics = {"nonexistent_metric": 42.0}
        z = compute_z_scores(metrics, profile)
        assert len(z) == 0

    def test_none_values_skipped(self) -> None:
        profile = make_synthetic_profile()
        metrics = {"music21_key_correlation": None}
        z = compute_z_scores(metrics, profile)
        assert len(z) == 0


# ---------------------------------------------------------------------------
# Concern scores tests
# ---------------------------------------------------------------------------


class TestConcernScores:
    def test_perfect_scores(self) -> None:
        profile = make_synthetic_profile()
        metrics = {k: v.mean for k, v in profile.metrics.items()}
        z = compute_z_scores(metrics, profile)
        concerns = compute_concern_scores(z)

        for concern, score in concerns.items():
            assert score >= 95.0, f"{concern}: score {score} should be ~100"

    def test_terrible_scores(self) -> None:
        profile = make_synthetic_profile()
        # Everything 5 sigma away
        metrics = {k: v.mean + 5 * v.std for k, v in profile.metrics.items()}
        z = compute_z_scores(metrics, profile)
        concerns = compute_concern_scores(z)

        for concern, score in concerns.items():
            assert score <= 10.0, f"{concern}: score {score} should be low"

    def test_missing_concern_gets_neutral(self) -> None:
        z_scores: dict[str, ZScoreResult] = {}
        concerns = compute_concern_scores(z_scores)

        for score in concerns.values():
            assert score == 50.0  # neutral when no data


# ---------------------------------------------------------------------------
# Composite score tests
# ---------------------------------------------------------------------------


class TestCompositeScore:
    def test_all_perfect(self) -> None:
        concerns = {k: 100.0 for k in ["tonal", "consonance", "melodic", "rhythmic", "voice_leading"]}
        assert composite_score(concerns) == 100.0

    def test_all_zero(self) -> None:
        concerns = {k: 0.0 for k in ["tonal", "consonance", "melodic", "rhythmic", "voice_leading"]}
        assert composite_score(concerns) == 0.0

    def test_weighted_average(self) -> None:
        concerns = {
            "tonal": 80.0,
            "consonance": 60.0,
            "melodic": 70.0,
            "rhythmic": 50.0,
            "voice_leading": 90.0,
        }
        score = composite_score(concerns)
        assert 50.0 < score < 80.0  # sanity check


# ---------------------------------------------------------------------------
# Deviation report tests
# ---------------------------------------------------------------------------


class TestDeviationReport:
    def test_top_5(self) -> None:
        profile = make_synthetic_profile()
        metrics = {k: v.mean + (i * v.std) for i, (k, v) in enumerate(profile.metrics.items())}
        z = compute_z_scores(metrics, profile)
        devs = deviation_report(z, top_n=5)

        assert len(devs) <= 5
        # Should be sorted by |z| descending
        z_values = [abs(d["z_score"]) for d in devs]
        assert z_values == sorted(z_values, reverse=True)


# ---------------------------------------------------------------------------
# Flatten metrics tests
# ---------------------------------------------------------------------------


class TestFlattenMetrics:
    def test_flatten_symbolic(self) -> None:
        symbolic = {
            "key_stability": {"avg_correlation": 0.82},
            "consonance": {"consonance_ratio": 0.75},
            "contour": {"step_ratio": 0.6, "direction_changes": 12},
            "voice_leading": {"parallel_fifths": 1, "parallel_octaves": 0},
        }
        flat = flatten_metrics(symbolic=symbolic)

        assert flat["music21_key_correlation"] == 0.82
        assert flat["music21_consonance_ratio"] == 0.75
        assert flat["music21_step_ratio"] == 0.6
        assert flat["music21_parallel_errors"] == 1

    def test_flatten_muspy(self) -> None:
        muspy = {"scale_consistency": 0.88, "groove_consistency": 0.72}
        flat = flatten_metrics(muspy=muspy)

        assert flat["muspy_scale_consistency"] == 0.88
        assert flat["muspy_groove_consistency"] == 0.72


# ---------------------------------------------------------------------------
# Full quality report tests
# ---------------------------------------------------------------------------


class TestQualityReport:
    def test_full_report_structure(self) -> None:
        profile = make_synthetic_profile()
        metrics = {k: v.mean for k, v in profile.metrics.items()}
        report = quality_report(metrics, profile, scenario_params={"tension": 0.3})

        assert "composite_score" in report
        assert "concern_scores" in report
        assert "reference_category" in report
        assert "top_deviations" in report
        assert "z_scores" in report
        assert report["reference_category"] == "test"
        assert 0 <= report["composite_score"] <= 100


# ---------------------------------------------------------------------------
# Integration: profile from real MIDI, score against itself
# ---------------------------------------------------------------------------


class TestScoringIntegration:
    def test_self_score_high(self, generated_music_dir: Path) -> None:
        """Build a profile from lab MIDIs, then score one against itself.

        Self-referencing should produce high scores (~80+).
        """
        from harmonium_lab.profiles import build_profile_from_midis

        midis = sorted(generated_music_dir.glob("lab_*.mid"))
        if len(midis) < 2:
            pytest.skip("Lab MIDI files not found (run `make test/lab-export`)")

        # Build profile from all lab MIDIs
        profile = build_profile_from_midis(midis, category="self-test")
        assert len(profile.metrics) > 0

        # Score one MIDI against the profile
        from harmonium_lab.muspy_metrics import compute_muspy_metrics
        from harmonium_lab.symbolic import full_symbolic_analysis

        test_midi = midis[0]
        symbolic = full_symbolic_analysis(test_midi)
        muspy = compute_muspy_metrics(test_midi)
        flat = flatten_metrics(symbolic=symbolic, muspy=muspy)

        report = quality_report(flat, profile)
        assert report["composite_score"] > 50.0, (
            f"Self-referencing score should be decent, got {report['composite_score']}"
        )

    def test_profile_save_load(self, tmp_path: Path) -> None:
        """Test profile serialization round-trip."""
        from harmonium_lab.profiles import load_profile, save_profile

        profile = make_synthetic_profile()
        path = tmp_path / "test_profile.json"
        save_profile(profile, path)

        loaded = load_profile(path)
        assert loaded.category == "test"
        assert len(loaded.metrics) == len(profile.metrics)
        for k, v in profile.metrics.items():
            assert k in loaded.metrics
            assert abs(loaded.metrics[k].mean - v.mean) < 1e-4
