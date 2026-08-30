"""E-006 character-relation representations for known-payload retrieval."""

from __future__ import annotations

import argparse
import bz2
import hashlib
import importlib.metadata
import lzma
import math
import platform
import random
import sys
import zlib
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import orjson
import yaml
from jsonschema import Draft202012Validator
from sklearn.metrics import roc_auc_score

from manuscript_lab.feature_panel import extract_sequence_features
from manuscript_lab.known_payload_retrieval import (
    _fit_pair_ensemble,
    _predict_pair_ensemble,
    cipher_object,
    document_segments,
    encipher_roundtrip,
    fixed_groups,
    normalize_gutenberg,
    pair_feature_vector,
    retrieval_metrics,
)
from manuscript_lab.ledger import git_provenance
from manuscript_lab.provenance import repository_root, sha256_file

LATIN25 = "ABCDEFGHIKLMNOPQRSTUVWXYZ"
LATIN25_INDEX = {symbol: index for index, symbol in enumerate(LATIN25)}


def first_occurrence_canonical(text: str) -> bytes:
    """Encode equality structure without retaining symbol identities."""
    mapping: dict[str, int] = {}
    values = []
    for symbol in text:
        if symbol not in mapping:
            mapping[symbol] = len(mapping)
        values.append(mapping[symbol])
    if len(mapping) > 255:
        raise ValueError("Canonical byte view supports at most 255 distinct symbols")
    return bytes(values)


def _compressor(name: str) -> Callable[[bytes], bytes]:
    functions: dict[str, Callable[[bytes], bytes]] = {
        "zlib": lambda value: zlib.compress(value, level=9),
        "bz2": lambda value: bz2.compress(value, compresslevel=9),
        "lzma": lambda value: lzma.compress(value, preset=9),
    }
    try:
        return functions[name]
    except KeyError as exc:
        raise ValueError(f"Unsupported compressor: {name}") from exc


def normalized_compression_distance(
    left: bytes, right: bytes, algorithm: str
) -> tuple[float, float]:
    """Return symmetric NCD and relative individual compressed-length difference."""
    compress = _compressor(algorithm)
    left_length = len(compress(left))
    right_length = len(compress(right))
    joint_length = min(len(compress(left + right)), len(compress(right + left)))
    denominator = max(left_length, right_length, 1)
    ncd = (joint_length - min(left_length, right_length)) / denominator
    relative_length = abs(left_length - right_length) / (left_length + right_length + 1e-9)
    return float(ncd), float(relative_length)


def compression_distance_vector(left: str, right: str, config: dict[str, Any]) -> np.ndarray:
    rows = []
    views = {
        "raw": (left.encode("ascii"), right.encode("ascii")),
        "first-occurrence-canonical": (
            first_occurrence_canonical(left),
            first_occurrence_canonical(right),
        ),
    }
    for view in config["views"]:
        for algorithm in config["algorithms"]:
            rows.extend(normalized_compression_distance(*views[view], str(algorithm)))
    return np.asarray(rows, dtype=float)


def _sorted_count_spectrum(tokens: list[str], retained: int) -> list[float]:
    if not tokens:
        return [0.0] * retained
    values = sorted((count / len(tokens) for count in Counter(tokens).values()), reverse=True)
    return (values + [0.0] * retained)[:retained]


def _normalized_entropy(values: np.ndarray, modulus: int) -> float:
    if not len(values):
        return 0.0
    counts = np.bincount(values.astype(int), minlength=modulus).astype(float)
    probabilities = counts[counts > 0] / counts.sum()
    return float(-(probabilities * np.log2(probabilities)).sum() / math.log2(modulus))


