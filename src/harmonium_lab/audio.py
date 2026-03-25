"""Audio-level music analysis using librosa (+ FluidSynth for MIDI rendering).

Analyzes harmonium's output at the psychoacoustic/audio level. This catches
things symbolic analysis misses — actual perceived dissonance, spectral
complexity, rhythmic feel.

Requires:
  - librosa (always available, installed as core dep)
  - pyfluidsynth + system fluidsynth lib + SoundFont (for MIDI→WAV rendering)

If FluidSynth is not available, rendering is skipped and only pre-rendered
WAV files can be analyzed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

# Lazy imports for optional deps
_FLUIDSYNTH_AVAILABLE: bool | None = None
_LIBROSA_AVAILABLE: bool | None = None


def _check_fluidsynth() -> bool:
    global _FLUIDSYNTH_AVAILABLE
    if _FLUIDSYNTH_AVAILABLE is None:
        try:
            import fluidsynth  # noqa: F401
            _FLUIDSYNTH_AVAILABLE = True
        except (ImportError, OSError):
            _FLUIDSYNTH_AVAILABLE = False
    return _FLUIDSYNTH_AVAILABLE


def _check_librosa() -> bool:
    global _LIBROSA_AVAILABLE
    if _LIBROSA_AVAILABLE is None:
        try:
            import librosa  # noqa: F401
            _LIBROSA_AVAILABLE = True
        except ImportError:
            _LIBROSA_AVAILABLE = False
    return _LIBROSA_AVAILABLE


# ---------------------------------------------------------------------------
# MIDI → WAV rendering
# ---------------------------------------------------------------------------

# Common SoundFont search paths (Linux)
_SOUNDFONT_PATHS = [
    "/usr/share/soundfonts/FluidR3_GM.sf2",
    "/usr/share/soundfonts/default.sf2",
    "/usr/share/sounds/sf2/FluidR3_GM.sf2",
    "/usr/share/sounds/sf2/default.sf2",
    "/usr/share/soundfonts/FluidR3_GS.sf2",
]


def find_soundfont() -> str | None:
    """Find a GM SoundFont on the system."""
    for path in _SOUNDFONT_PATHS:
        if Path(path).exists():
            return path
    return None


def render_midi_to_wav(
    midi_path: Path | str,
    output_path: Path | str | None = None,
    soundfont_path: str | None = None,
    sample_rate: int = 22050,
) -> np.ndarray:
    """Render a MIDI file to audio using FluidSynth via pretty_midi.

    Args:
        midi_path: Path to .mid file
        output_path: Optional path to save .wav file
        soundfont_path: Path to .sf2 SoundFont (auto-detected if None)
        sample_rate: Output sample rate

    Returns:
        numpy array of audio samples (mono, float32)

    Raises:
        RuntimeError: If FluidSynth is not available
    """
    import pretty_midi

    if not _check_fluidsynth():
        raise RuntimeError(
            "FluidSynth not available. Install with: "
            "sudo dnf install fluidsynth fluid-soundfont-gm"
        )

    if soundfont_path is None:
        soundfont_path = find_soundfont()
        if soundfont_path is None:
            raise RuntimeError(
                "No SoundFont found. Install with: "
                "sudo dnf install fluid-soundfont-gm"
            )

    pm = pretty_midi.PrettyMIDI(str(midi_path))
    audio = pm.fluidsynth(fs=sample_rate, sf2_path=soundfont_path)

    if output_path is not None:
        import soundfile as sf
        sf.write(str(output_path), audio, sample_rate)

    return audio


def load_audio(
    path: Path | str,
    sample_rate: int = 22050,
) -> tuple[np.ndarray, int]:
    """Load an audio file (WAV, FLAC, etc.) using librosa.

    Returns:
        (audio_array, sample_rate)
    """
    import librosa
    y, sr = librosa.load(str(path), sr=sample_rate, mono=True)
    return y, sr


# ---------------------------------------------------------------------------
# Audio analysis functions (using librosa)
# ---------------------------------------------------------------------------


def analyze_spectral(
    y: np.ndarray,
    sr: int = 22050,
) -> dict[str, Any]:
    """Analyze spectral characteristics.

    Returns:
        dict with spectral_centroid, spectral_bandwidth, spectral_flatness,
        spectral_rolloff, spectral_contrast (means and stds)
    """
    import librosa

    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    flatness = librosa.feature.spectral_flatness(y=y)[0]
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]

    return {
        "spectral_centroid_mean": round(float(np.mean(centroid)), 2),
        "spectral_centroid_std": round(float(np.std(centroid)), 2),
        "spectral_bandwidth_mean": round(float(np.mean(bandwidth)), 2),
        "spectral_flatness_mean": round(float(np.mean(flatness)), 6),
        "spectral_flatness_std": round(float(np.std(flatness)), 6),
        "spectral_rolloff_mean": round(float(np.mean(rolloff)), 2),
    }


def analyze_rhythm(
    y: np.ndarray,
    sr: int = 22050,
) -> dict[str, Any]:
    """Analyze rhythmic characteristics.

    Returns:
        dict with detected_tempo, beat_count, onset_rate,
        tempo_stability
    """
    import librosa

    # Tempo and beats
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    tempo_val = float(np.squeeze(tempo))

    # Onsets
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    duration = len(y) / sr
    onset_rate = len(onset_times) / duration if duration > 0 else 0.0

    # Tempo stability: std of inter-beat intervals
    beat_times = librosa.frames_to_time(beats, sr=sr)
    if len(beat_times) > 1:
        ibis = np.diff(beat_times)
        tempo_stability = 1.0 - min(float(np.std(ibis) / np.mean(ibis)), 1.0)
    else:
        tempo_stability = 0.0

    return {
        "detected_tempo": round(tempo_val, 1),
        "beat_count": len(beats),
        "onset_rate": round(onset_rate, 2),
        "tempo_stability": round(tempo_stability, 4),
        "duration": round(duration, 2),
    }


def analyze_tonal(
    y: np.ndarray,
    sr: int = 22050,
) -> dict[str, Any]:
    """Analyze tonal characteristics using chroma features.

    Returns:
        dict with key estimate, key_strength, chroma_energy distribution
    """
    import librosa

    # Chroma features (similar to Essentia HPCP)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)

    # Key estimation: strongest pitch class
    pitch_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    key_idx = int(np.argmax(chroma_mean))
    key_name = pitch_names[key_idx]

    # Key strength: ratio of strongest to mean
    key_strength = float(chroma_mean[key_idx] / (np.mean(chroma_mean) + 1e-10))

    # Tonal power ratio: energy in top 3 pitch classes vs total
    sorted_chroma = np.sort(chroma_mean)[::-1]
    tonal_power = float(np.sum(sorted_chroma[:3]) / (np.sum(chroma_mean) + 1e-10))

    return {
        "estimated_key": key_name,
        "key_strength": round(key_strength, 4),
        "tonal_power_ratio": round(tonal_power, 4),
        "chroma_entropy": round(float(-np.sum(
            (chroma_mean / (chroma_mean.sum() + 1e-10)) *
            np.log2(chroma_mean / (chroma_mean.sum() + 1e-10) + 1e-10)
        )), 4),
    }


def analyze_dynamics(
    y: np.ndarray,
    sr: int = 22050,
) -> dict[str, Any]:
    """Analyze dynamic range and loudness.

    Returns:
        dict with rms_mean, rms_std, dynamic_range, loudness_lufs_approx
    """
    import librosa

    rms = librosa.feature.rms(y=y)[0]
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)

    return {
        "rms_mean": round(float(np.mean(rms)), 6),
        "rms_std": round(float(np.std(rms)), 6),
        "dynamic_range_db": round(float(np.max(rms_db) - np.min(rms_db)), 2),
        "rms_db_mean": round(float(np.mean(rms_db)), 2),
    }


def analyze_dissonance(
    y: np.ndarray,
    sr: int = 22050,
) -> dict[str, Any]:
    """Estimate dissonance using spectral characteristics.

    Uses spectral flatness as a proxy for dissonance/noise ratio,
    and harmonic-to-percussive ratio for tonal clarity.

    Returns:
        dict with harmonic_ratio, percussive_ratio, flatness (dissonance proxy)
    """
    import librosa

    # Harmonic-percussive separation
    y_harmonic, y_percussive = librosa.effects.hpss(y)
    harmonic_energy = float(np.sum(y_harmonic ** 2))
    percussive_energy = float(np.sum(y_percussive ** 2))
    total_energy = harmonic_energy + percussive_energy + 1e-10

    # Spectral flatness (Wiener entropy) — closer to 1 = more noise-like/dissonant
    flatness = librosa.feature.spectral_flatness(y=y)[0]

    return {
        "harmonic_ratio": round(harmonic_energy / total_energy, 4),
        "percussive_ratio": round(percussive_energy / total_energy, 4),
        "dissonance_proxy": round(float(np.mean(flatness)), 6),
        "dissonance_std": round(float(np.std(flatness)), 6),
    }


# ---------------------------------------------------------------------------
# Full audio analysis
# ---------------------------------------------------------------------------


def full_audio_analysis(
    audio: np.ndarray,
    sr: int = 22050,
) -> dict[str, Any]:
    """Run all audio analyses on an audio array.

    Args:
        audio: mono audio samples (float32)
        sr: sample rate

    Returns:
        dict with spectral, rhythm, tonal, dynamics, dissonance sections
    """
    return {
        "spectral": analyze_spectral(audio, sr),
        "rhythm": analyze_rhythm(audio, sr),
        "tonal": analyze_tonal(audio, sr),
        "dynamics": analyze_dynamics(audio, sr),
        "dissonance": analyze_dissonance(audio, sr),
    }


def analyze_midi_file(
    midi_path: Path | str,
    soundfont_path: str | None = None,
    sample_rate: int = 22050,
) -> dict[str, Any]:
    """Full audio analysis pipeline: MIDI → render → analyze.

    Args:
        midi_path: Path to .mid file
        soundfont_path: Optional SoundFont path
        sample_rate: Rendering sample rate

    Returns:
        Full audio analysis dict

    Raises:
        RuntimeError: If FluidSynth not available
    """
    audio = render_midi_to_wav(midi_path, sample_rate=sample_rate, soundfont_path=soundfont_path)
    return full_audio_analysis(audio, sample_rate)


def analyze_wav_file(
    wav_path: Path | str,
    sample_rate: int = 22050,
) -> dict[str, Any]:
    """Full audio analysis on an existing WAV file.

    Args:
        wav_path: Path to .wav file
        sample_rate: Target sample rate for analysis

    Returns:
        Full audio analysis dict
    """
    audio, sr = load_audio(wav_path, sample_rate)
    return full_audio_analysis(audio, sr)
