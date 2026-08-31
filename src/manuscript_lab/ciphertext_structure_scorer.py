"""Ciphertext-only, symbol-renaming-invariant scorer for E-009."""

from __future__ import annotations

import argparse
import math
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numba
import numpy as np
import orjson
import yaml
from numba import njit

from manuscript_lab.adfgx_stage_localization import (
    _encode_coordinates,
    _permutations,
    _restore_columns,
)
from manuscript_lab.ledger import git_provenance
from manuscript_lab.provenance import repository_root, sha256_file

FORBIDDEN_PUBLIC_KEYS = {
    "base_id",
    "family",
    "keyword",
    "offset",
    "plaintext",
    "plaintext_sha256",
    "read_order",
    "source_id",
    "source_path",
    "square",
    "width",
}


def _recursive_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        keys.update(value)
        for item in value.values():
            keys.update(_recursive_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(_recursive_keys(item))
    return keys


@njit(cache=True)
def order2_over_order1_scores(
    ciphertext: np.ndarray,
    permutations: np.ndarray,
    train_fraction: float,
    alpha: float,
    backoff_k: float,
) -> np.ndarray:
    restored = np.empty(ciphertext.size, dtype=np.int8)
    symbol_count = ciphertext.size // 2
    symbols = np.empty(symbol_count, dtype=np.int16)
    split = int(symbol_count * train_fraction)
    if split < 3:
        split = 3
    if split >= symbol_count:
        split = symbol_count - 1
    scores = np.empty(permutations.shape[0], dtype=np.float64)
    log2 = math.log(2.0)
    for permutation_index in range(permutations.shape[0]):
        _restore_columns(ciphertext, permutations[permutation_index], restored)
        for index in range(symbol_count):
            symbols[index] = restored[index * 2] * 5 + restored[index * 2 + 1]
        order1 = np.zeros((25, 25), dtype=np.int32)
        order1_totals = np.zeros(25, dtype=np.int32)
        order2 = np.zeros((625, 25), dtype=np.int32)
        order2_totals = np.zeros(625, dtype=np.int32)
        for index in range(1, split):
            context1 = symbols[index - 1]
            target = symbols[index]
            order1[context1, target] += 1
            order1_totals[context1] += 1
            if index >= 2:
                context2 = symbols[index - 2] * 25 + symbols[index - 1]
                order2[context2, target] += 1
                order2_totals[context2] += 1
        gain = 0.0
        evaluated = 0
        for index in range(split, symbol_count):
            context1 = symbols[index - 1]
            context2 = symbols[index - 2] * 25 + symbols[index - 1]
            target = symbols[index]
            probability1 = (order1[context1, target] + alpha) / (
                order1_totals[context1] + alpha * 25.0
            )
            probability2_raw = (order2[context2, target] + alpha) / (
                order2_totals[context2] + alpha * 25.0
            )
            weight = order2_totals[context2] / (order2_totals[context2] + backoff_k)
            probability2 = weight * probability2_raw + (1.0 - weight) * probability1
            gain += math.log(probability2 / probability1) / log2
            evaluated += 1
        scores[permutation_index] = gain / evaluated
    return scores


def score_public_suite(config_path: Path) -> dict[str, Any]:
    root = repository_root()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    for boundary in (
        "plaintext_inputs_permitted",
        "candidate_inputs_permitted",
        "truth_inputs_permitted",
        "generator_seed_permitted",
        "semantic_model_permitted",
    ):
        if config.get(boundary) is not False:
            raise ValueError(f"Ciphertext-only scorer must forbid {boundary}")
    public_path = root / config["public_suite"]
    public = orjson.loads(public_path.read_bytes())
    leaked = sorted(FORBIDDEN_PUBLIC_KEYS & _recursive_keys(public))
    if leaked:
        raise ValueError(f"Public ciphertext suite leaks forbidden keys: {leaked}")
    if public.get("input_fields") != ["query_id", "ciphertext"]:
        raise ValueError("Public suite contains an unexpected input contract")

    widths = [int(value) for value in config["hypothesized_widths"]]
    permutations = {width: _permutations(width) for width in widths}
    objective = config["objective"]
    train_fraction = float(objective["train_fraction"])
    alpha = float(objective["smoothing_alpha"])
    backoff_k = float(objective["interpolation_backoff_k"])
    width_seconds = {str(width): 0.0 for width in widths}
    scored_queries = []
    for query in public["queries"]:
        ciphertext = _encode_coordinates(query["ciphertext"])
        heldout_symbols = ciphertext.size // 2 - int(ciphertext.size // 2 * train_fraction)
        width_results = {}
        for width in widths:
            started = time.perf_counter()
            raw_scores = order2_over_order1_scores(
                ciphertext,
                permutations[width],
                train_fraction,
                alpha,
                backoff_k,
            )
            width_seconds[str(width)] += time.perf_counter() - started
            raw_maximum = float(raw_scores.max())
            penalty = math.sqrt(2.0 * math.log(permutations[width].shape[0]) / heldout_symbols)
            maximizers = np.flatnonzero(np.isclose(raw_scores, raw_maximum)).tolist()
            width_results[str(width)] = {
                "raw_order_scores": raw_scores.astype(np.float32).tolist(),
                "raw_maximum": raw_maximum,
                "complexity_penalty": penalty,
                "corrected_score": raw_maximum - penalty,
                "maximizing_order_indices": maximizers,
            }
        scored_queries.append({"query_id": query["query_id"], "widths": width_results})

    result = {
        "schema_version": "1.0",
        "scorer_id": config["scorer_id"],
        "generated_at": datetime.now(UTC).isoformat(),
        "plaintext_accessed": False,
        "candidate_plaintext_accessed": False,
        "truth_accessed": False,
        "public_suite_sha256": sha256_file(public_path),
        "scorer_config": str(config_path.relative_to(root)),
        "scorer_config_sha256": sha256_file(config_path),
        "objective": objective,
        "hypothesized_widths": widths,
        "width_seconds": width_seconds,
        "queries": scored_queries,
        "provenance": {**git_provenance(root), "numba": numba.__version__},
    }
    output = root / config["output"]
    if output.exists():
        raise FileExistsError(f"Immutable output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(
        orjson.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    result = score_public_suite(args.config.resolve())
    print(
        orjson.dumps(
            {
                "queries": len(result["queries"]),
                "truth_accessed": result["truth_accessed"],
                "width_seconds": result["width_seconds"],
            },
            option=orjson.OPT_INDENT_2,
        ).decode()
    )


if __name__ == "__main__":
    main()
