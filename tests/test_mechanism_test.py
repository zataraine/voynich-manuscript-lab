from __future__ import annotations

from pathlib import Path

import yaml

import manuscript_lab.mechanism_test as mechanism
from manuscript_lab.mechanism_test import (
    evaluate_predictive_structure,
    generate_variant,
    load_ivtff_pages,
    run_study,
    split_pages,
    validate_result,
)


def _fixture(path: Path) -> None:
    rows = ["#=IVTFF Eva- 2.0 M 5"]
    for index in range(1, 9):
        language = "A" if index <= 4 else "B"
        hand = "1" if index % 2 else "2"
        section = "H" if index % 3 else "A"
        rows.extend(
            [
                f"<f{index}r> <! $L={language} $H={hand} $I={section}>",
                f"<f{index}r.1,@P0> <%>qokedy.qokedy.daiin.chol<$>",
                f"<f{index}r.2,+P0> qokeedy.qokedy.[x:y].daiin",
                f"<f{index}r.3,@L0> excluded.label",
            ]
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_page_loading_split_and_metrics_are_page_safe(tmp_path: Path) -> None:
    source = tmp_path / "synthetic.ivtff"
    _fixture(source)
    pages = load_ivtff_pages(source, currier={"A", "B"})
    assert len(pages) == 8
    assert all("label" not in page.groups for page in pages)
    assert sum(page.excluded_group_count for page in pages) == 8
    train, heldout = split_pages(pages, seed=11, heldout_fraction=0.25)
    assert {page.page_id for page in train}.isdisjoint(page.page_id for page in heldout)
    assert (train, heldout) == split_pages(pages, seed=11, heldout_fraction=0.25)
    metrics = evaluate_predictive_structure(train, heldout, alpha=0.1)
    assert metrics["heldout_char_trigram_gain_bits"] > 0
    assert metrics["heldout_local_copy_rate"] > 0


def test_null_generators_are_seeded_and_preserve_page_shapes(tmp_path: Path) -> None:
    source = tmp_path / "synthetic.ivtff"
    _fixture(source)
    pages = load_ivtff_pages(source)
    families = [
        "within_page_group_shuffle",
        "within_group_symbol_shuffle",
        "global_group_resample",
        "iid_symbol_length_matched",
        "copy_mutate_pseudotext",
    ]
    for family in families:
        first = generate_variant(pages, family, seed=17)
        second = generate_variant(pages, family, seed=17)
        assert first == second
        assert [len(page.groups) for page in first] == [len(page.groups) for page in pages]
        assert [page.page_id for page in first] == [page.page_id for page in pages]


def test_run_study_uses_explicit_nulls_and_refuses_a_posterior(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "data/raw/transcriptions/synthetic.ivtff"
    source.parent.mkdir(parents=True)
    _fixture(source)
    manifest = tmp_path / "data/manifests/synthetic.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("schema_version: '1.0'\n", encoding="utf-8")
    config_path = tmp_path / "config/experiments/test.yaml"
    config_path.parent.mkdir(parents=True)
    config = {
        "experiment_id": "E-SYNTHETIC",
        "hypothesis_id": "H-SYNTHETIC",
        "source_manifest": "data/manifests/synthetic.yaml",
        "normalization": {"version": "test"},
        "seed": 7,
        "parameters": {
            "input_path": "data/raw/transcriptions/synthetic.ivtff",
            "currier_values": ["A", "B"],
            "paragraph_only": True,
            "heldout_fraction": 0.25,
            "ngram_alpha": 0.1,
            "workers": 2,
        },
        "null_model": {
            "families": ["within_page_group_shuffle", "iid_symbol_length_matched"],
            "replicates": 3,
        },
        "metrics": {
            "primary": ["heldout_char_trigram_gain_bits"],
            "decision_rule": "synthetic test",
        },
    }
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    schema_dir.joinpath("mechanism-result.schema.json").write_text(
        (Path(__file__).parents[1] / "schemas/mechanism-result.schema.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text("synthetic-lock\n", encoding="utf-8")
    monkeypatch.setattr(mechanism, "repository_root", lambda: tmp_path)
    result = run_study(config_path)
    validate_result(result)
    assert result["experiment_id"] == "E-SYNTHETIC"
    assert result["interpretation_boundary"]["posterior_probability"] is None
    assert set(result["null_results"]) == {
        "within_page_group_shuffle",
        "iid_symbol_length_matched",
    }
    assert result["provenance"]["source_sha256"]
