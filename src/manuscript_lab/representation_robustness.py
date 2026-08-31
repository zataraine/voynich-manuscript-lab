"""Preregistered E-010 transcription-representation robustness campaign."""

from __future__ import annotations

import math
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import combinations, pairwise
from pathlib import Path
from typing import Any, Literal

import numpy as np
import orjson
import yaml
from scipy.stats import rankdata

from manuscript_lab.ivtff import LocusRecord, SurfaceUnit, parse_surface
from manuscript_lab.ledger import git_provenance
from manuscript_lab.provenance import repository_root, sha256_file
from manuscript_lab.witness_alignment import WitnessCorpus, load_witness_corpus

AlternativePolicy = Literal["first", "last", "opaque"]
SpacePolicy = Literal["split", "join"]

IGNORED_UNITS = frozenset({"paragraph_start", "paragraph_end", "free_comment", "text_tag"})
DRAWING_UNITS = frozenset({"drawing_space", "misaligned_drawing_space"})
FEATURES = (
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
)


@dataclass(frozen=True)
class PageUnits:
    """Groups nested under physical loci, retaining hard sequence boundaries."""

    loci: tuple[tuple[tuple[str, ...], ...], ...]

    @property
    def groups(self) -> tuple[tuple[str, ...], ...]:
        return tuple(group for locus in self.loci for group in locus)

    @property
    def symbol_count(self) -> int:
        return sum(len(group) for group in self.groups)


def _sta_codes(raw: str, context: str) -> tuple[str, ...]:
    if len(raw) % 2 or any(
        not (raw[index].isupper() and raw[index + 1].isalnum()) for index in range(0, len(raw), 2)
    ):
        raise ValueError(f"invalid STA1 glyph run {raw!r} in {context}")
    return tuple(raw[index : index + 2] for index in range(0, len(raw), 2))


def _append_units(
    units: tuple[SurfaceUnit, ...],
    groups: list[tuple[str, ...]],
    current: list[str],
    *,
    alternative_policy: AlternativePolicy,
    uncertain_space_policy: SpacePolicy,
    context: str,
) -> None:
    def finish_group() -> None:
        if current:
            groups.append(tuple(current))
            current.clear()

    for unit in units:
        if unit.kind in IGNORED_UNITS:
            continue
        if unit.kind == "glyph_run":
            current.extend(_sta_codes(unit.raw, context))
        elif unit.kind == "certain_space":
            finish_group()
        elif unit.kind == "uncertain_space":
            if uncertain_space_policy == "split":
                finish_group()
        elif unit.kind in DRAWING_UNITS:
            finish_group()
        elif unit.kind == "alternative_reading":
            if alternative_policy == "opaque":
                current.append("<ALT>")
            else:
                branch = unit.alternatives[0 if alternative_policy == "first" else -1]
                _append_units(
                    parse_surface(branch),
                    groups,
                    current,
                    alternative_policy=alternative_policy,
                    uncertain_space_policy=uncertain_space_policy,
                    context=context,
                )
        elif unit.kind == "unreadable_character":
            current.append("<UNK1>")
        elif unit.kind == "unreadable_unknown_count":
            current.append("<UNKN>")
        elif unit.kind == "ligature":
            current.append(f"<LIG:{unit.raw}>")
        elif unit.kind == "high_ascii":
            current.append(f"<HIGH:{unit.raw}>")
        else:
            raise ValueError(f"unsupported STA1 unit {unit.kind!r} in {context}")


def unitize_locus(
    locus: LocusRecord,
    *,
    alternative_policy: AlternativePolicy = "first",
    uncertain_space_policy: SpacePolicy = "split",
) -> tuple[tuple[str, ...], ...]:
    """Resolve one declared uncertainty view without losing unknown symbols."""
    groups: list[tuple[str, ...]] = []
    current: list[str] = []
    _append_units(
        locus.units,
        groups,
        current,
        alternative_policy=alternative_policy,
        uncertain_space_policy=uncertain_space_policy,
        context=locus.record_id,
    )
    if current:
        groups.append(tuple(current))
    return tuple(groups)


