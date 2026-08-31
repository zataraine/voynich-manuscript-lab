"""Truth-isolated scorer for the E-008 public ADFGX suite."""

from __future__ import annotations

import argparse
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import orjson
import yaml

from manuscript_lab.adfgx_stage_localization import (
    _encode_coordinates,
    _encode_plain,
    _permutations,
    best_combined_scores,
)
from manuscript_lab.ledger import git_provenance
from manuscript_lab.provenance import repository_root, sha256_file

FORBIDDEN_SCORER_KEYS = {
    "correct_candidate_id",
    "generator_seed",
    "keyword",
    "read_order",
    "sealed_truth",
    "square",
    "truth",
}


def _recursive_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_recursive_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_recursive_keys(item) for item in value), set())
    return set()


def score_public_suite(config_path: Path) -> dict[str, Any]:
    root = repository_root()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config.get("truth_inputs_permitted") is not False:
        raise ValueError("Blind scorer must explicitly forbid truth inputs")
    leaked_config = sorted(FORBIDDEN_SCORER_KEYS & _recursive_keys(config))
    if leaked_config:
        raise ValueError(f"Scorer config leaks forbidden keys: {leaked_config}")
    public_path = root / config["public_suite"]
    public = orjson.loads(public_path.read_bytes())
    leaked_public = sorted(FORBIDDEN_SCORER_KEYS & _recursive_keys(public))
    if leaked_public:
        raise ValueError(f"Public suite leaks forbidden keys: {leaked_public}")

    widths = [int(value) for value in config["hypothesized_widths"]]
    permutations = {width: _permutations(width) for width in widths}
    width_seconds = {str(width): 0.0 for width in widths}
    scored_suites = []
    for suite in public["suites"]:
        candidate_ids = [item["candidate_id"] for item in suite["candidates"]]
        plains = np.asarray([_encode_plain(item["text"]) for item in suite["candidates"]])
        query_scores = []
        for query in suite["queries"]:
            real = _encode_coordinates(query["ciphertext"])
            broken = _encode_coordinates(query["broken_ciphertext"])
            real_by_width = {}
            broken_by_width = {}
            for width in widths:
                started = time.perf_counter()
                real_by_width[str(width)] = best_combined_scores(
                    real, plains, permutations[width]
                ).tolist()
                broken_by_width[str(width)] = best_combined_scores(
                    broken, plains, permutations[width]
                ).tolist()
                width_seconds[str(width)] += time.perf_counter() - started
            query_scores.append(
                {
                    "query_id": query["query_id"],
                    "scores_by_width": real_by_width,
                    "broken_scores_by_width": broken_by_width,
                }
            )
        scored_suites.append(
            {
                "suite_id": suite["suite_id"],
                "candidate_ids": candidate_ids,
                "queries": query_scores,
            }
        )

    result = {
        "schema_version": "1.0",
        "scorer_id": config["scorer_id"],
        "generated_at": datetime.now(UTC).isoformat(),
        "truth_accessed": False,
        "public_suite": config["public_suite"],
        "public_suite_sha256": sha256_file(public_path),
        "scorer_config": str(config_path.relative_to(root)),
        "scorer_config_sha256": sha256_file(config_path),
        "hypothesized_widths": widths,
        "width_seconds_real_plus_broken": width_seconds,
        "suites": scored_suites,
        "provenance": git_provenance(root),
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
                "truth_accessed": result["truth_accessed"],
                "suites": len(result["suites"]),
                "width_seconds": result["width_seconds_real_plus_broken"],
            },
            option=orjson.OPT_INDENT_2,
        ).decode()
    )


if __name__ == "__main__":
    main()
