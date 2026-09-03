"""Phase 3: confidence is a fixed, code-only formula."""
from __future__ import annotations

from app import confidence


def test_full_corroboration() -> None:
    assert confidence.compute(9, 9, contradiction=False) == 1.0


def test_contradiction_drops_two_signals() -> None:
    assert confidence.compute(9, 9, contradiction=True) == 0.78  # (9-2)/9


def test_no_expected_is_zero() -> None:
    assert confidence.compute(0, 0, contradiction=False) == 0.0


def test_incompleteness_lowers_confidence_via_fixed_denominator() -> None:
    full = confidence.compute(9, 9, contradiction=False)     # 1.0
    partial = confidence.compute(5, 9, contradiction=False)  # 5/9 = 0.56
    assert partial < full  # a missing agent genuinely lowers confidence


def test_never_negative() -> None:
    assert confidence.compute(1, 9, contradiction=True) == 0.0  # max(0, 1-2)/9


def test_trusted_exceeding_expected_is_clamped_not_over_100_percent() -> None:
    # Regression: hypothesis found compute(2, 1, False) == 2.0 before the clamp.
    assert confidence.compute(2, 1, contradiction=False) == 1.0
    assert confidence.compute(1000, 9, contradiction=False) == 1.0