def invariant_signature(text: str, config: dict[str, Any]) -> np.ndarray:
    """Fixed-length symbol-renaming-invariant distribution and recurrence signature."""
    rows: list[float] = [len(text) / 1200.0, len(set(text)) / 25.0]
    retained = int(config["retained_sorted_counts"])
    for order in config["ngram_orders"]:
        width = int(order)
        tokens = [text[index : index + width] for index in range(len(text) - width + 1)]
        rows.extend(_sorted_count_spectrum(tokens, retained))
    for lag in range(1, int(config["equality_lags"]) + 1):
        rows.append(
            sum(left == right for left, right in zip(text[:-lag], text[lag:], strict=True))
            / max(len(text) - lag, 1)
        )
    for period in config["residue_periods"]:
        entropies = []
        maxima = []
        for residue in range(int(period)):
            symbols = text[residue :: int(period)]
            counts = np.asarray(list(Counter(symbols).values()), dtype=float)
            probabilities = counts / max(counts.sum(), 1.0)
            entropies.append(float(-(probabilities * np.log2(probabilities)).sum() / math.log2(25)))
            maxima.append(float(probabilities.max(initial=0.0)))
        for values in (entropies, maxima):
            rows.extend([float(np.mean(values)), float(np.std(values)), min(values), max(values)])
    return np.asarray(rows, dtype=float)


def _token_values(text: str, width: int, *, frequency_rank: bool) -> np.ndarray:
    tokens = [text[index : index + width] for index in range(0, len(text) - width + 1, width)]
    if frequency_rank or width > 1:
        counts = Counter(tokens)
        ordered = sorted(counts, key=lambda token: (-counts[token], token))
        mapping = {token: index % 25 for index, token in enumerate(ordered)}
    else:
        mapping = LATIN25_INDEX
    return np.asarray([mapping[token] for token in tokens], dtype=int)


