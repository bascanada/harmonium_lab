"""CI regression detection and quality gating.

Compares quality reports before/after engine changes and enforces
quality thresholds to prevent regressions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MetricDelta:
    """Change in a single metric between two runs."""
    metric: str
    before: float
    after: float
    delta: float
    improved: bool
    concern: str = ""


@dataclass
class ComparisonReport:
    """Result of comparing two quality reports."""
    before_composite: float
    after_composite: float
    composite_delta: float
    improvements: list[MetricDelta] = field(default_factory=list)
    regressions: list[MetricDelta] = field(default_factory=list)
    unchanged: list[MetricDelta] = field(default_factory=list)
    concern_deltas: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "before_composite": self.before_composite,
            "after_composite": self.after_composite,
            "composite_delta": self.composite_delta,
            "improvements": [
                {"metric": d.metric, "before": d.before, "after": d.after,
                 "delta": d.delta, "concern": d.concern}
                for d in self.improvements
            ],
            "regressions": [
                {"metric": d.metric, "before": d.before, "after": d.after,
                 "delta": d.delta, "concern": d.concern}
                for d in self.regressions
            ],
            "concern_deltas": self.concern_deltas,
        }


def compare_runs(
    before: dict[str, Any],
    after: dict[str, Any],
) -> ComparisonReport:
    """Compare two quality reports and identify improvements/regressions.

    Args:
        before: Quality report dict from previous run
        after: Quality report dict from current run

    Returns:
        ComparisonReport with per-metric deltas
    """
    from .scorer import CONCERN_METRICS, INVERTED_METRICS

    before_composite = before.get("composite_score", 0.0)
    after_composite = after.get("composite_score", 0.0)

    # Build concern lookup
    metric_to_concern: dict[str, str] = {}
    for concern, metrics in CONCERN_METRICS.items():
        for metric in metrics:
            metric_to_concern[metric] = concern

    # Compare z-scores
    before_z = before.get("z_scores", {})
    after_z = after.get("z_scores", {})
    all_metrics = set(before_z.keys()) | set(after_z.keys())

    improvements = []
    regressions = []
    unchanged = []

    for metric in sorted(all_metrics):
        b_val = before_z.get(metric, {}).get("value")
        a_val = after_z.get(metric, {}).get("value")
        if b_val is None or a_val is None:
            continue

        delta = round(a_val - b_val, 6)
        # For inverted metrics, negative delta = improvement
        if metric in INVERTED_METRICS:
            improved = delta < -0.001
            regressed = delta > 0.001
        else:
            improved = delta > 0.001
            regressed = delta < -0.001

        md = MetricDelta(
            metric=metric,
            before=b_val,
            after=a_val,
            delta=delta,
            improved=improved,
            concern=metric_to_concern.get(metric, "other"),
        )

        if improved:
            improvements.append(md)
        elif regressed:
            regressions.append(md)
        else:
            unchanged.append(md)

    # Concern score deltas
    before_concerns = before.get("concern_scores", {})
    after_concerns = after.get("concern_scores", {})
    concern_deltas = {}
    for concern in set(before_concerns.keys()) | set(after_concerns.keys()):
        b = before_concerns.get(concern, 50.0)
        a = after_concerns.get(concern, 50.0)
        concern_deltas[concern] = round(a - b, 1)

    return ComparisonReport(
        before_composite=before_composite,
        after_composite=after_composite,
        composite_delta=round(after_composite - before_composite, 1),
        improvements=improvements,
        regressions=regressions,
        unchanged=unchanged,
        concern_deltas=concern_deltas,
    )


@dataclass
class GateResult:
    """Result of a quality gate check."""
    passed: bool
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "reasons": self.reasons}


def check_quality_gate(
    report: dict[str, Any],
    baseline: dict[str, Any] | None = None,
    min_composite: float = 40.0,
    max_concern_drop: float = 15.0,
    max_z_score: float = 3.0,
) -> GateResult:
    """Check if a quality report passes the quality gate.

    Args:
        report: Current quality report dict
        baseline: Optional baseline report to compare against
        min_composite: Minimum acceptable composite score
        max_concern_drop: Maximum acceptable drop in any concern score vs baseline
        max_z_score: Maximum acceptable |z_score| for any metric

    Returns:
        GateResult with pass/fail and reasons
    """
    reasons = []

    composite = report.get("composite_score", 0.0)
    if composite < min_composite:
        reasons.append(
            f"Composite score {composite:.1f} below minimum {min_composite:.1f}"
        )

    # Check individual z-scores
    for metric, z_data in report.get("z_scores", {}).items():
        z = abs(z_data.get("z", 0.0))
        if z > max_z_score:
            reasons.append(
                f"Metric {metric} z-score {z:.2f} exceeds ±{max_z_score}"
            )

    # Compare against baseline if provided
    if baseline is not None:
        baseline_composite = baseline.get("composite_score", 0.0)
        if composite < baseline_composite - max_concern_drop:
            reasons.append(
                f"Composite dropped {baseline_composite:.1f} → {composite:.1f} "
                f"(>{max_concern_drop:.1f} point drop)"
            )

        baseline_concerns = baseline.get("concern_scores", {})
        current_concerns = report.get("concern_scores", {})
        for concern in baseline_concerns:
            b = baseline_concerns[concern]
            a = current_concerns.get(concern, 50.0)
            if b - a > max_concern_drop:
                reasons.append(
                    f"Concern '{concern}' dropped {b:.1f} → {a:.1f} "
                    f"(>{max_concern_drop:.1f} point drop)"
                )

    return GateResult(passed=len(reasons) == 0, reasons=reasons)


# ---------------------------------------------------------------------------
# Baseline management
# ---------------------------------------------------------------------------


def save_baseline(reports: dict[str, Any], path: Path | str) -> None:
    """Save quality reports as a baseline for future comparisons."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(reports, f, indent=2)


def load_baseline(path: Path | str) -> dict[str, Any]:
    """Load a previously saved baseline."""
    with Path(path).open() as f:
        return json.load(f)


def format_comparison(comparison: ComparisonReport) -> str:
    """Format a comparison report as human-readable text."""
    lines = []
    lines.append(f"Composite: {comparison.before_composite:.1f} -> {comparison.after_composite:.1f} ({comparison.composite_delta:+.1f})")
    lines.append("")

    if comparison.improvements:
        lines.append("Improvements:")
        for d in comparison.improvements:
            lines.append(f"  + {d.metric}: {d.before:.4f} -> {d.after:.4f} ({d.delta:+.4f}) [{d.concern}]")

    if comparison.regressions:
        lines.append("Regressions:")
        for d in comparison.regressions:
            lines.append(f"  - {d.metric}: {d.before:.4f} -> {d.after:.4f} ({d.delta:+.4f}) [{d.concern}]")

    if comparison.concern_deltas:
        lines.append("")
        lines.append("Concern deltas:")
        for concern, delta in sorted(comparison.concern_deltas.items()):
            symbol = "+" if delta > 0 else ""
            lines.append(f"  {concern}: {symbol}{delta:.1f}")

    return "\n".join(lines)


def format_gate_result(result: GateResult) -> str:
    """Format a gate result as human-readable text."""
    if result.passed:
        return "PASSED: Quality gate check passed."
    lines = ["FAILED: Quality gate check failed."]
    for reason in result.reasons:
        lines.append(f"  - {reason}")
    return "\n".join(lines)
