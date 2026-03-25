"""Composite scoring with reference comparison.

Combines metrics from symbolic (and optionally audio) analysis layers
into reference-relative quality scores. Scoring is always relative to
a reference profile — raw numbers are meaningless without context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Concern definitions: which metrics contribute to which quality concern
# ---------------------------------------------------------------------------

# Concern → {metric_name: weight}
# Weights within each concern are re-normalized at scoring time
# to handle missing metrics (e.g., audio metrics when FluidSynth unavailable)
CONCERN_METRICS: dict[str, dict[str, float]] = {
    "tonal": {
        "music21_key_correlation": 0.30,
        "muspy_scale_consistency": 0.30,
        "mgeval_pc_overlap": 0.20,
        "audio_key_strength": 0.20,
    },
    "consonance": {
        "music21_consonance_ratio": 0.50,
        "audio_harmonic_ratio": 0.30,
        "audio_dissonance_proxy": 0.20,  # inverted
    },
    "melodic": {
        "music21_step_ratio": 0.30,
        "muspy_pitch_class_entropy": 0.30,
        "muspy_pitch_range": 0.20,
        "music21_direction_changes": 0.20,
    },
    "rhythmic": {
        "muspy_groove_consistency": 0.25,
        "muspy_empty_beat_rate": 0.25,  # inverted
        "mgeval_note_length_overlap": 0.25,
        "audio_tempo_stability": 0.25,
    },
    "dynamics": {
        "music21_velocity_std": 0.35,
        "music21_velocity_range": 0.25,
        "audio_dynamic_range_db": 0.20,
        "audio_rms_std": 0.20,
    },
    "voice_leading": {
        "music21_parallel_errors": 1.0,  # inverted (fewer is better)
    },
}

# Overall composite weights across concerns
COMPOSITE_WEIGHTS: dict[str, float] = {
    "tonal": 0.22,
    "consonance": 0.18,
    "melodic": 0.18,
    "rhythmic": 0.18,
    "dynamics": 0.10,
    "voice_leading": 0.14,
}

# Metrics where lower is better (inverted for z-score calculation)
INVERTED_METRICS = {
    "muspy_empty_beat_rate",
    "music21_parallel_errors",
    "audio_dissonance_proxy",
}


# ---------------------------------------------------------------------------
# Reference Profile
# ---------------------------------------------------------------------------


@dataclass
class MetricStats:
    """Distribution statistics for a single metric in the reference corpus."""
    mean: float
    std: float
    min: float = 0.0
    max: float = 0.0
    count: int = 0


@dataclass
class ReferenceProfile:
    """Per-metric distribution from a reference corpus."""
    category: str
    metrics: dict[str, MetricStats] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "metrics": {
                k: {"mean": v.mean, "std": v.std, "min": v.min, "max": v.max, "count": v.count}
                for k, v in self.metrics.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReferenceProfile:
        profile = cls(category=data["category"])
        for k, v in data.get("metrics", {}).items():
            profile.metrics[k] = MetricStats(
                mean=v["mean"],
                std=v["std"],
                min=v.get("min", 0.0),
                max=v.get("max", 0.0),
                count=v.get("count", 0),
            )
        return profile


# ---------------------------------------------------------------------------
# Z-Score computation
# ---------------------------------------------------------------------------


@dataclass
class ZScoreResult:
    """Z-score for a single metric."""
    metric: str
    value: float
    ref_mean: float
    ref_std: float
    z_score: float
    status: str  # "ok", "warn", "flag"


def compute_z_scores(
    metrics: dict[str, float | None],
    reference: ReferenceProfile,
) -> dict[str, ZScoreResult]:
    """Compute z-scores for all metrics that exist in both input and reference.

    Args:
        metrics: {metric_name: value} from analysis
        reference: ReferenceProfile with per-metric distributions

    Returns:
        {metric_name: ZScoreResult}
    """
    results: dict[str, ZScoreResult] = {}

    for name, value in metrics.items():
        if value is None or name not in reference.metrics:
            continue

        stats = reference.metrics[name]
        if stats.std == 0:
            z = 0.0
        else:
            z = (value - stats.mean) / stats.std

        # For inverted metrics, negate so positive z = worse
        if name in INVERTED_METRICS:
            z = -z

        if abs(z) < 1.0:
            status = "ok"
        elif abs(z) < 2.0:
            status = "warn"
        else:
            status = "flag"

        results[name] = ZScoreResult(
            metric=name,
            value=value,
            ref_mean=stats.mean,
            ref_std=stats.std,
            z_score=round(z, 4),
            status=status,
        )

    return results


# ---------------------------------------------------------------------------
# Per-concern scores
# ---------------------------------------------------------------------------


def compute_concern_scores(
    z_scores: dict[str, ZScoreResult],
) -> dict[str, float]:
    """Compute per-concern quality scores (0-100).

    Score = 100 - (weighted average of |z_score| * 20), clamped to [0, 100].
    100 = identical to reference, 0 = completely unlike reference.

    Only includes metrics that have z-scores available (handles missing
    audio metrics gracefully by re-normalizing weights).
    """
    concern_scores: dict[str, float] = {}

    for concern, metric_weights in CONCERN_METRICS.items():
        # Filter to available metrics
        available = {m: w for m, w in metric_weights.items() if m in z_scores}
        if not available:
            concern_scores[concern] = 50.0  # neutral if no data
            continue

        # Re-normalize weights
        total_weight = sum(available.values())
        weighted_abs_z = sum(
            abs(z_scores[m].z_score) * (w / total_weight)
            for m, w in available.items()
        )

        score = 100.0 - (weighted_abs_z * 20.0)
        concern_scores[concern] = round(max(0.0, min(100.0, score)), 1)

    return concern_scores


# ---------------------------------------------------------------------------
# Composite score
# ---------------------------------------------------------------------------


def composite_score(concern_scores: dict[str, float]) -> float:
    """Compute overall weighted composite score (0-100).

    Uses COMPOSITE_WEIGHTS to combine per-concern scores.
    """
    total = 0.0
    weight_sum = 0.0

    for concern, weight in COMPOSITE_WEIGHTS.items():
        if concern in concern_scores:
            total += concern_scores[concern] * weight
            weight_sum += weight

    if weight_sum == 0:
        return 50.0
    return round(total / weight_sum * sum(COMPOSITE_WEIGHTS.values()) / weight_sum
                 if False else total / weight_sum, 1)


# ---------------------------------------------------------------------------
# Deviation report
# ---------------------------------------------------------------------------


def deviation_report(
    z_scores: dict[str, ZScoreResult],
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """Return the top-N worst deviations sorted by |z_score|.

    Each entry includes: metric name, value, reference mean±std, z_score,
    which concern it belongs to, and status.
    """
    # Build concern lookup
    metric_to_concern: dict[str, str] = {}
    for concern, metrics in CONCERN_METRICS.items():
        for metric in metrics:
            metric_to_concern[metric] = concern

    sorted_z = sorted(z_scores.values(), key=lambda r: abs(r.z_score), reverse=True)

    deviations = []
    for r in sorted_z[:top_n]:
        deviations.append({
            "metric": r.metric,
            "value": r.value,
            "ref": f"{r.ref_mean:.4f} ± {r.ref_std:.4f}",
            "z_score": r.z_score,
            "concern": metric_to_concern.get(r.metric, "other"),
            "status": r.status,
        })

    return deviations


# ---------------------------------------------------------------------------
# Full quality report
# ---------------------------------------------------------------------------


def quality_report(
    metrics: dict[str, float | None],
    reference: ReferenceProfile,
    scenario_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a complete quality report.

    Args:
        metrics: flat dict of {metric_name: value} from all analysis layers
        reference: ReferenceProfile for the target category
        scenario_params: optional engine parameters for context

    Returns:
        Complete quality report dict
    """
    z = compute_z_scores(metrics, reference)
    concerns = compute_concern_scores(z)
    comp = composite_score(concerns)
    devs = deviation_report(z)

    return {
        "composite_score": comp,
        "concern_scores": concerns,
        "reference_category": reference.category,
        "top_deviations": devs,
        "scenario_params": scenario_params or {},
        "z_scores": {k: {"value": v.value, "z": v.z_score, "status": v.status}
                     for k, v in z.items()},
    }


