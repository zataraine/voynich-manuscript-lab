"""E-012 replication of frozen mechanism effects across STA1 witness views."""

from __future__ import annotations

import math
import multiprocessing
import platform
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import orjson
import yaml

from manuscript_lab.ledger import git_provenance
from manuscript_lab.mechanism_test import (
    PageSequence,
    _family_samples,
    _holm_adjust,
    evaluate_predictive_structure,
    split_pages,
)
from manuscript_lab.provenance import repository_root, sha256_file
from manuscript_lab.representation_robustness import unitize_locus
from manuscript_lab.witness_alignment import load_witness_corpus


def _document_index(loci: tuple[Any, ...]) -> dict[tuple[str, int], tuple[Any, ...]]:
    mutable: dict[tuple[str, int], list[Any]] = {}
    for locus in loci:
        mutable.setdefault((locus.page, locus.number), []).append(locus)
    return {key: tuple(values) for key, values in mutable.items()}


def encode_atomic_groups(
    groups_by_view: dict[str, dict[str, tuple[tuple[str, ...], ...]]],
) -> tuple[dict[str, dict[str, tuple[str, ...]]], dict[str, str], float]:
    """Map each atomic STA1 symbol bijectively to one private-use character."""
    symbols = sorted(
        {
            symbol
            for pages in groups_by_view.values()
            for groups in pages.values()
            for group in groups
            for symbol in group
        }
    )
    if len(symbols) > 6400:
        raise ValueError("atomic symbol inventory exceeds Unicode BMP private-use capacity")
    symbol_map = {symbol: chr(0xE000 + index) for index, symbol in enumerate(symbols)}
    inverse = {value: key for key, value in symbol_map.items()}
    encoded: dict[str, dict[str, tuple[str, ...]]] = {}
    correct = 0
    total = 0
    for view, pages in groups_by_view.items():
        encoded[view] = {}
        for page, groups in pages.items():
            encoded_groups = tuple(
                "".join(symbol_map[symbol] for symbol in group) for group in groups
            )
            encoded[view][page] = encoded_groups
            for source, transported in zip(groups, encoded_groups, strict=True):
                total += 1
                if tuple(inverse[character] for character in transported) == source:
                    correct += 1
    return encoded, symbol_map, correct / total if total else 0.0


def build_corpora(
    config: dict[str, Any],
) -> tuple[dict[str, list[PageSequence]], dict[str, str], dict[str, Any]]:
    """Build ten page-aligned STA1 views on common paragraph loci."""
    root = repository_root()
    corpus = load_witness_corpus(root / config["witness_registry"])
    view_specs = tuple(config["views"]["primary"]) + tuple(config["views"]["uncertainty"])
    names = [str(item["name"]) for item in view_specs]
    if len(names) != len(set(names)):
        raise ValueError("duplicate E-012 view name")
    primary_witnesses = tuple(str(item["witness"]) for item in config["views"]["primary"])
    indexes = {
        witness: _document_index(corpus.comparison_documents[witness].loci)
        for witness in primary_witnesses
    }
    common_keys = set.intersection(*(set(index) for index in indexes.values()))
    zl_document = corpus.comparison_documents["ZL3b"]
    zl_index = indexes["ZL3b"]
    paragraph_keys = {
        key
        for key in common_keys
        if all(locus.locus_type.startswith("P") for locus in zl_index[key])
    }
    page_metadata = {page.page: page.fields for page in zl_document.pages}
    page_order = {page.page: index for index, page in enumerate(zl_document.pages)}
    keys_by_page: dict[str, list[tuple[str, int]]] = {}
    for key in paragraph_keys:
        if page_metadata.get(key[0], {}).get("L") in set(config["scope"]["currier_values"]):
            keys_by_page.setdefault(key[0], []).append(key)
    for keys in keys_by_page.values():
        keys.sort(key=lambda item: item[1])

    token_groups: dict[str, dict[str, tuple[tuple[str, ...], ...]]] = {}
    for spec in view_specs:
        name = str(spec["name"])
        witness = str(spec["witness"])
        index = indexes[witness]
        token_groups[name] = {}
        for page, keys in keys_by_page.items():
            token_groups[name][page] = tuple(
                group
                for key in keys
                for locus in index[key]
                for group in unitize_locus(
                    locus,
                    alternative_policy=str(spec["alternative"]),  # type: ignore[arg-type]
                    uncertain_space_policy=str(spec["uncertain_space"]),  # type: ignore[arg-type]
                )
            )

    primary_names = tuple(str(item["name"]) for item in config["views"]["primary"])
    minimum_groups = int(config["scope"]["minimum_groups_per_page_per_view"])
    minimum_symbols = int(config["scope"]["minimum_symbols_per_page_per_view"])
    eligible_pages = tuple(
        page
        for page in sorted(keys_by_page, key=lambda value: page_order[value])
        if all(
            len(token_groups[name][page]) >= minimum_groups
            and sum(len(group) for group in token_groups[name][page]) >= minimum_symbols
            for name in primary_names
        )
    )
    if len(eligible_pages) < 20:
        raise ValueError("too few eligible common paragraph pages")
    restricted = {
        name: {page: pages[page] for page in eligible_pages} for name, pages in token_groups.items()
    }
    encoded, symbol_map, roundtrip = encode_atomic_groups(restricted)
    page_corpora: dict[str, list[PageSequence]] = {}
    for name, pages in encoded.items():
        page_corpora[name] = [
            PageSequence(
                page_id=page,
                currier=page_metadata[page].get("L"),
                hand=page_metadata[page].get("H"),
                section=page_metadata[page].get("I"),
                groups=pages[page],
                source_line_count=len(keys_by_page[page]),
                excluded_group_count=0,
            )
            for page in eligible_pages
        ]
    audit = {
        "common_locus_count": len(common_keys),
        "common_paragraph_locus_count": len(paragraph_keys),
        "candidate_page_count": len(keys_by_page),
        "eligible_page_count": len(eligible_pages),
        "view_count": len(page_corpora),
        "atomic_symbol_count": len(symbol_map),
        "group_roundtrip_fraction": roundtrip,
        "witness_registry_sha256": corpus.config_sha256,
        "source_manifest_sha256": corpus.source_manifest_sha256,
    }
    return page_corpora, symbol_map, audit