def page_features(page: PageUnits) -> dict[str, float]:
    """Calculate the frozen ten-feature panel on one page view."""
    groups = page.groups
    symbols = [symbol for group in groups for symbol in group]
    alphabet = set(symbols)
    counts = Counter(symbols)
    symbol_total = len(symbols)
    entropy = -sum(
        (count / symbol_total) * math.log2(count / symbol_total) for count in counts.values()
    )
    log_alphabet = math.log2(len(alphabet)) if len(alphabet) > 1 else math.nan

    bigrams = [pair for locus in page.loci for group in locus for pair in pairwise(group)]
    contexts: dict[str, Counter[str]] = {}
    for left, right in bigrams:
        contexts.setdefault(left, Counter())[right] += 1
    conditional = 0.0
    if bigrams:
        for next_counts in contexts.values():
            context_total = sum(next_counts.values())
            context_entropy = -sum(
                (count / context_total) * math.log2(count / context_total)
                for count in next_counts.values()
            )
            conditional += (context_total / len(bigrams)) * context_entropy
    else:
        conditional = math.nan

    lengths = np.asarray([len(group) for group in groups], dtype=np.float64)
    group_counts = Counter(groups)
    adjacent_groups = [pair for locus in page.loci for pair in pairwise(locus)]
    recurrence_hits = 0
    recurrence_total = 0
    for locus in page.loci:
        for index, group in enumerate(locus):
            if index == 0:
                continue
            recurrence_total += 1
            if group in locus[max(0, index - 20) : index]:
                recurrence_hits += 1

    return {
        "symbol_entropy_normalized": float(entropy / log_alphabet),
        "symbol_conditional_entropy_normalized": float(conditional / log_alphabet),
        "symbol_repeat_rate": float(
            sum(left == right for left, right in bigrams) / len(bigrams) if bigrams else math.nan
        ),
        "symbol_bigram_type_ratio": float(
            len(set(bigrams)) / len(bigrams) if bigrams else math.nan
        ),
        "group_length_mean": float(np.mean(lengths)),
        "group_length_cv": float(np.std(lengths) / np.mean(lengths)),
        "group_type_token_ratio": float(len(group_counts) / len(groups)),
        "group_hapax_ratio": float(
            sum(count == 1 for count in group_counts.values()) / len(group_counts)
        ),
        "adjacent_group_repeat_rate": float(
            sum(left == right for left, right in adjacent_groups) / len(adjacent_groups)
            if adjacent_groups
            else math.nan
        ),
        "window20_group_recurrence": float(
            recurrence_hits / recurrence_total if recurrence_total else math.nan
        ),
    }


def _document_index(
    loci: tuple[LocusRecord, ...],
) -> dict[tuple[str, int], tuple[LocusRecord, ...]]:
    mutable: dict[tuple[str, int], list[LocusRecord]] = {}
    for locus in loci:
        mutable.setdefault((locus.page, locus.number), []).append(locus)
    return {key: tuple(values) for key, values in mutable.items()}


def _build_page_view(
    index: dict[tuple[str, int], tuple[LocusRecord, ...]],
    keys_by_page: dict[str, tuple[tuple[str, int], ...]],
    *,
    alternative_policy: AlternativePolicy,
    uncertain_space_policy: SpacePolicy,
) -> dict[str, PageUnits]:
    pages: dict[str, PageUnits] = {}
    for page, keys in keys_by_page.items():
        loci = tuple(
            unitize_locus(
                locus,
                alternative_policy=alternative_policy,
                uncertain_space_policy=uncertain_space_policy,
            )
            for key in keys
            for locus in index[key]
        )
        pages[page] = PageUnits(loci=loci)
    return pages


