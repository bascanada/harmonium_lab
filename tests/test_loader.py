"""Tests for harmonium_lab.loader module."""

from __future__ import annotations

from pathlib import Path

import pytest

from harmonium_lab.loader import load_measures_json, load_scenario_json
from harmonium_lab.types import MeasureData, NoteData, Scenario


class TestLoadMeasuresJson:
    """Test loading MeasureSnapshot JSON arrays."""

    def test_load_golden_file(self, sample_golden_json: Path) -> None:
        measures = load_measures_json(sample_golden_json)
        assert len(measures) > 0
        assert all(isinstance(m, MeasureData) for m in measures)

    def test_measure_fields_valid(self, sample_golden_json: Path) -> None:
        measures = load_measures_json(sample_golden_json)
        for m in measures:
            assert m.index >= 1
            assert m.tempo > 0
            assert m.time_sig_numerator > 0
            assert m.time_sig_denominator > 0
            assert m.steps > 0
            assert isinstance(m.chord_name, str)

    def test_note_fields_valid(self, sample_golden_json: Path) -> None:
        measures = load_measures_json(sample_golden_json)
        for m in measures:
            for n in m.notes:
                assert isinstance(n, NoteData)
                assert 0 <= n.track <= 3
                assert 0 <= n.pitch <= 127
                assert n.start_step >= 0
                assert n.duration_steps >= 0
                assert 0 <= n.velocity <= 127

    def test_notes_within_measure_bounds(self, sample_golden_json: Path) -> None:
        measures = load_measures_json(sample_golden_json)
        for m in measures:
            for n in m.notes:
                assert n.start_step < m.steps, (
                    f"Note start_step {n.start_step} >= measure steps {m.steps}"
                )

    def test_measures_sequential(self, sample_golden_json: Path) -> None:
        measures = load_measures_json(sample_golden_json)
        indices = [m.index for m in measures]
        assert indices == sorted(indices)
        # Indices should be consecutive
        for i in range(1, len(indices)):
            assert indices[i] == indices[i - 1] + 1

    def test_all_golden_files(self, golden_measures_dir: Path) -> None:
        """Smoke test: load every golden JSON file."""
        json_files = sorted(golden_measures_dir.glob("*.json"))
        if not json_files:
            pytest.skip("No golden JSON files found")
        for path in json_files:
            measures = load_measures_json(path)
            assert len(measures) > 0, f"Empty measures in {path.name}"


class TestLabExports:
    """Test loading generated lab export files (MIDI + JSON + scenario)."""

    LAB_SCENARIOS = [
        "lab_calm_ambient",
        "lab_jazz_ballad",
        "lab_jazz_medium",
        "lab_practice_easy",
        "lab_dramatic_high",
    ]

    def test_load_lab_json(self, generated_music_dir: Path) -> None:
        """Load all lab export JSON files."""
        for name in self.LAB_SCENARIOS:
            path = generated_music_dir / f"{name}.json"
            if not path.exists():
                pytest.skip(f"Lab export not found: {path} (run `make test/lab-export`)")
            measures = load_measures_json(path)
            assert len(measures) == 32, f"{name}: expected 32 measures, got {len(measures)}"

    def test_load_lab_scenario_with_metadata(self, generated_music_dir: Path) -> None:
        """Load lab export with scenario metadata."""
        for name in self.LAB_SCENARIOS:
            json_path = generated_music_dir / f"{name}.json"
            meta_path = generated_music_dir / f"{name}_scenario.json"
            if not json_path.exists() or not meta_path.exists():
                pytest.skip(f"Lab export not found (run `make test/lab-export`)")
            scenario = load_scenario_json(json_path, meta_path)
            assert scenario.name == name
            assert scenario.bars == 32
            assert scenario.seed == 42
            assert scenario.params.bpm > 0

    def test_lab_midi_exists(self, generated_music_dir: Path) -> None:
        """Verify MIDI files were generated."""
        for name in self.LAB_SCENARIOS:
            path = generated_music_dir / f"{name}.mid"
            if not path.exists():
                pytest.skip(f"Lab export not found (run `make test/lab-export`)")
            assert path.stat().st_size > 100, f"{name}.mid is suspiciously small"


class TestLoadScenarioJson:
    """Test loading scenarios with metadata."""

    def test_load_without_metadata(self, sample_golden_json: Path) -> None:
        scenario = load_scenario_json(sample_golden_json)
        assert isinstance(scenario, Scenario)
        assert scenario.name == sample_golden_json.stem
        assert len(scenario.measures) > 0
        assert scenario.bars == len(scenario.measures)

    def test_load_with_metadata(self, sample_golden_json: Path, tmp_path: Path) -> None:
        import json

        meta = {
            "scenario": "test_calm",
            "params": {
                "bpm": 80.0,
                "density": 0.25,
                "tension": 0.15,
                "smoothness": 0.8,
                "valence": 0.3,
                "arousal": 0.2,
            },
            "bars": 8,
            "seed": 42,
        }
        meta_path = tmp_path / "scenario.json"
        meta_path.write_text(json.dumps(meta))

        scenario = load_scenario_json(sample_golden_json, meta_path)
        assert scenario.name == "test_calm"
        assert scenario.seed == 42
        assert scenario.params.tension == 0.15
        assert scenario.params.smoothness == 0.8
