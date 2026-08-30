"""Held-out sequence tests against explicit nonsemantic mechanism families.

This module cannot determine whether a text has meaning.  It measures whether
simple null or pseudo-text mechanisms reproduce preregistered predictive
structure, while keeping physical pages on one side of every split.
"""

from __future__ import annotations

import argparse
import math
import multiprocessing
import platform
import random
import re
import sys
from collections import Counter, defaultdict, deque
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import orjson
import yaml
from jsonschema import Draft202012Validator
from rapidfuzz.distance import Levenshtein

from manuscript_lab.ivtff import iter_page_headers, iter_text_lines
from manuscript_lab.ledger import git_provenance
from manuscript_lab.provenance import repository_root, sha256_file

INLINE_COMMENT = re.compile(r"<!.*?>")
CONTROL_MARK = re.compile(r"<[%$]>")
INTRUSION_MARK = re.compile(r"<->")
GROUP_BOUNDARY = re.compile(r"[.,]+")
STABLE_GROUP = re.compile(r"^[A-Za-z']+$", re.ASCII)


@dataclass(frozen=True)
class PageSequence:
    """Analysis groups for one physical page plus auditable source metadata."""

    page_id: str
    currier: str | None
    hand: str | None
    section: str | None
    groups: tuple[str, ...]
    source_line_count: int
    excluded_group_count: int


@dataclass(frozen=True)
class CorpusDistributions:
    """Precomputed weighted populations reused across null replicates."""

    group_values: tuple[str, ...]
    group_cumulative_weights: tuple[int, ...]
    symbol_values: tuple[str, ...]
    symbol_cumulative_weights: tuple[int, ...]


def _stable_groups(text: str) -> tuple[list[str], int]:
    """Extract conservative EVA groups, excluding every uncertainty-bearing group."""
    visible = INLINE_COMMENT.sub("", text)
    visible = CONTROL_MARK.sub("", visible)
    visible = INTRUSION_MARK.sub("", visible)
    groups: list[str] = []
    excluded = 0
    for value in GROUP_BOUNDARY.split(visible):
        value = value.strip()
        if not value:
            continue
        if STABLE_GROUP.fullmatch(value):
            groups.append(value)
        else:
            excluded += 1
    return groups, excluded


def load_ivtff_pages(
    path: Path,
    *,
    currier: set[str] | None = None,
    paragraph_only: bool = True,
) -> list[PageSequence]:
    """Build a conservative page corpus while retaining page-level provenance."""
    metadata = {header.page: header.fields for header in iter_page_headers(path)}
    groups: dict[str, list[str]] = defaultdict(list)
    line_counts: Counter[str] = Counter()
    excluded_counts: Counter[str] = Counter()
    for line in iter_text_lines(path):
        if paragraph_only and "P" not in line.locator:
            continue
        stable, excluded = _stable_groups(line.text)
        groups[line.page].extend(stable)
        line_counts[line.page] += 1
        excluded_counts[line.page] += excluded

    pages: list[PageSequence] = []
    for page_id in metadata:
        fields = metadata[page_id]
        language = fields.get("L")
        if currier is not None and language not in currier:
            continue
        if not groups[page_id]:
            continue
        pages.append(
            PageSequence(
                page_id=page_id,
                currier=language,
                hand=fields.get("H"),
                section=fields.get("I"),
                groups=tuple(groups[page_id]),
                source_line_count=line_counts[page_id],
                excluded_group_count=excluded_counts[page_id],
            )
        )
    return pages


def split_pages(
    pages: list[PageSequence], *, seed: int, heldout_fraction: float
) -> tuple[list[PageSequence], list[PageSequence]]:
    """Stratify by available Currier/hand/section labels without splitting pages."""
    if not 0 < heldout_fraction < 1:
        raise ValueError("heldout_fraction must be between zero and one")
    strata: dict[tuple[str | None, str | None, str | None], list[PageSequence]] = defaultdict(list)
    for page in pages:
        strata[(page.currier, page.hand, page.section)].append(page)
    train: list[PageSequence] = []
    heldout: list[PageSequence] = []
    for key in sorted(strata, key=lambda value: tuple(item or "" for item in value)):
        members = sorted(strata[key], key=lambda page: page.page_id)
        random.Random(f"{seed}:{key}").shuffle(members)
        if len(members) == 1:
            train.extend(members)
            continue
        count = min(len(members) - 1, max(1, round(len(members) * heldout_fraction)))
        heldout.extend(members[:count])
        train.extend(members[count:])
    if not train or not heldout:
        raise ValueError("Page split produced an empty partition")
    return sorted(train, key=lambda page: page.page_id), sorted(
        heldout, key=lambda page: page.page_id
    )