def _rename_pages(pages: list[PageSequence]) -> list[PageSequence]:
    translation = {
        ord(character): ord(character) + 0x1000
        for page in pages
        for group in page.groups
        for character in group
    }
    return [
        PageSequence(
            **{
                **asdict(page),
                "groups": tuple(group.translate(translation) for group in page.groups),
            }
        )
        for page in pages
    ]


def _evaluate_observed(
    pages: list[PageSequence],
    train_ids: tuple[str, ...],
    heldout_ids: tuple[str, ...],
    alpha: float,
) -> dict[str, float]:
    by_id = {page.page_id: page for page in pages}
    return evaluate_predictive_structure(
        [by_id[page] for page in train_ids],
        [by_id[page] for page in heldout_ids],
        alpha=alpha,
    )


def _run_null_tasks(
    config: dict[str, Any],
    corpora: dict[str, list[PageSequence]],
    train_ids: tuple[str, ...],
    heldout_ids: tuple[str, ...],
) -> dict[str, dict[str, dict[str, list[float]]]]:
    families = tuple(config["null_model"]["families"])
    primary = list(config["metrics"]["primary"])
    replicates = int(config["null_model"]["replicates"])
    alpha = float(config["parameters"]["ngram_alpha"])
    mutation_rate = float(config["parameters"]["mutation_rate"])
    base_seed = int(config["split"]["seed"])
    tasks = []
    for view_index, (view, pages) in enumerate(corpora.items()):
        for family_index, family in enumerate(families):
            arguments = (
                pages,
                list(train_ids),
                list(heldout_ids),
                family,
                family_index,
                base_seed + view_index * 100_000_007,
                replicates,
                mutation_rate,
                alpha,
                primary,
            )
            tasks.append((view, family, arguments))
    workers = min(int(config["parameters"]["workers"]), len(tasks))
    completed: dict[str, dict[str, dict[str, list[float]]]] = {view: {} for view in corpora}
    with ProcessPoolExecutor(
        max_workers=workers, mp_context=multiprocessing.get_context("spawn")
    ) as executor:
        futures = {
            executor.submit(_family_samples, *arguments): (view, family)
            for view, family, arguments in tasks
        }
        for future in as_completed(futures):
            view, expected_family = futures[future]
            family, values = future.result()
            if family != expected_family:
                raise ValueError("null worker returned the wrong family")
            completed[view][family] = values
            print(f"E-012 completed {view}/{family}", flush=True)
    return completed


