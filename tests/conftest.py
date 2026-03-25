"""Shared test fixtures for harmonium_lab."""

from __future__ import annotations

from pathlib import Path

import pytest

# Root of the harmonium project
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Golden test data from harmonium_core
GOLDEN_MEASURES_DIR = (
    PROJECT_ROOT / "harmonium" / "harmonium_host" / "tests" / "golden_measures"
)

# Generated music from `make test/lab-export`
# Cargo workspace target dir is at the crate level when run directly
GENERATED_MUSIC_DIR = (
    PROJECT_ROOT / "harmonium" / "harmonium_core" / "target" / "generated_music"
)

# Reference corpus
REFERENCES_DIR = Path(__file__).resolve().parent.parent / "references"


@pytest.fixture
def golden_measures_dir() -> Path:
    return GOLDEN_MEASURES_DIR


@pytest.fixture
def generated_music_dir() -> Path:
    return GENERATED_MUSIC_DIR


@pytest.fixture
def references_dir() -> Path:
    return REFERENCES_DIR


@pytest.fixture
def sample_golden_json(golden_measures_dir: Path) -> Path:
    """Return path to a known golden test JSON file."""
    path = golden_measures_dir / "default_seed42_8bars.json"
    if not path.exists():
        pytest.skip(f"Golden test file not found: {path}")
    return path
