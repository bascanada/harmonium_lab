"""Tests for Phase 6: CI integration and CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

from harmonium_lab.ci import (
    ComparisonReport,
    GateResult,
    check_quality_gate,
    compare_runs,
    format_comparison,
    format_gate_result,
    load_baseline,
    save_baseline,
)


# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------


def make_report(composite: float = 75.0, **concern_overrides) -> dict:
    """Create a minimal quality report for testing."""
    concerns = {
        "tonal": 80.0, "consonance": 70.0, "melodic": 75.0,
        "rhythmic": 72.0, "voice_leading": 85.0,
    }
    concerns.update(concern_overrides)
    return {
        "composite_score": composite,
        "concern_scores": concerns,
        "z_scores": {
            "music21_key_correlation": {"value": 0.82, "z": 0.4, "status": "ok"},
            "muspy_scale_consistency": {"value": 0.88, "z": 0.0, "status": "ok"},
            "muspy_groove_consistency": {"value": 0.65, "z": -0.9, "status": "ok"},
            "muspy_empty_beat_rate": {"value": 0.25, "z": -1.0, "status": "ok"},
        },
    }


# ---------------------------------------------------------------------------
# Compare runs
# ---------------------------------------------------------------------------


class TestCompareRuns:
    def test_identical_runs(self) -> None:
        report = make_report()
        comp = compare_runs(report, report)
        assert comp.composite_delta == 0.0
        assert len(comp.improvements) == 0
        assert len(comp.regressions) == 0

    def test_improvement_detected(self) -> None:
        before = make_report(composite=60.0)
        after = make_report(composite=75.0)
        # Increase key correlation
        after["z_scores"]["music21_key_correlation"]["value"] = 0.90
        comp = compare_runs(before, after)
        assert comp.composite_delta == 15.0

        improved_metrics = {d.metric for d in comp.improvements}
        assert "music21_key_correlation" in improved_metrics

    def test_regression_detected(self) -> None:
        before = make_report(composite=75.0)
        after = make_report(composite=60.0)
        # Decrease groove consistency
        after["z_scores"]["muspy_groove_consistency"]["value"] = 0.40
        comp = compare_runs(before, after)

        regressed_metrics = {d.metric for d in comp.regressions}
        assert "muspy_groove_consistency" in regressed_metrics

    def test_format_comparison(self) -> None:
        before = make_report(composite=60.0)
        after = make_report(composite=75.0)
        comp = compare_runs(before, after)
        text = format_comparison(comp)
        assert "60.0" in text
        assert "75.0" in text


# ---------------------------------------------------------------------------
# Quality gate
# ---------------------------------------------------------------------------


class TestQualityGate:
    def test_passes_good_report(self) -> None:
        report = make_report(composite=75.0)
        result = check_quality_gate(report)
        assert result.passed

    def test_fails_low_composite(self) -> None:
        report = make_report(composite=30.0)
        result = check_quality_gate(report, min_composite=40.0)
        assert not result.passed
        assert any("Composite" in r for r in result.reasons)

    def test_fails_high_z_score(self) -> None:
        report = make_report()
        report["z_scores"]["music21_key_correlation"]["z"] = 4.0
        result = check_quality_gate(report, max_z_score=3.0)
        assert not result.passed

    def test_fails_concern_drop_vs_baseline(self) -> None:
        baseline = make_report(composite=80.0, tonal=90.0)
        current = make_report(composite=70.0, tonal=70.0)  # 20 point drop
        result = check_quality_gate(current, baseline=baseline, max_concern_drop=15.0)
        assert not result.passed
        assert any("tonal" in r for r in result.reasons)

    def test_passes_with_baseline(self) -> None:
        baseline = make_report(composite=75.0)
        current = make_report(composite=72.0)  # small drop
        result = check_quality_gate(current, baseline=baseline)
        assert result.passed

    def test_format_gate_result(self) -> None:
        result = GateResult(passed=True)
        assert "PASSED" in format_gate_result(result)

        result = GateResult(passed=False, reasons=["score too low"])
        text = format_gate_result(result)
        assert "FAILED" in text
        assert "score too low" in text


# ---------------------------------------------------------------------------
# Baseline save/load
# ---------------------------------------------------------------------------


class TestBaseline:
    def test_save_load_roundtrip(self, tmp_path: Path) -> None:
        reports = {"scenario_a": make_report(70.0), "scenario_b": make_report(80.0)}
        path = tmp_path / "baseline.json"

        save_baseline(reports, path)
        loaded = load_baseline(path)

        assert "scenario_a" in loaded
        assert "scenario_b" in loaded
        assert loaded["scenario_a"]["composite_score"] == 70.0


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


class TestCLI:
    def test_no_args_shows_help(self) -> None:
        from harmonium_lab.cli import main
        assert main([]) == 0

    def test_analyze_midi(self, generated_music_dir: Path, tmp_path: Path) -> None:
        from harmonium_lab.cli import main

        midi = generated_music_dir / "lab_calm_ambient.mid"
        if not midi.exists():
            pytest.skip("Lab MIDI not found")

        output = tmp_path / "report.json"
        result = main(["analyze", str(midi), "-o", str(output)])
        assert result == 0
        assert output.exists()

        import json
        report = json.loads(output.read_text())
        assert "composite_score" in report

    def test_suite(self, generated_music_dir: Path, tmp_path: Path) -> None:
        from harmonium_lab.cli import main

        if not (generated_music_dir / "lab_calm_ambient.mid").exists():
            pytest.skip("Lab MIDI not found")

        output_dir = tmp_path / "reports"
        result = main(["suite", "-i", str(generated_music_dir), "-o", str(output_dir)])
        assert result == 0
        assert (output_dir / "suite_report.json").exists()

        # Verify individual reports exist
        report_files = list(output_dir.glob("lab_*_report.json"))
        assert len(report_files) >= 1

    def test_gate_pass(self, tmp_path: Path) -> None:
        from harmonium_lab.cli import main
        import json

        report = make_report(composite=75.0)
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report))

        result = main(["gate", "--report", str(report_path)])
        assert result == 0  # pass

    def test_gate_fail(self, tmp_path: Path) -> None:
        from harmonium_lab.cli import main
        import json

        report = make_report(composite=20.0)
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report))

        result = main(["gate", "--report", str(report_path), "--min-composite", "40"])
        assert result == 1  # fail
