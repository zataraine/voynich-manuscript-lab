"""E-007 deterministic localization of ADFGX stage and unitization failures."""

from __future__ import annotations

import argparse
import importlib.metadata
import itertools
import platform
import random
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numba
import numpy as np
import orjson
import pycipher
import pynini
import yaml
from numba import njit
from sklearn.metrics import roc_auc_score

from manuscript_lab.known_payload_retrieval import document_segments, normalize_gutenberg
from manuscript_lab.ledger import git_provenance
from manuscript_lab.provenance import repository_root, sha256_file

LATIN25 = "ABCDEFGHIKLMNOPQRSTUVWXYZ"


def validate_square(square: str) -> None:
    if len(square) != 25 or set(square) != set(LATIN25):
        raise ValueError("Polybius square must be a permutation of the 25-letter alphabet")


def polybius_maps(square: str, coordinates: str = "ADFGX") -> tuple[dict[str, str], dict[str, str]]:
    validate_square(square)
    if len(coordinates) != 5 or len(set(coordinates)) != 5:
        raise ValueError("Coordinate alphabet must contain five unique symbols")
    forward = {
        symbol: coordinates[index // 5] + coordinates[index % 5]
        for index, symbol in enumerate(square)
    }
    return forward, {pair: symbol for symbol, pair in forward.items()}


def fractionate(text: str, square: str, coordinates: str = "ADFGX") -> str:
    forward, _reverse = polybius_maps(square, coordinates)
    try:
        return "".join(forward[symbol] for symbol in text)
    except KeyError as exc:
        raise ValueError(f"Symbol outside Polybius square: {exc.args[0]}") from exc


def defractionate(stream: str, square: str, coordinates: str = "ADFGX") -> str:
    _forward, reverse = polybius_maps(square, coordinates)
    if len(stream) % 2:
        raise ValueError("Fractionated stream length must be even")
    try:
        return "".join(reverse[stream[index : index + 2]] for index in range(0, len(stream), 2))
    except KeyError as exc:
        raise ValueError(f"Invalid coordinate pair: {exc.args[0]}") from exc


def keyword_read_order(keyword: str) -> tuple[int, ...]:
    if not keyword or len(set(keyword)) != len(keyword):
        raise ValueError("E-007 keywords must be nonempty and contain unique symbols")
    return tuple(sorted(range(len(keyword)), key=lambda index: keyword[index]))


def columnar_encipher(stream: str, read_order: tuple[int, ...]) -> str:
    width = len(read_order)
    if sorted(read_order) != list(range(width)):
        raise ValueError("Column read order must be a permutation")
    return "".join(stream[column::width] for column in read_order)


def columnar_decipher(ciphertext: str, read_order: tuple[int, ...]) -> str:
    width = len(read_order)
    if sorted(read_order) != list(range(width)):
        raise ValueError("Column read order must be a permutation")
    base, extra = divmod(len(ciphertext), width)
    lengths = [base + int(column < extra) for column in range(width)]
    columns = [""] * width
    cursor = 0
    for column in read_order:
        columns[column] = ciphertext[cursor : cursor + lengths[column]]
        cursor += lengths[column]
    return "".join(
        columns[column][row]
        for row in range(base + bool(extra))
        for column in range(width)
        if row < len(columns[column])
    )


def adfgx_encipher(text: str, square: str, keyword: str) -> tuple[str, str]:
    intermediate = fractionate(text, square)
    return intermediate, columnar_encipher(intermediate, keyword_read_order(keyword))


def modal_consistency_score(plain: np.ndarray, coordinates: np.ndarray) -> float:
    """Pure-Python reference for the bidirectional plaintext/pair consistency score."""
    if coordinates.size != plain.size * 2:
        raise ValueError("Coordinate stream must have exactly two symbols per plaintext symbol")
    pairs = coordinates[0::2] * 5 + coordinates[1::2]
    counts = np.zeros((25, 25), dtype=np.int64)
    np.add.at(counts, (plain, pairs), 1)
    forward_errors = plain.size - counts.max(axis=1).sum()
    reverse_errors = plain.size - counts.max(axis=0).sum()
    return float(1.0 - (forward_errors + reverse_errors) / (2.0 * plain.size))


@njit(cache=True)
def _score_one(plain: np.ndarray, coordinates: np.ndarray) -> float:
    counts = np.zeros((25, 25), dtype=np.int32)
    for index in range(plain.size):
        pair = coordinates[index * 2] * 5 + coordinates[index * 2 + 1]
        counts[plain[index], pair] += 1
    forward_correct = 0
    reverse_correct = 0
    for left in range(25):
        best = 0
        for right in range(25):
            if counts[left, right] > best:
                best = counts[left, right]
        forward_correct += best
    for right in range(25):
        best = 0
        for left in range(25):
            if counts[left, right] > best:
                best = counts[left, right]
        reverse_correct += best
    return (forward_correct + reverse_correct) / (2.0 * plain.size)


@njit(cache=True)
def _restore_columns(ciphertext: np.ndarray, order: np.ndarray, restored: np.ndarray) -> None:
    width = order.size
    base = ciphertext.size // width
    extra = ciphertext.size % width
    cursor = 0
    for order_index in range(width):
        column = order[order_index]
        length = base + (1 if column < extra else 0)
        for row in range(length):
            restored[row * width + column] = ciphertext[cursor]
            cursor += 1


@njit(cache=True)
def best_combined_scores(
    ciphertext: np.ndarray, plains: np.ndarray, permutations: np.ndarray
) -> np.ndarray:
    restored = np.empty(ciphertext.size, dtype=np.int8)
    best = np.zeros(plains.shape[0], dtype=np.float64)
    for permutation_index in range(permutations.shape[0]):
        _restore_columns(ciphertext, permutations[permutation_index], restored)
        for candidate in range(plains.shape[0]):
            score = _score_one(plains[candidate], restored)
            if score > best[candidate]:
                best[candidate] = score
    return best


@njit(cache=True)
def best_stream_scores(
    ciphertext: np.ndarray, streams: np.ndarray, permutations: np.ndarray
) -> np.ndarray:
    restored = np.empty(ciphertext.size, dtype=np.int8)
    best = np.zeros(streams.shape[0], dtype=np.float64)
    for permutation_index in range(permutations.shape[0]):
        _restore_columns(ciphertext, permutations[permutation_index], restored)
        for candidate in range(streams.shape[0]):
            matches = 0
            for index in range(ciphertext.size):
                matches += restored[index] == streams[candidate, index]
            score = matches / ciphertext.size
            if score > best[candidate]:
                best[candidate] = score
    return best


def _encode_plain(text: str) -> np.ndarray:
    lookup = {symbol: index for index, symbol in enumerate(LATIN25)}
    return np.asarray([lookup[symbol] for symbol in text], dtype=np.int8)


def _encode_coordinates(text: str) -> np.ndarray:
    lookup = {symbol: index for index, symbol in enumerate("ADFGX")}
    return np.asarray([lookup[symbol] for symbol in text], dtype=np.int8)


def _permutations(width: int) -> np.ndarray:
    return np.asarray(list(itertools.permutations(range(width))), dtype=np.int8)


def tie_safe_retrieval(score_matrix: np.ndarray) -> dict[str, float]:
    count = score_matrix.shape[0]
    ranks = []
    for index, scores in enumerate(score_matrix):
        target = scores[index]
        rank = 1.0 + float(np.sum(scores > target)) + 0.5 * float(np.sum(scores == target) - 1)
        ranks.append(rank)
    mrr = float(np.mean(1.0 / np.asarray(ranks)))
    chance = float(sum(1.0 / rank for rank in range(1, count + 1)) / count)
    labels = np.eye(count, dtype=np.int8).ravel()
    return {
        "queries": count,
        "mean_reciprocal_rank": mrr,
        "normalized_mrr": (mrr - chance) / (1.0 - chance),
        "pair_roc_auc": float(roc_auc_score(labels, score_matrix.ravel())),
        "top1_fraction": float(np.mean(np.asarray(ranks) == 1.0)),
        "median_rank": float(np.median(ranks)),
    }


def _fst_roundtrip(text: str, square: str) -> tuple[str, bool]:
    forward, _reverse = polybius_maps(square)
    transducer = pynini.closure(pynini.string_map(sorted(forward.items()))).optimize()
    encoded = pynini.shortestpath(pynini.accep(text) @ transducer).string()
    decoded = pynini.shortestpath(pynini.accep(encoded) @ pynini.invert(transducer)).string()
    return encoded, decoded == text


def _load_segments(root: Path, benchmark: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    params = benchmark["parameters"]
    texts = []
    audit = []
    for document in params["documents"]:
        path = root / document["path"]
        normalized = normalize_gutenberg(path.read_text(encoding="utf-8-sig"))
        offset, text = document_segments(
            normalized,
            segment_characters=int(params["segment_characters"]),
            count=int(params["segments_per_document"]),
        )[0]
        texts.append(text)
        audit.append(
            {
                "document_id": document["id"],
                "path": document["path"],
                "sha256": sha256_file(path),
                "offset": offset,
                "characters": len(text),
            }
        )
    return texts, audit


def _permutation_p(
    matrices: list[np.ndarray], observed: float, iterations: int, seed: int
) -> float:
    rng = random.Random(seed)
    null = []
    count = matrices[0].shape[0]
    for _ in range(iterations):
        values = []
        for matrix in matrices:
            assignment = list(range(count))
            rng.shuffle(assignment)
            permuted = matrix[:, assignment]
            values.append(tie_safe_retrieval(permuted)["normalized_mrr"])
        null.append(float(np.mean(values)))
    return float((1 + sum(value >= observed for value in null)) / (iterations + 1))


def run_experiment(config_path: Path) -> dict[str, Any]:
    root = repository_root()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    params = config["parameters"]
    benchmark_path = root / params["benchmark_config"]
    if sha256_file(benchmark_path) != params["benchmark_config_sha256"]:
        raise ValueError("Frozen E-005 benchmark config hash changed")
    predecessor = root / params["predecessor_result"]
    if sha256_file(predecessor) != params["predecessor_result_sha256"]:
        raise ValueError("Frozen E-006 result hash changed")
    benchmark = yaml.safe_load(benchmark_path.read_text(encoding="utf-8"))
    texts, source_audit = _load_segments(root, benchmark)
    plains = np.asarray([_encode_plain(text) for text in texts])

    variants: dict[str, Any] = {}
    combined_matrices = []
    oracle_checks = []
    fst_checks = []
    order_checks = []
    width_margins = []
    exact_stage_checks = []

    for spec in params["variants"]:
        variant_id = spec["id"]
        square = spec["square"]
        keyword = spec["keyword"]
        width = int(spec["width"])
        order = keyword_read_order(keyword)
        permutations = _permutations(width)
        wrong_permutations = _permutations(int(spec["wrong_width"]))
        streams_text = []
        ciphers_text = []
        for text in texts:
            intermediate, ciphertext = adfgx_encipher(text, square, keyword)
            streams_text.append(intermediate)
            ciphers_text.append(ciphertext)
            exact_stage_checks.append(
                defractionate(columnar_decipher(ciphertext, order), square) == text
            )
            oracle_checks.append(
                pycipher.ADFGX(key=square, keyword=keyword).encipher(text).upper() == ciphertext
            )
            fst_encoded, fst_ok = _fst_roundtrip(text, square)
            fst_checks.append(fst_ok and fst_encoded == intermediate)

        streams = np.asarray([_encode_coordinates(stream) for stream in streams_text])
        fractionation = np.asarray(
            [
                [
                    modal_consistency_score(plains[candidate], streams[query])
                    for candidate in range(len(texts))
                ]
                for query in range(len(texts))
            ]
        )
        transposition = np.asarray(
            [
                best_stream_scores(_encode_coordinates(ciphertext), streams, permutations)
                for ciphertext in ciphers_text
            ]
        )
        combined = np.asarray(
            [
                best_combined_scores(_encode_coordinates(ciphertext), plains, permutations)
                for ciphertext in ciphers_text
            ]
        )
        combined_matrices.append(combined)

        actual = np.asarray(order, dtype=np.int8)
        for query, ciphertext in enumerate(ciphers_text):
            restored = np.empty(len(ciphertext), dtype=np.int8)
            _restore_columns(_encode_coordinates(ciphertext), actual, restored)
            actual_score = _score_one(plains[query], restored)
            order_checks.append(bool(np.isclose(actual_score, combined[query, query])))
            wrong_scores = best_combined_scores(
                _encode_coordinates(ciphertext), plains[query : query + 1], wrong_permutations
            )
            width_margins.append(float(combined[query, query] - wrong_scores[0]))

        variants[variant_id] = {
            "width": width,
            "wrong_width": int(spec["wrong_width"]),
            "permutations": int(permutations.shape[0]),
            "read_order": list(order),
            "fractionation": tie_safe_retrieval(fractionation),
            "transposition": tie_safe_retrieval(transposition),
            "combined": tie_safe_retrieval(combined),
            "combined_score_range": [float(combined.min()), float(combined.max())],
            "median_correct_minus_wrong_width_margin": float(
                np.median(width_margins[-len(texts) :])
            ),
        }

    cryptii_square = "BTALPDHOZKQFVSNGICUXMREWY"
    _intermediate, cryptii_cipher = adfgx_encipher("ATTACKATONCE", cryptii_square, "CARGO")
    cryptii_ok = cryptii_cipher == "FAXDFADDDGDGFFFAFAXAFAFX"
    oracle_checks.append(cryptii_ok)

    fractionation_mrr = min(value["fractionation"]["normalized_mrr"] for value in variants.values())
    transposition_mrr = min(value["transposition"]["normalized_mrr"] for value in variants.values())
    worst_combined_mrr = min(value["combined"]["normalized_mrr"] for value in variants.values())
    worst_combined_auc = min(value["combined"]["pair_roc_auc"] for value in variants.values())
    observed_combined = float(
        np.mean([tie_safe_retrieval(matrix)["normalized_mrr"] for matrix in combined_matrices])
    )
    metrics = {
        "independent_oracle_fraction": float(np.mean(oracle_checks)),
        "fst_roundtrip_fraction": float(np.mean(fst_checks)),
        "exact_stage_roundtrip_fraction": float(np.mean(exact_stage_checks)),
        "fractionation_normalized_mrr": float(fractionation_mrr),
        "transposition_normalized_mrr": float(transposition_mrr),
        "worst_variant_combined_normalized_mrr": float(worst_combined_mrr),
        "worst_variant_combined_pair_roc_auc": float(worst_combined_auc),
        "true_order_in_maximizer_fraction": float(np.mean(order_checks)),
        "median_correct_minus_wrong_width_margin": float(np.median(width_margins)),
        "combined_permutation_one_sided_p": _permutation_p(
            combined_matrices,
            observed_combined,
            int(params["permutation_iterations"]),
            int(params["seed"]),
        ),
    }
    gates = config["metrics"]["interpretation_gates"]
    gate_results = {
        "independent_oracle": metrics["independent_oracle_fraction"]
        >= gates["minimum_independent_oracle_fraction"],
        "fst_roundtrip": metrics["fst_roundtrip_fraction"]
        >= gates["minimum_fst_roundtrip_fraction"],
        "fractionation": metrics["fractionation_normalized_mrr"]
        >= gates["minimum_fractionation_normalized_mrr"],
        "transposition": metrics["transposition_normalized_mrr"]
        >= gates["minimum_transposition_normalized_mrr"],
        "combined_mrr": metrics["worst_variant_combined_normalized_mrr"]
        >= gates["minimum_worst_variant_combined_normalized_mrr"],
        "combined_auc": metrics["worst_variant_combined_pair_roc_auc"]
        >= gates["minimum_worst_variant_combined_pair_roc_auc"],
        "true_order": metrics["true_order_in_maximizer_fraction"]
        >= gates["minimum_true_order_in_maximizer_fraction"],
        "wrong_width": metrics["median_correct_minus_wrong_width_margin"]
        >= gates["minimum_median_correct_minus_wrong_width_margin"],
        "permutation": metrics["combined_permutation_one_sided_p"]
        <= gates["maximum_combined_permutation_p"],
    }
    result = {
        "schema_version": "1.0",
        "experiment_id": config["experiment_id"],
        "hypothesis_id": config["hypothesis_id"],
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "pass" if all(gate_results.values()) else "fail",
        "target_scored": False,
        "config": str(config_path.relative_to(root)),
        "config_sha256": sha256_file(config_path),
        "source_manifest_sha256": sha256_file(root / config["source_manifest"]),
        "oracle_manifest_sha256": sha256_file(root / config["oracle_source_manifest"]),
        "source_audit": source_audit,
        "variants": variants,
        "metrics": metrics,
        "gates": gate_results,
        "gate_count": {"passed": sum(gate_results.values()), "total": len(gate_results)},
        "provenance": {
            **git_provenance(root),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": np.__version__,
            "numba": numba.__version__,
            "pynini": importlib.metadata.version("pynini"),
            "pycipher_commit": "8f1d7cf3cba4e12171e27d9ce723ad890194de19",
            "cryptii_commit": "c04a823b5f3f0c8dfc9d8a4bd10e35ef8177d642",
        },
        "interpretation": (
            "Known-control stage localization only; no Voynich inference is permitted."
        ),
    }
    output = root / config["artifacts"]["root"] / "result.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(
        orjson.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    result = run_experiment(args.config.resolve())
    print(
        orjson.dumps(
            {"status": result["status"], "metrics": result["metrics"], "gates": result["gates"]},
            option=orjson.OPT_INDENT_2,
        ).decode()
    )


if __name__ == "__main__":
    main()