def ngram_cross_entropy(
    train_sequences: list[tuple[str, ...]],
    test_sequences: list[tuple[str, ...]],
    *,
    order: int,
    alpha: float,
) -> float:
    """Additive-smoothed held-out cross entropy in bits per predicted unit."""
    if order < 0 or alpha <= 0:
        raise ValueError("order must be nonnegative and alpha positive")
    vocabulary = {unit for sequence in train_sequences for unit in sequence}
    vocabulary.update({"<UNK>", "<EOS>"})
    context_counts: Counter[tuple[str, ...]] = Counter()
    transition_counts: Counter[tuple[tuple[str, ...], str]] = Counter()

    def observations(sequence: tuple[str, ...]) -> list[tuple[tuple[str, ...], str]]:
        mapped = tuple(unit if unit in vocabulary else "<UNK>" for unit in sequence)
        padded = ("<BOS>",) * order + mapped + ("<EOS>",)
        return [
            (padded[index - order : index], padded[index]) for index in range(order, len(padded))
        ]

    for sequence in train_sequences:
        for context, unit in observations(sequence):
            context_counts[context] += 1
            transition_counts[(context, unit)] += 1
    loss = 0.0
    count = 0
    width = len(vocabulary)
    for sequence in test_sequences:
        for context, unit in observations(sequence):
            probability = (transition_counts[(context, unit)] + alpha) / (
                context_counts[context] + alpha * width
            )
            loss -= math.log2(probability)
            count += 1
    if count == 0:
        raise ValueError("No held-out units were available")
    return loss / count


def local_copy_rate(pages: list[PageSequence], *, window: int = 20) -> float:
    """Rate of groups within edit distance one of a recent group on the same page."""
    matches = 0
    comparisons = 0
    for page in pages:
        recent: deque[str] = deque()
        buckets: dict[str, Counter[str]] = defaultdict(Counter)
        for group in page.groups:
            if not recent:
                for signature in _deletion_signatures(group):
                    buckets[signature][group] += 1
                recent.append(group)
                continue
            comparisons += 1
            candidates = {
                candidate
                for signature in _deletion_signatures(group)
                for candidate in buckets.get(signature, {})
            }
            if any(
                Levenshtein.distance(group, candidate, score_cutoff=1) <= 1
                for candidate in candidates
            ):
                matches += 1
            for signature in _deletion_signatures(group):
                buckets[signature][group] += 1
            recent.append(group)
            if len(recent) > window:
                expired = recent.popleft()
                for signature in _deletion_signatures(expired):
                    buckets[signature][expired] -= 1
                    if not buckets[signature][expired]:
                        del buckets[signature][expired]
                    if not buckets[signature]:
                        del buckets[signature]
    return matches / comparisons if comparisons else 0.0


def _deletion_signatures(value: str) -> frozenset[str]:
    return frozenset({value, *(value[:index] + value[index + 1 :] for index in range(len(value)))})


def evaluate_predictive_structure(
    train: list[PageSequence], heldout: list[PageSequence], *, alpha: float
) -> dict[str, float]:
    """Compute the preregistered held-out predictive and copy-neighborhood panel."""
    train_char = [tuple(group) for page in train for group in page.groups]
    test_char = [tuple(group) for page in heldout for group in page.groups]
    train_group = [page.groups for page in train]
    test_group = [page.groups for page in heldout]
    char_0 = ngram_cross_entropy(train_char, test_char, order=0, alpha=alpha)
    char_2 = ngram_cross_entropy(train_char, test_char, order=2, alpha=alpha)
    group_0 = ngram_cross_entropy(train_group, test_group, order=0, alpha=alpha)
    group_1 = ngram_cross_entropy(train_group, test_group, order=1, alpha=alpha)
    return {
        "heldout_char_unigram_bits_per_symbol": char_0,
        "heldout_char_trigram_bits_per_symbol": char_2,
        "heldout_char_trigram_gain_bits": char_0 - char_2,
        "heldout_group_unigram_bits_per_group": group_0,
        "heldout_group_bigram_bits_per_group": group_1,
        "heldout_group_bigram_gain_bits": group_0 - group_1,
        "heldout_local_copy_rate": local_copy_rate(heldout),
    }


def corpus_distributions(pages: list[PageSequence]) -> CorpusDistributions:
    """Build cumulative weights once for repeated seeded generation."""
    group_frequency = Counter(group for page in pages for group in page.groups)
    symbol_frequency = Counter(
        symbol for page in pages for group in page.groups for symbol in group
    )

    def population(counter: Counter[str]) -> tuple[tuple[str, ...], tuple[int, ...]]:
        values = tuple(sorted(counter))
        running = 0
        cumulative: list[int] = []
        for value in values:
            running += counter[value]
            cumulative.append(running)
        return values, tuple(cumulative)

    group_values, group_cumulative = population(group_frequency)
    symbol_values, symbol_cumulative = population(symbol_frequency)
    return CorpusDistributions(
        group_values,
        group_cumulative,
        symbol_values,
        symbol_cumulative,
    )