def _resample_pair(left: np.ndarray, right: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    size = min(len(left), len(right))
    if not size:
        raise ValueError("Cannot align empty sequences")
    left_indices = np.linspace(0, len(left) - 1, size).round().astype(int)
    right_indices = np.linspace(0, len(right) - 1, size).round().astype(int)
    return left[left_indices], right[right_indices]


def _operation_profile(values: np.ndarray, periods: list[int], modulus: int) -> list[float]:
    counts = np.bincount(values, minlength=modulus).astype(float)
    probabilities = counts / counts.sum()
    rows = [
        _normalized_entropy(values, modulus),
        float(probabilities.max()),
        float(np.square(probabilities).sum()),
    ]
    for period in periods:
        entropies = []
        maxima = []
        for residue in range(period):
            subset = values[residue::period]
            subset_counts = np.bincount(subset, minlength=modulus).astype(float)
            subset_probabilities = subset_counts / subset_counts.sum()
            entropies.append(_normalized_entropy(subset, modulus))
            maxima.append(float(subset_probabilities.max()))
        rows.extend(
            [
                float(np.mean(entropies)),
                float(np.std(entropies)),
                float(np.mean(maxima)),
                float(np.std(maxima)),
            ]
        )
    return rows


def _normalized_mutual_information(left: np.ndarray, right: np.ndarray, modulus: int) -> float:
    contingency = np.zeros((modulus, modulus), dtype=float)
    np.add.at(contingency, (left, right), 1.0)
    joint = contingency / contingency.sum()
    left_probability = joint.sum(axis=1)
    right_probability = joint.sum(axis=0)
    expected = left_probability[:, None] * right_probability[None, :]
    mask = joint > 0
    mutual_information = float((joint[mask] * np.log2(joint[mask] / expected[mask])).sum())
    denominator = max(
        _normalized_entropy(left, modulus) * math.log2(modulus),
        _normalized_entropy(right, modulus) * math.log2(modulus),
        1e-9,
    )
    return mutual_information / denominator


def _aligned_relation_view(
    plain: np.ndarray, cipher: np.ndarray, config: dict[str, Any]
) -> list[float]:
    modulus = int(config["modulus"])
    periods = [int(value) for value in config["periods"]]
    plain, cipher = _resample_pair(plain, cipher)
    difference = (cipher - plain) % modulus
    summation = (cipher + plain) % modulus
    rows = _operation_profile(difference, periods, modulus)
    rows.extend(_operation_profile(summation, periods, modulus))

    affine_entropy = []
    affine_maximum = []
    for multiplier in config["affine_multipliers"]:
        residual = (cipher - int(multiplier) * plain) % modulus
        probabilities = np.bincount(residual, minlength=modulus).astype(float)
        probabilities /= probabilities.sum()
        affine_entropy.append(_normalized_entropy(residual, modulus))
        affine_maximum.append(float(probabilities.max()))
    rows.extend(
        [
            min(affine_entropy),
            float(np.median(affine_entropy)),
            float(np.std(affine_entropy)),
            max(affine_maximum),
            float(np.median(affine_maximum)),
            float(np.std(affine_maximum)),
        ]
    )
    rows.extend(
        [
            _normalized_mutual_information(plain, cipher, modulus),
            float(np.mean(plain == cipher)),
        ]
    )

    lag_mi = []
    lag_equal = []
    for shift in config["aligned_shifts"]:
        shift = int(shift)
        if shift < 0:
            left, right = plain[-shift:], cipher[:shift]
        elif shift > 0:
            left, right = plain[:-shift], cipher[shift:]
        else:
            left, right = plain, cipher
        lag_mi.append(_normalized_mutual_information(left, right, modulus))
        lag_equal.append(float(np.mean(left == right)))
    for values in (lag_mi, lag_equal):
        rows.extend([max(values), float(np.mean(values)), float(np.std(values))])
    return rows


def modular_relation_vector(plain: str, cipher: str, config: dict[str, Any]) -> np.ndarray:
    rows: list[float] = [len(cipher) / max(len(plain), 1), len(set(cipher)) / 25.0]
    for cipher_width in config["cipher_unit_widths"]:
        for frequency_rank in (False, True):
            plain_values = _token_values(plain, 1, frequency_rank=frequency_rank)
            cipher_values = _token_values(cipher, int(cipher_width), frequency_rank=frequency_rank)
            rows.extend(_aligned_relation_view(plain_values, cipher_values, config))
    return np.asarray(rows, dtype=float)


class PairRepresentations:
    """Cache individual and pair representations for the fixed benchmark."""

    def __init__(
        self,
        segments: list[dict[str, Any]],
        cipher_texts: dict[str, list[str]],
        config: dict[str, Any],
        surface_names: list[str],
        plain_surface: np.ndarray,
        cipher_surface: dict[str, np.ndarray],
        *,
        destruction_seed: int,
    ) -> None:
        self.segments = segments
        self.cipher_texts = cipher_texts
        self.config = config
        self.surface_names = surface_names
        self.plain_surface = plain_surface
        self.cipher_surface = cipher_surface
        self.invariant_plain = [
            invariant_signature(item["text"], config["invariant_signature"]) for item in segments
        ]
        self.invariant_cipher = {
            family: [invariant_signature(text, config["invariant_signature"]) for text in texts]
            for family, texts in cipher_texts.items()
        }
        self.destroyed_cipher = {
            family: [
                self._destroy(text, destruction_seed, family, index)
                for index, text in enumerate(texts)
            ]
            for family, texts in cipher_texts.items()
        }
        self.cache: dict[tuple[str, str, int, int, bool], np.ndarray] = {}

    @staticmethod
    def _destroy(text: str, seed: int, family: str, index: int) -> str:
        digest = hashlib.sha256(f"{seed}:{family}:{index}".encode()).digest()
        rng = random.Random(int.from_bytes(digest[:8], "big"))
        symbols = list(text)
        rng.shuffle(symbols)
        return "".join(symbols)

    def vector(
        self,
        representation: str,
        family: str,
        query: int,
        candidate: int,
        *,
        destroyed: bool = False,
    ) -> np.ndarray:
        key = (representation, family, query, candidate, destroyed)
        if key in self.cache:
            return self.cache[key]
        if representation == "fused-character-relation-v1":
            value = np.concatenate(
                [
                    self.vector(component, family, query, candidate, destroyed=destroyed)
                    for component in (
                        "relative-surface-sequence-pair-v1",
                        "invariant-signature-v1",
                        "modular-relation-v1",
                        "compression-distance-v1",
                    )
                ]
            )
            self.cache[key] = value
            return value
        plain = self.segments[candidate]["text"]
        cipher = (
            self.destroyed_cipher[family][query] if destroyed else self.cipher_texts[family][query]
        )
        components: dict[str, Callable[[], np.ndarray]] = {
            "relative-surface-sequence-pair-v1": lambda: pair_feature_vector(
                self.plain_surface[candidate],
                (
                    np.asarray(
                        [
                            extract_sequence_features(fixed_groups(cipher, width=5))[name]
                            for name in self.surface_names
                        ]
                    )
                    if destroyed
                    else self.cipher_surface[family][query]
                ),
            ),
            "invariant-signature-v1": lambda: pair_feature_vector(
                self.invariant_plain[candidate],
                (
                    invariant_signature(cipher, self.config["invariant_signature"])
                    if destroyed
                    else self.invariant_cipher[family][query]
                ),
            ),
            "modular-relation-v1": lambda: modular_relation_vector(
                plain, cipher, self.config["modular_relation"]
            ),
            "compression-distance-v1": lambda: compression_distance_vector(
                plain, cipher, self.config["compression"]
            ),
        }
        value = components[representation]()
        value = np.nan_to_num(value, nan=0.0, posinf=1e6, neginf=-1e6)
        self.cache[key] = value
        return value

    def precompute(
        self,
        representation: str,
        families: list[str],
        folds: np.ndarray,
        *,
        workers: int,
    ) -> None:
        """Materialize the frozen pair bank once, parallelizing compressor work."""
        normal_tasks = [
            (family, query, candidate, False)
            for family in families
            for query in range(len(self.segments))
            for candidate in range(len(self.segments))
        ]
        destruction_tasks = [
            (family, query, candidate, True)
            for family in families
            for query in range(len(self.segments))
            for candidate in range(len(self.segments))
            if folds[query] == folds[candidate]
        ]

        def calculate(task: tuple[str, int, int, bool]) -> None:
            family, query, candidate, destroyed = task
            self.vector(
                representation,
                family,
                query,
                candidate,
                destroyed=destroyed,
            )

        for label, tasks in (("normal", normal_tasks), ("destruction", destruction_tasks)):
            print(f"E-006 feature bank: {label} {len(tasks)} pairs", flush=True)
            with ThreadPoolExecutor(max_workers=workers) as executor:
                list(executor.map(calculate, tasks))
            print(f"E-006 feature bank: completed {label}", flush=True)


def _training_pairs(
    factory: PairRepresentations,
    representation: str,
    families: list[str],
    document_ids: np.ndarray,
    train: np.ndarray,
    *,
    negatives: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = random.Random(seed)
    rows = []
    labels = []
    groups = []
    for family in families:
        for query in train:
            candidates = [
                int(candidate)
                for candidate in train
                if document_ids[candidate] != document_ids[query]
            ]
            selected = rng.sample(candidates, negatives)
            for candidate, label in [(int(query), 1), *((value, 0) for value in selected)]:
                rows.append(factory.vector(representation, family, int(query), candidate))
                labels.append(label)
                groups.append(f"{family}:{document_ids[query]}:{query}")
    return np.asarray(rows), np.asarray(labels), np.asarray(groups)


def _evaluate_case(
    factory: PairRepresentations,
    representation: str,
    family: str,
    train_families: list[str],
    document_ids: np.ndarray,
    folds: np.ndarray,
    fold: int,
    *,
    negatives: int,
    seed: int,
    workers: int,
    trees: int,
    destruction: bool,
) -> tuple[dict[str, float], np.ndarray, np.ndarray | None]:
    train = np.flatnonzero(folds != fold)
    test = np.flatnonzero(folds == fold)
    train_x, train_y, train_groups = _training_pairs(
        factory,
        representation,
        train_families,
        document_ids,
        train,
        negatives=negatives,
        seed=seed,
    )
    models = _fit_pair_ensemble(
        train_x, train_y, train_groups, seed=seed, workers=workers, trees=trees
    )

    def score_matrix(*, destroyed: bool) -> np.ndarray:
        matrix = np.asarray(
            [
                factory.vector(
                    representation, family, int(query), int(candidate), destroyed=destroyed
                )
                for query in test
                for candidate in test
            ]
        )
        return _predict_pair_ensemble(models, matrix).reshape(len(test), len(test))

    scores = score_matrix(destroyed=False)
    metrics = retrieval_metrics(scores)
    metrics["pair_roc_auc"] = float(
        roc_auc_score(np.eye(len(test), dtype=int).ravel(), scores.ravel())
    )
    metrics["fold"] = int(fold)
    destroyed_scores = score_matrix(destroyed=True) if destruction else None
    return metrics, scores, destroyed_scores


def _summarize_cases(cases: list[dict[str, Any]], families: list[str]) -> dict[str, Any]:
    result = {}
    for family in families:
        selected = [case for case in cases if case["family"] == family]
        result[family] = {
            "cases": [case["metrics"] for case in selected],
            "mean_normalized_mrr": float(
                np.mean([case["metrics"]["normalized_mrr"] for case in selected])
            ),
            "mean_top1_lift_over_chance": float(
                np.mean([case["metrics"]["top1_lift_over_chance"] for case in selected])
            ),
            "mean_pair_roc_auc": float(
                np.mean([case["metrics"]["pair_roc_auc"] for case in selected])
            ),
        }
    return result


def run_campaign(config_path: Path) -> dict[str, Any]:
    root = repository_root()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    params = config["parameters"]
    benchmark_path = root / params["benchmark_config"]
    predecessor_path = root / params["predecessor_result"]
    if sha256_file(benchmark_path) != params["benchmark_config_sha256"]:
        raise ValueError("Frozen E-005 benchmark config hash mismatch")
    if sha256_file(predecessor_path) != params["predecessor_result_sha256"]:
        raise ValueError("Frozen E-005 predecessor result hash mismatch")
    benchmark = yaml.safe_load(benchmark_path.read_text(encoding="utf-8"))
    predecessor = orjson.loads(predecessor_path.read_bytes())
    benchmark_params = benchmark["parameters"]

    segments = []
    source_audit = []
    for document in benchmark_params["documents"]:
        path = root / document["path"]
        normalized = normalize_gutenberg(path.read_text(encoding="utf-8-sig"))
        selected = document_segments(
            normalized,
            segment_characters=int(benchmark_params["segment_characters"]),
            count=int(benchmark_params["segments_per_document"]),
        )
        source_audit.append(
            {
                "document_id": document["id"],
                "path": document["path"],
                "sha256": sha256_file(path),
                "genre": document["genre"],
                "fold": int(document["fold"]),
                "normalized_characters": len(normalized),
                "segment_offsets": [offset for offset, _text in selected],
            }
        )
        for segment_number, (offset, text) in enumerate(selected):
            segments.append(
                {
                    "segment_id": f"{document['id']}:{segment_number}",
                    "document_id": document["id"],
                    "fold": int(document["fold"]),
                    "offset": offset,
                    "text": text,
                }
            )
    if source_audit != predecessor["source_audit"]:
        raise ValueError("Regenerated E-005 source audit differs from the frozen predecessor")

    plain_feature_rows = [
        extract_sequence_features(
            fixed_groups(item["text"], width=int(benchmark_params["group_characters"]))
        )
        for item in segments
    ]
    surface_names = sorted(plain_feature_rows[0])
    plain_surface = np.asarray(
        [[row[name] for name in surface_names] for row in plain_feature_rows]
    )
    cipher_texts: dict[str, list[str]] = {}
    cipher_surface: dict[str, np.ndarray] = {}
    recovered_texts: dict[str, list[str]] = {}
    roundtrip: dict[str, Any] = {}
    for spec in benchmark_params["cipher_families"]:
        family = str(spec["id"])
        texts = []
        recovered = []
        exact = []
        lengths = []
        feature_rows = []
        for item in segments:
            ciphertext, passed = encipher_roundtrip(item["text"], spec)
            deciphered = cipher_object(spec).decipher(ciphertext).upper()
            texts.append(ciphertext)
            recovered.append(deciphered)
            exact.append(passed and deciphered == item["text"])
            lengths.append(len(ciphertext))
            features = extract_sequence_features(
                fixed_groups(ciphertext, width=int(benchmark_params["group_characters"]))
            )
            feature_rows.append([features[name] for name in surface_names])
        cipher_texts[family] = texts
        recovered_texts[family] = recovered
        cipher_surface[family] = np.asarray(feature_rows)
        roundtrip[family] = {
            "pairs": len(exact),
            "exact": int(sum(exact)),
            "fraction": float(np.mean(exact)),
            "ciphertext_character_range": [min(lengths), max(lengths)],
        }

    representation_config = params["representations"]
    factory = PairRepresentations(
        segments,
        cipher_texts,
        representation_config,
        surface_names,
        plain_surface,
        cipher_surface,
        destruction_seed=int(config["seed"]) + 700_000,
    )
    primary = str(representation_config["primary"]["id"])
    diagnostics = [str(value) for value in representation_config["diagnostics"]]
    families = [str(spec["id"]) for spec in benchmark_params["cipher_families"]]
    folds = np.asarray([item["fold"] for item in segments])
    document_ids = np.asarray([item["document_id"] for item in segments])
    workers = int(params["workers"])
    trees = int(params["extra_trees_estimators"])
    negatives = int(params["negatives_per_positive"])
    seeds = [int(value) for value in params["classifier_seeds"]]
    factory.precompute(primary, families, folds, workers=workers)

    primary_cases: list[dict[str, Any]] = []
    retrieval_matrices: list[np.ndarray] = []
    destruction_drops = []
    for seed_number, seed in enumerate(seeds):
        for family_number, family in enumerate(families):
            for fold in sorted(set(folds)):
                case_seed = seed + family_number * 100 + int(fold)
                metrics, scores, destroyed_scores = _evaluate_case(
                    factory,
                    primary,
                    family,
                    [candidate for candidate in families if candidate != family],
                    document_ids,
                    folds,
                    int(fold),
                    negatives=negatives,
                    seed=case_seed,
                    workers=workers,
                    trees=trees,
                    destruction=True,
                )
                metrics["seed"] = seed
                destroyed_metrics = retrieval_metrics(destroyed_scores)
                destruction_drops.append(
                    metrics["normalized_mrr"] - destroyed_metrics["normalized_mrr"]
                )
                primary_cases.append({"family": family, "metrics": metrics})
                retrieval_matrices.append(scores)
            print(
                f"E-006 primary: seed {seed_number + 1}/{len(seeds)} family {family}",
                flush=True,
            )

    diagnostic_results = {}
    diagnostic_seed = seeds[0]
    for representation in diagnostics:
        cases = []
        for family_number, family in enumerate(families):
            for fold in sorted(set(folds)):
                metrics, _scores, _destroyed = _evaluate_case(
                    factory,
                    representation,
                    family,
                    [candidate for candidate in families if candidate != family],
                    document_ids,
                    folds,
                    int(fold),
                    negatives=negatives,
                    seed=diagnostic_seed + family_number * 100 + int(fold),
                    workers=workers,
                    trees=trees,
                    destruction=False,
                )
                metrics["seed"] = diagnostic_seed
                cases.append({"family": family, "metrics": metrics})
        diagnostic_results[representation] = _summarize_cases(cases, families)
        print(f"E-006 diagnostic representation: {representation}", flush=True)

    same_family_cases = []
    for family_number, family in enumerate(families):
        for fold in sorted(set(folds)):
            metrics, _scores, _destroyed = _evaluate_case(
                factory,
                primary,
                family,
                [family],
                document_ids,
                folds,
                int(fold),
                negatives=negatives,
                seed=diagnostic_seed + 50_000 + family_number * 100 + int(fold),
                workers=workers,
                trees=trees,
                destruction=False,
            )
            metrics["seed"] = diagnostic_seed
            same_family_cases.append({"family": family, "metrics": metrics})
    same_family_results = _summarize_cases(same_family_cases, families)

    ceiling_metrics = []
    for family in families:
        for fold in sorted(set(folds)):
            test = np.flatnonzero(folds == fold)
            scores = np.asarray(
                [
                    [
                        float(recovered_texts[family][query] == segments[candidate]["text"])
                        for candidate in test
                    ]
                    for query in test
                ]
            )
            ceiling_metrics.append(retrieval_metrics(scores))
    exact_ceiling_mrr = float(np.mean([value["mean_reciprocal_rank"] for value in ceiling_metrics]))

    family_results = _summarize_cases(primary_cases, families)
    family_mrr = [value["mean_normalized_mrr"] for value in family_results.values()]
    family_lift = [value["mean_top1_lift_over_chance"] for value in family_results.values()]
    family_auc = [value["mean_pair_roc_auc"] for value in family_results.values()]
    seed_means = {
        str(seed): float(
            np.mean(
                [
                    case["metrics"]["normalized_mrr"]
                    for case in primary_cases
                    if case["metrics"]["seed"] == seed
                ]
            )
        )
        for seed in seeds
    }
    roundtrip_fraction = sum(value["exact"] for value in roundtrip.values()) / sum(
        value["pairs"] for value in roundtrip.values()
    )
    aggregate = {
        "median_family_normalized_mrr": float(np.median(family_mrr)),
        "worst_family_normalized_mrr": float(min(family_mrr)),
        "median_family_top1_lift_over_chance": float(np.median(family_lift)),
        "worst_family_pair_roc_auc": float(min(family_auc)),
        "exact_roundtrip_fraction": float(roundtrip_fraction),
        "worst_seed_mean_normalized_mrr": min(seed_means.values()),
        "exact_decryption_ceiling_mrr": exact_ceiling_mrr,
    }

    observed = float(
        np.mean([retrieval_metrics(scores)["normalized_mrr"] for scores in retrieval_matrices])
    )
    rng = random.Random(int(config["seed"]) + 900_000)
    null_values = []
    for _iteration in range(int(params["permutation_iterations"])):
        values = []
        for scores in retrieval_matrices:
            permutation = list(range(len(scores)))
            rng.shuffle(permutation)
            values.append(retrieval_metrics(scores[:, permutation])["normalized_mrr"])
        null_values.append(float(np.mean(values)))
    permutation_p = (1 + sum(value >= observed for value in null_values)) / (len(null_values) + 1)

    thresholds = config["metrics"]["interpretation_gates"]
    checks = {
        "median_family_normalized_mrr": aggregate["median_family_normalized_mrr"]
        >= float(thresholds["minimum_median_family_normalized_mrr"]),
        "worst_family_normalized_mrr": aggregate["worst_family_normalized_mrr"]
        >= float(thresholds["minimum_worst_family_normalized_mrr"]),
        "median_family_top1_lift": aggregate["median_family_top1_lift_over_chance"]
        >= float(thresholds["minimum_median_family_top1_lift"]),
        "worst_family_pair_roc_auc": aggregate["worst_family_pair_roc_auc"]
        >= float(thresholds["minimum_worst_family_pair_roc_auc"]),
        "permutation_significance": permutation_p <= float(thresholds["maximum_permutation_p"]),
        "exact_roundtrip": roundtrip_fraction
        >= float(thresholds["minimum_exact_roundtrip_fraction"]),
        "worst_seed_mean_normalized_mrr": aggregate["worst_seed_mean_normalized_mrr"]
        >= float(thresholds["minimum_worst_seed_mean_normalized_mrr"]),
        "exact_decryption_ceiling_mrr": exact_ceiling_mrr
        >= float(thresholds["minimum_exact_decryption_ceiling_mrr"]),
    }
    passed = all(checks.values())
    dimensions = {
        representation: int(factory.vector(representation, families[0], 0, 0).size)
        for representation in [primary, *diagnostics]
    }
    return {
        "schema_version": "1.0",
        "experiment_id": config["experiment_id"],
        "hypothesis_id": config["hypothesis_id"],
        "run_finished_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source_audit": source_audit,
        "normalization": config["normalization"],
        "representations": {
            "primary": primary,
            "dimensions": dimensions,
            "configuration": representation_config,
            "diagnostic_results": diagnostic_results,
        },
        "cipher_suite": {
            "implementation": "pycipher",
            "installed_version": importlib.metadata.version("pycipher"),
            "revision": benchmark_params["pycipher_revision"],
            "families": benchmark_params["cipher_families"],
            "roundtrip": roundtrip,
        },
        "family_results": family_results,
        "same_family_diagnostic": same_family_results,
        "destruction_control": {
            "operation": "independent fixed-seed within-ciphertext character permutation",
            "median_normalized_mrr_drop": float(np.median(destruction_drops)),
            "mean_normalized_mrr_drop": float(np.mean(destruction_drops)),
            "positive_drop_fraction": float(np.mean(np.asarray(destruction_drops) > 0)),
        },
        "seed_means": seed_means,
        "aggregate": aggregate,
        "permutation": {
            "iterations": len(null_values),
            "observed_mean_normalized_mrr": observed,
            "null_mean": float(np.mean(null_values)),
            "one_sided_p": float(permutation_p),
        },
        "interpretation_gate": {
            "checks": checks,
            "passed": passed,
            "permitted_next_step": (
                "replicate with an independent cipher implementation suite; no Voynich scoring"
                if passed
                else "retain target exclusion and diagnose the failed regime; no Voynich scoring"
            ),
            "voynich_scored": False,
            "posterior_probability": None,
        },
        "provenance": {
            "source_manifest": config["source_manifest"],
            "source_manifest_sha256": sha256_file(root / config["source_manifest"]),
            "benchmark_config": params["benchmark_config"],
            "benchmark_config_sha256": sha256_file(benchmark_path),
            "predecessor_result": params["predecessor_result"],
            "predecessor_result_sha256": sha256_file(predecessor_path),
            "source_code_archive": benchmark_params["source_code_archive"],
            "source_code_archive_sha256": sha256_file(
                root / benchmark_params["source_code_archive"]
            ),
            "config_path": config_path.relative_to(root).as_posix(),
            "config_sha256": sha256_file(config_path),
            "classifier_seeds": seeds,
            "workers": workers,
            "extra_trees_estimators": trees,
            "git": git_provenance(root),
            "environment": {
                "device": "cpu",
                "python": sys.version,
                "platform": platform.platform(),
                "uv_lock_sha256": sha256_file(root / "uv.lock"),
            },
        },
    }


def validate_result(result: dict[str, Any]) -> None:
    schema = orjson.loads(
        (repository_root() / "schemas" / "cipher-relation-result.schema.json").read_bytes()
    )
    Draft202012Validator(schema).validate(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Immutable output already exists: {args.output}")
    result = run_campaign(args.config.resolve())
    validate_result(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(
        orjson.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE)
    )


if __name__ == "__main__":
    main()