def build_views(
    corpus: WitnessCorpus, config: dict[str, Any]
) -> tuple[dict[str, dict[str, PageUnits]], tuple[str, ...], int]:
    """Create all frozen views and the common-locus page population."""
    primary_specs = config["population"]["primary_views"]
    primary_ids = tuple(str(item["witness"]) for item in primary_specs)
    indexes = {
        witness_id: _document_index(corpus.comparison_documents[witness_id].loci)
        for witness_id in primary_ids
    }
    common_keys = set.intersection(*(set(index) for index in indexes.values()))
    page_order = {
        page.page: i for i, page in enumerate(corpus.documents[corpus.order_witness].pages)
    }
    keys_by_page_mutable: dict[str, list[tuple[str, int]]] = {}
    for key in common_keys:
        keys_by_page_mutable.setdefault(key[0], []).append(key)
    keys_by_page = {
        page: tuple(sorted(keys, key=lambda item: item[1]))
        for page, keys in sorted(
            keys_by_page_mutable.items(), key=lambda item: (page_order.get(item[0], 10**9), item[0])
        )
    }

    views: dict[str, dict[str, PageUnits]] = {}
    for item in primary_specs:
        witness_id = str(item["witness"])
        variant = str(item["variant"])
        views[variant] = _build_page_view(
            indexes[witness_id],
            keys_by_page,
            alternative_policy="first",
            uncertain_space_policy="split",
        )

    for witness_id in ("CD2a", "GC2a"):
        alternates = corpus.comparison_alternates[witness_id]
        if len(alternates) != 1:
            raise ValueError(f"expected exactly one conversion alternate for {witness_id}")
        name = f"{witness_id}_1"
        views[name] = _build_page_view(
            _document_index(alternates[0].loci),
            keys_by_page,
            alternative_policy="first",
            uncertain_space_policy="split",
        )

    uncertainty_names: list[str] = []
    zl_index = indexes[str(config["views"]["uncertainty_witness"])]
    for alternative in config["views"]["alternative_policies"]:
        for space in config["views"]["uncertain_space_policies"]:
            name = f"ZL3b-alt-{alternative}-space-{space}"
            uncertainty_names.append(name)
            views[name] = _build_page_view(
                zl_index,
                keys_by_page,
                alternative_policy=alternative,
                uncertain_space_policy=space,
            )
    return views, tuple(uncertainty_names), len(common_keys)


def _spearman(left: np.ndarray, right: np.ndarray) -> float:
    if left.size < 2 or np.all(left == left[0]) or np.all(right == right[0]):
        return math.nan
    return float(np.corrcoef(rankdata(left), rankdata(right))[0, 1])


def _pair_stats(
    values: dict[str, np.ndarray], names: tuple[str, ...], scale: float
) -> dict[str, dict[str, float]]:
    return {
        f"{left}::{right}": {
            "spearman_rho": _spearman(values[left], values[right]),
            "median_normalized_absolute_difference": float(
                np.median(np.abs(values[left] - values[right])) / scale
            ),
        }
        for left, right in combinations(names, 2)
    }


def _holm(raw: dict[str, float]) -> dict[str, float]:
    ordered = sorted(raw, key=raw.get)
    adjusted: dict[str, float] = {}
    running = 0.0
    total = len(ordered)
    for rank, name in enumerate(ordered):
        running = max(running, raw[name] * (total - rank))
        adjusted[name] = min(1.0, running)
    return adjusted