def generate_variant(
    pages: list[PageSequence],
    family: str,
    *,
    seed: int,
    mutation_rate: float = 0.18,
    distributions: CorpusDistributions | None = None,
) -> list[PageSequence]:
    """Generate a seeded structure-preserving comparator corpus."""
    rng = random.Random(seed)
    distribution = distributions or corpus_distributions(pages)
    vocabulary = distribution.symbol_values
    generated: list[PageSequence] = []
    for page in pages:
        if family == "within_page_group_shuffle":
            values = list(page.groups)
            rng.shuffle(values)
        elif family == "within_group_symbol_shuffle":
            values = []
            for group in page.groups:
                symbols = list(group)
                rng.shuffle(symbols)
                values.append("".join(symbols))
        elif family == "global_group_resample":
            values = rng.choices(
                distribution.group_values,
                cum_weights=distribution.group_cumulative_weights,
                k=len(page.groups),
            )
        elif family == "iid_symbol_length_matched":
            values = [
                "".join(
                    rng.choices(
                        vocabulary,
                        cum_weights=distribution.symbol_cumulative_weights,
                        k=len(group),
                    )
                )
                for group in page.groups
            ]
        elif family == "copy_mutate_pseudotext":
            values = []
            for template in page.groups:
                base = (
                    rng.choice(values[-20:])
                    if values and rng.random() < 0.75
                    else rng.choices(
                        distribution.group_values,
                        cum_weights=distribution.group_cumulative_weights,
                        k=1,
                    )[0]
                )
                symbols = list(base)
                if symbols and rng.random() < mutation_rate:
                    symbols[rng.randrange(len(symbols))] = rng.choice(vocabulary)
                if rng.random() < mutation_rate / 3 and len(symbols) > 1:
                    del symbols[rng.randrange(len(symbols))]
                if rng.random() < mutation_rate / 3:
                    symbols.insert(rng.randrange(len(symbols) + 1), rng.choice(vocabulary))
                value = "".join(symbols) or template
                values.append(value)
        else:
            raise ValueError(f"Unknown mechanism family: {family}")
        generated.append(replace(page, groups=tuple(values)))
    return generated


def _holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values, key=p_values.get)  # type: ignore[arg-type]
    adjusted: dict[str, float] = {}
    running = 0.0
    total = len(ordered)
    for index, name in enumerate(ordered):
        running = max(running, min(1.0, p_values[name] * (total - index)))
        adjusted[name] = running
    return adjusted


def _family_samples(
    pages: list[PageSequence],
    train_ids: list[str],
    heldout_ids: list[str],
    family: str,
    family_index: int,
    seed: int,
    replicates: int,
    mutation_rate: float,
    alpha: float,
    primary: list[str],
) -> tuple[str, dict[str, list[float]]]:
    """Evaluate one mechanism family; kept top-level for process isolation."""
    values = {metric: [] for metric in primary}
    distributions = corpus_distributions(pages)
    for replicate in range(replicates):
        variant = generate_variant(
            pages,
            family,
            seed=seed + (family_index + 1) * 1_000_003 + replicate,
            mutation_rate=mutation_rate,
            distributions=distributions,
        )
        variant_by_id = {page.page_id: page for page in variant}
        metrics = evaluate_predictive_structure(
            [variant_by_id[page_id] for page_id in train_ids],
            [variant_by_id[page_id] for page_id in heldout_ids],
            alpha=alpha,
        )
        for metric in primary:
            values[metric].append(metrics[metric])
    return family, values


