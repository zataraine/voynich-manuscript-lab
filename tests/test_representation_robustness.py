from __future__ import annotations

from pathlib import Path

import numpy as np

from manuscript_lab.ivtff import parse_ivtff
from manuscript_lab.representation_robustness import (
    PageUnits,
    _holm,
    page_features,
    unitize_locus,
)


def _locus(tmp_path: Path, surface: str):
    path = tmp_path / "sta.txt"
    path.write_text(
        f"#=IVTFF STA1 2.0 M 1\n<f1r> <! $L=A>\n<f1r.1,@P0> {surface}\n",
        encoding="ascii",
    )
    return parse_ivtff(path, witness_id="TEST").loci[0]


def test_uncertainty_views_are_explicit_and_atomic(tmp_path: Path) -> None:
    locus = _locus(tmp_path, "A1[B1:C1D1],E1.???F1?{G1H1}<->I1")

    assert unitize_locus(locus, alternative_policy="first", uncertain_space_policy="split") == (
        ("A1", "B1"),
        ("E1",),
        ("<UNKN>", "F1", "<UNK1>", "<LIG:{G1H1}>"),
        ("I1",),
    )
    assert unitize_locus(locus, alternative_policy="last", uncertain_space_policy="join")[0] == (
        "A1",
        "C1",
        "D1",
        "E1",
    )
    assert unitize_locus(locus, alternative_policy="opaque", uncertain_space_policy="join")[0] == (
        "A1",
        "<ALT>",
        "E1",
    )


def test_feature_panel_respects_group_and_locus_boundaries() -> None:
    page = PageUnits(
        loci=(
            (("A1", "A1", "B1"), ("A1", "B1")),
            (("A1", "A1", "B1"),),
        )
    )
    features = page_features(page)

    assert set(features) == {
        "symbol_entropy_normalized",
        "symbol_conditional_entropy_normalized",
        "symbol_repeat_rate",
        "symbol_bigram_type_ratio",
        "group_length_mean",
        "group_length_cv",
        "group_type_token_ratio",
        "group_hapax_ratio",
        "adjacent_group_repeat_rate",
        "window20_group_recurrence",
    }
    assert np.isclose(features["symbol_repeat_rate"], 2 / 5)
    assert np.isclose(features["adjacent_group_repeat_rate"], 0.0)
    assert np.isclose(features["window20_group_recurrence"], 0.0)


def test_holm_adjustment_is_monotone_in_rank() -> None:
    adjusted = _holm({"a": 0.01, "b": 0.03, "c": 0.02})
    assert adjusted == {"a": 0.03, "c": 0.04, "b": 0.04}