def _preregistration_revision(root: Path, config_path: Path) -> str:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", str(config_path.relative_to(root))],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def analyze(
    config: dict[str, Any],
    views: dict[str, dict[str, PageUnits]],
    uncertainty_names: tuple[str, ...],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    primary_names = tuple(str(item["variant"]) for item in config["population"]["primary_views"])
    eligibility_names = primary_names + uncertainty_names
    minimum_groups = int(config["eligibility"]["minimum_groups_per_page_per_view"])
    minimum_symbols = int(config["eligibility"]["minimum_symbols_per_page_per_view"])
    candidate_pages = tuple(views[primary_names[0]])
    eligible_pages = tuple(
        page
        for page in candidate_pages
        if all(
            len(views[name][page].groups) >= minimum_groups
            and views[name][page].symbol_count >= minimum_symbols
            for name in eligibility_names
        )
    )

    rows: list[dict[str, Any]] = []
    by_view: dict[str, dict[str, dict[str, float]]] = {}
    for name, pages in views.items():
        by_view[name] = {}
        for page in eligible_pages:
            features = page_features(pages[page])
            by_view[name][page] = features
            rows.append(
                {
                    "page": page,
                    "view": name,
                    "group_count": len(pages[page].groups),
                    "symbol_count": pages[page].symbol_count,
                    "features": features,
                }
            )

    values = {
        feature: {
            name: np.asarray([by_view[name][page][feature] for page in eligible_pages])
            for name in views
        }
        for feature in FEATURES
    }
    scales = {
        feature: float(
            np.subtract(
                *np.percentile(
                    np.median(np.stack([values[feature][name] for name in primary_names]), axis=0),
                    [75, 25],
                )
            )
        )
        for feature in FEATURES
    }

    bootstrap_config = config["bootstrap"]
    bootstrap_rng = np.random.default_rng(int(bootstrap_config["seed"]))
    bootstrap_indices = bootstrap_rng.integers(
        0,
        len(eligible_pages),
        size=(int(bootstrap_config["page_replicates"]), len(eligible_pages)),
    )
    primary_pairs = tuple(combinations(primary_names, 2))
    bootstrap: dict[str, dict[str, Any]] = {}
    for feature in FEATURES:
        pair_samples: dict[str, list[float]] = {
            f"{left}::{right}": [] for left, right in primary_pairs
        }
        worst_samples: list[float] = []
        for indices in bootstrap_indices:
            replicate = []
            for left, right in primary_pairs:
                rho = _spearman(values[feature][left][indices], values[feature][right][indices])
                pair_samples[f"{left}::{right}"].append(rho)
                replicate.append(rho)
            worst_samples.append(float(np.nanmin(replicate)))
        bootstrap[feature] = {
            "pair_95_ci": {
                pair: [
                    float(np.nanpercentile(samples, 2.5)),
                    float(np.nanpercentile(samples, 97.5)),
                ]
                for pair, samples in pair_samples.items()
            },
            "worst_pair_95_ci": [
                float(np.nanpercentile(worst_samples, 2.5)),
                float(np.nanpercentile(worst_samples, 97.5)),
            ],
        }

    null_config = config["null_model"]
    null_rng = np.random.default_rng(int(null_config["seed"]))
    reference = str(null_config["reference_witness"])
    observed: dict[str, float] = {}
    null_summaries: dict[str, dict[str, float]] = {}
    raw_p: dict[str, float] = {}
    for feature in FEATURES:
        observed_pairs = [
            _spearman(values[feature][left], values[feature][right])
            for left, right in primary_pairs
        ]
        observed[feature] = float(np.nanmedian(observed_pairs))
        null_values = []
        for _ in range(int(null_config["replicates"])):
            permuted = {
                name: (
                    values[feature][name]
                    if name == reference
                    else values[feature][name][null_rng.permutation(len(eligible_pages))]
                )
                for name in primary_names
            }
            null_values.append(
                float(
                    np.nanmedian(
                        [
                            _spearman(permuted[left], permuted[right])
                            for left, right in primary_pairs
                        ]
                    )
                )
            )
        raw_p[feature] = float(
            (1 + sum(value >= observed[feature] for value in null_values))
            / (int(null_config["replicates"]) + 1)
        )
        null_summaries[feature] = {
            "mean": float(np.mean(null_values)),
            "p95": float(np.percentile(null_values, 95)),
            "maximum": float(np.max(null_values)),
        }
    adjusted_p = _holm(raw_p)

    gates_config = config["gates"]
    conversion_pairs = tuple(tuple(pair) for pair in config["views"]["conversion_pairs"])
    feature_results: dict[str, Any] = {}
    for feature in FEATURES:
        scale = scales[feature]
        finite_scale = math.isfinite(scale) and scale > 0
        if finite_scale:
            primary_stats = _pair_stats(values[feature], primary_names, scale)
            conversion_stats = {
                f"{left}::{right}": {
                    "spearman_rho": _spearman(values[feature][left], values[feature][right]),
                    "median_normalized_absolute_difference": float(
                        np.median(np.abs(values[feature][left] - values[feature][right])) / scale
                    ),
                }
                for left, right in conversion_pairs
            }
            uncertainty_stats = _pair_stats(values[feature], uncertainty_names, scale)
        else:
            primary_stats = conversion_stats = uncertainty_stats = {}
        all_values = np.concatenate([values[feature][name] for name in views])
        nonfinite_fraction = float(np.mean(~np.isfinite(all_values)))
        worst_primary = min(
            (item["spearman_rho"] for item in primary_stats.values()), default=math.nan
        )
        maximum_primary_difference = max(
            (item["median_normalized_absolute_difference"] for item in primary_stats.values()),
            default=math.inf,
        )
        worst_conversion = min(
            (item["spearman_rho"] for item in conversion_stats.values()), default=math.nan
        )
        maximum_conversion_difference = max(
            (item["median_normalized_absolute_difference"] for item in conversion_stats.values()),
            default=math.inf,
        )
        worst_uncertainty = min(
            (item["spearman_rho"] for item in uncertainty_stats.values()), default=math.nan
        )
        maximum_uncertainty_difference = max(
            (item["median_normalized_absolute_difference"] for item in uncertainty_stats.values()),
            default=math.inf,
        )
        gate_values = {
            "eligible_pages": len(eligible_pages)
            >= int(config["eligibility"]["minimum_eligible_pages"]),
            "finite_values": nonfinite_fraction
            <= float(config["eligibility"]["maximum_nonfinite_fraction"]),
            "finite_nonzero_scale": finite_scale,
            "primary_rank": worst_primary >= float(gates_config["minimum_worst_primary_spearman"]),
            "primary_bootstrap": bootstrap[feature]["worst_pair_95_ci"][0]
            >= float(gates_config["minimum_worst_primary_bootstrap_lower"]),
            "primary_difference": maximum_primary_difference
            <= float(gates_config["maximum_primary_median_normalized_difference"]),
            "conversion_rank": worst_conversion
            >= float(gates_config["minimum_worst_conversion_spearman"]),
            "conversion_difference": maximum_conversion_difference
            <= float(gates_config["maximum_conversion_median_normalized_difference"]),
            "uncertainty_rank": worst_uncertainty
            >= float(gates_config["minimum_worst_uncertainty_spearman"]),
            "uncertainty_difference": maximum_uncertainty_difference
            <= float(gates_config["maximum_uncertainty_median_normalized_difference"]),
            "aligned_page_null": adjusted_p[feature]
            <= float(gates_config["maximum_holm_adjusted_permutation_p"]),
        }
        feature_results[feature] = {
            "stable": all(gate_values.values()),
            "scale_iqr": scale,
            "nonfinite_fraction": nonfinite_fraction,
            "worst_primary_spearman": worst_primary,
            "maximum_primary_median_normalized_difference": maximum_primary_difference,
            "worst_conversion_spearman": worst_conversion,
            "maximum_conversion_median_normalized_difference": maximum_conversion_difference,
            "worst_uncertainty_spearman": worst_uncertainty,
            "maximum_uncertainty_median_normalized_difference": maximum_uncertainty_difference,
            "primary_pairs": primary_stats,
            "conversion_pairs": conversion_stats,
            "uncertainty_pairs": uncertainty_stats,
            "bootstrap": bootstrap[feature],
            "page_label_null": {
                "observed_median_primary_pair_spearman": observed[feature],
                "raw_p": raw_p[feature],
                "holm_adjusted_p": adjusted_p[feature],
                **null_summaries[feature],
            },
            "gates": gate_values,
        }

    stable = [feature for feature in FEATURES if feature_results[feature]["stable"]]
    order_sensitive = set(config["features"]["order_sensitive"])
    stable_order = [feature for feature in stable if feature in order_sensitive]
    hypothesis_gates = {
        "minimum_stable_features": len(stable)
        >= int(gates_config["hypothesis_minimum_stable_features"]),
        "minimum_stable_order_sensitive_features": len(stable_order)
        >= int(gates_config["hypothesis_minimum_stable_order_sensitive_features"]),
    }
    analysis = {
        "candidate_pages": len(candidate_pages),
        "eligible_pages": list(eligible_pages),
        "eligible_page_count": len(eligible_pages),
        "view_count": len(views),
        "feature_results": feature_results,
        "stable_features": stable,
        "stable_order_sensitive_features": stable_order,
        "hypothesis_gates": hypothesis_gates,
        "status": "pass" if all(hypothesis_gates.values()) else "fail",
    }
    return rows, analysis