def evaluate_replication(
    config: dict[str, Any],
    observed: dict[str, dict[str, float]],
    samples: dict[str, dict[str, dict[str, list[float]]]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Summarize view-level nulls and apply frozen worst-view conjunction tests."""
    summaries: dict[str, Any] = {}
    for view, families in samples.items():
        summaries[view] = {}
        for family, metrics in families.items():
            summaries[view][family] = {}
            for metric, values in metrics.items():
                mean = sum(values) / len(values)
                variance = sum((value - mean) ** 2 for value in values) / max(1, len(values) - 1)
                summaries[view][family][metric] = {
                    "mean": mean,
                    "standard_deviation": math.sqrt(variance),
                    "observed_minus_null": observed[view][metric] - mean,
                    "empirical_one_sided_p": (
                        1 + sum(value >= observed[view][metric] for value in values)
                    )
                    / (len(values) + 1),
                    "samples": values,
                }
    effects: dict[str, Any] = {}
    conjunction_raw: dict[str, float] = {}
    for effect in config["metrics"]["replicated_effects"]:
        effect_id = str(effect["id"])
        family = str(effect["family"])
        metric = str(effect["metric"])
        by_view = {
            view: {
                "effect": summaries[view][family][metric]["observed_minus_null"],
                "raw_p": summaries[view][family][metric]["empirical_one_sided_p"],
            }
            for view in observed
        }
        conjunction = max(item["raw_p"] for item in by_view.values())
        conjunction_raw[effect_id] = conjunction
        effects[effect_id] = {
            "family": family,
            "metric": metric,
            "views": by_view,
            "all_effects_positive": all(item["effect"] > 0 for item in by_view.values()),
            "conjunction_raw_p": conjunction,
        }
    adjusted = _holm_adjust(conjunction_raw)
    threshold = float(config["metrics"]["maximum_adjusted_p"])
    for effect_id, item in effects.items():
        item["holm_adjusted_conjunction_p"] = adjusted[effect_id]
        item["passed"] = item["all_effects_positive"] and adjusted[effect_id] <= threshold
    copy_diagnostic = {
        view: {
            metric: {
                key: value
                for key, value in summaries[view]["copy_mutate_pseudotext"][metric].items()
                if key != "samples"
            }
            for metric in config["metrics"]["primary"]
        }
        for view in observed
    }
    return summaries, effects, copy_diagnostic


def _preregistration_revision(root: Path, config_path: Path) -> str:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", str(config_path.relative_to(root))],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def run_campaign(config_path: Path) -> dict[str, Any]:
    """Run E-012 from the preregistered config and write immutable artifacts."""
    started = time.monotonic()
    root = repository_root()
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config.get("experiment_id") != "E-012-multi-witness-mechanism-replication":
        raise ValueError("not the frozen E-012 config")
    if len(config["metrics"]["replicated_effects"]) != 8:
        raise ValueError("E-012 frozen effect family changed")
    if sha256_file(root / config["source_lattice"]) != config["source_lattice_sha256"]:
        raise ValueError("Q-011 lattice hash changed")
    for key in ("e001", "e010", "e011"):
        path = root / config["predecessors"][f"{key}_result"]
        if sha256_file(path) != config["predecessors"][f"{key}_result_sha256"]:
            raise ValueError(f"frozen {key.upper()} result hash changed")

    corpora, symbol_map, corpus_audit = build_corpora(config)
    reference = corpora["ZL3b"]
    train, heldout = split_pages(
        reference,
        seed=int(config["split"]["seed"]),
        heldout_fraction=float(config["split"]["heldout_fraction"]),
    )
    train_ids = tuple(page.page_id for page in train)
    heldout_ids = tuple(page.page_id for page in heldout)
    expected_ids = {page.page_id for page in reference}
    page_sets_match = all(
        {page.page_id for page in pages} == expected_ids for pages in corpora.values()
    )
    split_audit = {
        "train_pages": list(train_ids),
        "heldout_pages": list(heldout_ids),
        "overlap_page_count": len(set(train_ids) & set(heldout_ids)),
        "coverage_matches_eligible_pages": set(train_ids) | set(heldout_ids) == expected_ids,
        "all_view_page_sets_match": page_sets_match,
    }
    alpha = float(config["parameters"]["ngram_alpha"])
    observed = {
        view: _evaluate_observed(pages, train_ids, heldout_ids, alpha)
        for view, pages in corpora.items()
    }
    rename_max_difference = 0.0
    for view, pages in corpora.items():
        renamed = _evaluate_observed(_rename_pages(pages), train_ids, heldout_ids, alpha)
        rename_max_difference = max(
            rename_max_difference,
            *(abs(observed[view][metric] - renamed[metric]) for metric in observed[view]),
        )
    samples = _run_null_tasks(config, corpora, train_ids, heldout_ids)
    null_results, replicated_effects, copy_diagnostic = evaluate_replication(
        config, observed, samples
    )
    controls = {
        "atomic_group_roundtrip": corpus_audit["group_roundtrip_fraction"] == 1.0,
        "shared_page_sets": page_sets_match,
        "split_disjoint": split_audit["overlap_page_count"] == 0,
        "split_complete": split_audit["coverage_matches_eligible_pages"],
        "rename_invariance": rename_max_difference
        <= float(config["unitization"]["rename_invariance_tolerance"]),
    }
    passing_effects = [
        effect_id for effect_id, item in replicated_effects.items() if item["passed"]
    ]
    gates = {
        "integrity_controls": all(controls.values()),
        "minimum_replicated_effects": len(passing_effects)
        >= int(config["metrics"]["minimum_passing_effects"]),
    }
    provenance = git_provenance(root)
    if provenance["git_dirty"]:
        raise ValueError("E-012 target calculation requires a clean committed worktree")
    destination = root / config["artifacts"]["root"]
    outputs = {
        "symbol_map": destination / config["artifacts"]["symbol_map"],
        "split": destination / config["artifacts"]["split"],
        "result": destination / config["artifacts"]["result"],
    }
    if any(path.exists() for path in outputs.values()):
        raise FileExistsError(f"immutable E-012 output already exists under {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    outputs["symbol_map"].write_bytes(
        orjson.dumps(
            {symbol: ord(character) for symbol, character in symbol_map.items()},
            option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
        )
        + b"\n"
    )
    outputs["split"].write_bytes(
        orjson.dumps(split_audit, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n"
    )
    result = {
        "schema_version": "1.0",
        "experiment_id": config["experiment_id"],
        "hypothesis_id": config["hypothesis_id"],
        "question_id": config["question_id"],
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "pass" if all(gates.values()) else "fail",
        "target_inference_permitted": False,
        "corpus_audit": corpus_audit,
        "split": split_audit,
        "controls": controls,
        "rename_maximum_absolute_metric_difference": rename_max_difference,
        "observed_metrics": observed,
        "null_results": null_results,
        "replicated_effects": replicated_effects,
        "passing_effects": passing_effects,
        "copy_mutate_diagnostic": copy_diagnostic,
        "gates": gates,
        "runtime_seconds": time.monotonic() - started,
        "provenance": {
            **provenance,
            "preregistration_git_commit": _preregistration_revision(root, config_path),
            "config_sha256": sha256_file(config_path),
            "protocol_sha256": sha256_file(root / config["protocol"]),
            "source_manifest_sha256": sha256_file(root / config["source_manifest"]),
            "source_lattice_sha256": config["source_lattice_sha256"],
            "symbol_map_sha256": sha256_file(outputs["symbol_map"]),
            "split_sha256": sha256_file(outputs["split"]),
            "seed": int(config["split"]["seed"]),
            "workers": int(config["parameters"]["workers"]),
            "device": "CPU",
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "uv_lock_sha256": sha256_file(root / "uv.lock"),
        },
        "interpretation": (
            "Multi-witness replication of fixed structure effects only; no meaning, language, "
            "cipher, constructed-language, or hoax inference is permitted."
        ),
    }
    outputs["result"].write_bytes(
        orjson.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n"
    )
    return result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/E-012-multi-witness-mechanism-replication.yaml"),
    )
    args = parser.parse_args()
    result = run_campaign(args.config)
    print(
        orjson.dumps(
            {
                "status": result["status"],
                "corpus_audit": result["corpus_audit"],
                "controls": result["controls"],
                "passing_effects": result["passing_effects"],
                "gates": result["gates"],
                "runtime_seconds": result["runtime_seconds"],
            },
            option=orjson.OPT_INDENT_2,
        ).decode()
    )


if __name__ == "__main__":
    main()