def run_study(config_path: Path) -> dict[str, Any]:
    """Run the configured target/null panel and return a provenance-complete record."""
    root = repository_root()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("Experiment config must contain a mapping")
    parameters = config["parameters"]
    source_path = root / parameters["input_path"]
    seed = int(config["seed"])
    pages = load_ivtff_pages(
        source_path,
        currier=set(parameters.get("currier_values", ["A", "B"])),
        paragraph_only=bool(parameters.get("paragraph_only", True)),
    )
    train, heldout = split_pages(
        pages, seed=seed, heldout_fraction=float(parameters["heldout_fraction"])
    )
    alpha = float(parameters["ngram_alpha"])
    observed = evaluate_predictive_structure(train, heldout, alpha=alpha)
    primary = list(config["metrics"]["primary"])
    replicates = int(config["null_model"]["replicates"])
    families = list(config["null_model"]["families"])
    workers = min(int(parameters.get("workers", 1)), len(families))
    if replicates < 1 or workers < 1:
        raise ValueError("null replicates and workers must be positive")
    family_arguments = [
        (
            pages,
            [page.page_id for page in train],
            [page.page_id for page in heldout],
            family,
            family_index,
            seed,
            replicates,
            float(config["null_model"].get("mutation_rate", 0.18)),
            alpha,
            primary,
        )
        for family_index, family in enumerate(families)
    ]
    print(
        f"mechanism panel: {len(pages)} pages, {replicates} replicates x "
        f"{len(families)} families, {workers} workers",
        flush=True,
    )
    if workers > 1:
        with ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        ) as executor:
            futures = {
                executor.submit(_family_samples_star, arguments): arguments[3]
                for arguments in family_arguments
            }
            completed: dict[str, dict[str, list[float]]] = {}
            for future in as_completed(futures):
                family, values = future.result()
                completed[family] = values
                print(f"mechanism panel: completed {family}", flush=True)
            family_values = [(family, completed[family]) for family in families]
    else:
        family_values = []
        for arguments in family_arguments:
            family, values = _family_samples(*arguments)
            family_values.append((family, values))
            print(f"mechanism panel: completed {family}", flush=True)
    null_results: dict[str, dict[str, Any]] = {}
    raw_p: dict[str, float] = {}
    for family, values in family_values:
        summaries: dict[str, Any] = {}
        for metric, samples in values.items():
            mean = sum(samples) / len(samples)
            variance = sum((value - mean) ** 2 for value in samples) / max(1, len(samples) - 1)
            p_value = (1 + sum(value >= observed[metric] for value in samples)) / (len(samples) + 1)
            key = f"{family}:{metric}"
            raw_p[key] = p_value
            summaries[metric] = {
                "mean": mean,
                "standard_deviation": math.sqrt(variance),
                "observed_minus_null": observed[metric] - mean,
                "empirical_one_sided_p": p_value,
                "samples": samples,
            }
        null_results[family] = summaries
    adjusted = _holm_adjust(raw_p)
    for family, metrics in null_results.items():
        for metric, summary in metrics.items():
            summary["holm_adjusted_p"] = adjusted[f"{family}:{metric}"]

    manifest = root / config["source_manifest"]
    train_ids = [page.page_id for page in train]
    heldout_ids = [page.page_id for page in heldout]
    overlap = set(train_ids) & set(heldout_ids)
    union = set(train_ids) | set(heldout_ids)
    return {
        "schema_version": "1.0",
        "experiment_id": config["experiment_id"],
        "hypothesis_id": config["hypothesis_id"],
        "run_finished_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "question": "Which explicit sequence mechanisms are compatible with Voynichese structure?",
        "observed_metrics": observed,
        "null_results": null_results,
        "split": {
            "grouping_unit": "physical_page",
            "assignment_method": "seeded stratification by Currier, hand, and section",
            "train_pages": train_ids,
            "heldout_pages": heldout_ids,
            "overlap_page_count": len(overlap),
            "union_page_count": len(union),
            "coverage_matches_corpus_audit": len(union) == len(pages),
            "train_group_count": sum(len(page.groups) for page in train),
            "heldout_group_count": sum(len(page.groups) for page in heldout),
        },
        "corpus_audit": {
            "pages": len(pages),
            "groups": sum(len(page.groups) for page in pages),
            "excluded_uncertain_or_markup_groups": sum(page.excluded_group_count for page in pages),
            "normalization": config["normalization"],
        },
        "decision_rule": config["metrics"]["decision_rule"],
        "interpretation_boundary": {
            "posterior_probability": None,
            "reason": (
                "A posterior needs explicit priors and independently calibrated meaningful and "
                "nonsemantic generator families. These first tests can reject mechanisms, not "
                "detect meaning."
            ),
        },
        "provenance": {
            "source_path": parameters["input_path"],
            "source_sha256": sha256_file(source_path),
            "source_manifest": config["source_manifest"],
            "source_manifest_sha256": sha256_file(manifest),
            "config_path": config_path.relative_to(root).as_posix(),
            "config_sha256": sha256_file(config_path),
            "seed": seed,
            "workers": workers,
            "git": git_provenance(root),
            "environment": {
                "device": "cpu",
                "python": sys.version,
                "platform": platform.platform(),
                "uv_lock_sha256": sha256_file(root / "uv.lock"),
            },
        },
    }


def _family_samples_star(arguments: tuple[Any, ...]) -> tuple[str, dict[str, list[float]]]:
    """Unpack process-pool arguments without relying on a lambda."""
    return _family_samples(*arguments)


def validate_result(result: dict[str, Any]) -> None:
    """Require the committed result contract before an immutable write."""
    schema_path = repository_root() / "schemas" / "mechanism-result.schema.json"
    schema = orjson.loads(schema_path.read_bytes())
    Draft202012Validator(schema).validate(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Immutable output already exists: {args.output}")
    result = run_study(args.config.resolve())
    validate_result(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(
        orjson.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE)
    )


if __name__ == "__main__":
    main()