def run_campaign(config_path: Path, output_root: Path | None = None) -> dict[str, Any]:
    """Run E-010 and write immutable page features and result records."""
    started = time.monotonic()
    root = repository_root()
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config.get("experiment_id") != "E-010-representation-robustness":
        raise ValueError("not the frozen E-010 config")
    if tuple(config["features"]["all"]) != FEATURES:
        raise ValueError("E-010 frozen feature panel changed")
    corpus = load_witness_corpus(root / config["source_registry"])
    lattice_path = root / config["source_lattice"]
    views, uncertainty_names, common_locus_count = build_views(corpus, config)
    rows, analysis = analyze(config, views, uncertainty_names)
    destination = output_root or root / config["artifacts"]["root"]
    page_output = destination / config["artifacts"]["page_features"]
    result_output = destination / config["artifacts"]["result"]
    if page_output.exists() or result_output.exists():
        raise FileExistsError(f"immutable E-010 output already exists under {destination}")
    provenance = git_provenance(root)
    if provenance["git_dirty"]:
        raise ValueError("E-010 target calculation requires a clean committed worktree")
    result = {
        "schema_version": "1.0",
        "experiment_id": config["experiment_id"],
        "hypothesis_id": config["hypothesis_id"],
        "question_id": config["question_id"],
        "generated_at": datetime.now(UTC).isoformat(),
        "status": analysis["status"],
        "target_scored": True,
        "target_inference_permitted": False,
        "common_locus_count": common_locus_count,
        **analysis,
        "provenance": {
            **provenance,
            "preregistration_git_commit": _preregistration_revision(root, config_path),
            "config": str(config_path.relative_to(root)),
            "config_sha256": sha256_file(config_path),
            "protocol_sha256": sha256_file(root / config["protocol"]),
            "witness_registry_sha256": corpus.config_sha256,
            "source_manifest_sha256": corpus.source_manifest_sha256,
            "source_lattice": config["source_lattice"],
            "source_lattice_sha256": sha256_file(lattice_path),
            "page_features": str(page_output.relative_to(root)),
            "python": sys.version.split()[0],
            "device": "CPU",
        },
        "runtime_seconds": time.monotonic() - started,
        "interpretation": (
            "Representation-stability audit only. This result is not a language, cipher, "
            "meaning, constructed-language, or hoax probability."
        ),
    }
    destination.mkdir(parents=True, exist_ok=True)
    with page_output.open("wb") as handle:
        for row in rows:
            handle.write(orjson.dumps(row, option=orjson.OPT_SORT_KEYS) + b"\n")
    result["provenance"]["page_features_sha256"] = sha256_file(page_output)
    result_output.write_bytes(
        orjson.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n"
    )
    return result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/E-010-representation-robustness.yaml"),
    )
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    result = run_campaign(args.config, args.output_root)
    print(
        orjson.dumps(
            {
                "status": result["status"],
                "eligible_page_count": result["eligible_page_count"],
                "stable_features": result["stable_features"],
                "stable_order_sensitive_features": result["stable_order_sensitive_features"],
                "hypothesis_gates": result["hypothesis_gates"],
                "runtime_seconds": result["runtime_seconds"],
            },
            option=orjson.OPT_INDENT_2,
        ).decode()
    )


if __name__ == "__main__":
    main()