# ---------------------------------------------------------------------------
# Flatten metrics from analysis results
# ---------------------------------------------------------------------------


def flatten_metrics(
    symbolic: dict[str, Any] | None = None,
    muspy: dict[str, Any] | None = None,
    mgeval: dict[str, Any] | None = None,
    audio: dict[str, Any] | None = None,
) -> dict[str, float | None]:
    """Flatten analysis results into a single metric dict for scoring.

    Maps analysis output keys to the metric names used by the scorer.
    Audio metrics are optional — omit when FluidSynth is unavailable.
    """
    flat: dict[str, float | None] = {}

    if symbolic:
        ks = symbolic.get("key_stability", {})
        flat["music21_key_correlation"] = ks.get("avg_correlation")
        cons = symbolic.get("consonance", {})
        flat["music21_consonance_ratio"] = cons.get("consonance_ratio")
        cont = symbolic.get("contour", {})
        flat["music21_step_ratio"] = cont.get("step_ratio")
        flat["music21_direction_changes"] = cont.get("direction_changes")
        vl = symbolic.get("voice_leading", {})
        flat["music21_parallel_errors"] = (
            (vl.get("parallel_fifths", 0) or 0) + (vl.get("parallel_octaves", 0) or 0)
        )
        vel = symbolic.get("velocity", {})
        flat["music21_velocity_std"] = vel.get("velocity_std")
        flat["music21_velocity_range"] = vel.get("velocity_range")

    if muspy:
        flat["muspy_scale_consistency"] = muspy.get("scale_consistency")
        flat["muspy_pitch_class_entropy"] = muspy.get("pitch_class_entropy")
        flat["muspy_pitch_range"] = muspy.get("pitch_range")
        flat["muspy_groove_consistency"] = muspy.get("groove_consistency")
        flat["muspy_empty_beat_rate"] = muspy.get("empty_beat_rate")

    if mgeval:
        pc = mgeval.get("pitch_class", {})
        flat["mgeval_pc_overlap"] = pc.get("overlap_area")
        nl = mgeval.get("note_length", {})
        flat["mgeval_note_length_overlap"] = nl.get("overlap_area")

    if audio:
        tonal = audio.get("tonal", {})
        flat["audio_key_strength"] = tonal.get("key_strength")
        dissonance = audio.get("dissonance", {})
        flat["audio_harmonic_ratio"] = dissonance.get("harmonic_ratio")
        flat["audio_dissonance_proxy"] = dissonance.get("dissonance_proxy")
        rhythm = audio.get("rhythm", {})
        flat["audio_tempo_stability"] = rhythm.get("tempo_stability")
        dynamics = audio.get("dynamics", {})
        flat["audio_dynamic_range_db"] = dynamics.get("dynamic_range_db")
        flat["audio_rms_std"] = dynamics.get("rms_std")

    return flat
