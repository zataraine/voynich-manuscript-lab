"""Independent E-008 suite generator; deliberately does not import E-007 transforms."""

from __future__ import annotations

import argparse
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import orjson
import pycipher
import yaml

from manuscript_lab.known_payload_retrieval import normalize_gutenberg
from manuscript_lab.provenance import repository_root, sha256_file

LATIN25 = "ABCDEFGHIKLMNOPQRSTUVWXYZ"
KEYWORD_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _write_immutable(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"Immutable output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(orjson.dumps(value, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n")


def _source_starts(length: int, suites: int, maximum_segment: int, rng: random.Random) -> list[int]:
    if length < suites * maximum_segment:
        raise ValueError("Source is too short for nonoverlapping blind-suite segments")
    maximum_start = length - maximum_segment
    starts = [round(index * maximum_start / (suites - 1)) for index in range(suites)]
    rng.shuffle(starts)
    return starts


def _shuffle_pairs(stream: str, rng: random.Random) -> tuple[str, int]:
    pairs = [stream[index : index + 2] for index in range(0, len(stream), 2)]
    original = list(pairs)
    rng.shuffle(pairs)
    if pairs == original:
        pairs = pairs[1:] + pairs[:1]
    unchanged = sum(left == right for left, right in zip(original, pairs, strict=True))
    return "".join(pairs), unchanged


def _pycipher_encipher(text: str, square: str, keyword: str) -> tuple[str, str, bool]:
    polybius = pycipher.PolybiusSquare(key=square, size=5, chars="ADFGX")
    columnar = pycipher.ColTrans(keyword)
    intermediate = polybius.encipher(text).upper()
    ciphertext = columnar.encipher(intermediate).upper()
    recovered = polybius.decipher(columnar.decipher(ciphertext)).upper()
    return intermediate, ciphertext, recovered == text


def generate(config_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = repository_root()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if sha256_file(root / config["source_manifest"]) != config["source_manifest_sha256"]:
        raise ValueError("Frozen E-008 source manifest hash changed")
    predecessor = config["predecessor"]
    if sha256_file(root / predecessor["result"]) != predecessor["result_sha256"]:
        raise ValueError("Frozen E-007 result hash changed")

    parameters = config["parameters"]
    lengths = [int(value) for value in parameters["suite_segment_characters"]]
    documents = list(parameters["documents"])
    suite_count = len(lengths)
    if int(parameters["queries_per_suite"]) != len(documents):
        raise ValueError("Each suite must query every candidate exactly once")

    segment_rng = random.Random(int(parameters["segment_seed"]))
    parameter_rng = random.Random(int(parameters["generator_seed"]))
    broken_rng = random.Random(int(parameters["broken_mapping_seed"]))
    normalized: dict[str, str] = {}
    starts: dict[str, list[int]] = {}
    source_hashes: dict[str, str] = {}
    for document in documents:
        path = root / document["path"]
        text = normalize_gutenberg(path.read_text(encoding="utf-8-sig"))
        normalized[document["id"]] = text
        starts[document["id"]] = _source_starts(len(text), suite_count, max(lengths), segment_rng)
        source_hashes[document["id"]] = sha256_file(path)

    public_suites = []
    truth_queries = []
    all_candidate_truth = []
    source_audit = []
    roundtrips = []
    widths = [int(value) for value in parameters["widths"]]
    for suite_index, segment_length in enumerate(lengths):
        candidate_records = []
        candidate_truth = []
        for candidate_index, document in enumerate(documents):
            source_id = document["id"]
            offset = starts[source_id][suite_index]
            text = normalized[source_id][offset : offset + segment_length]
            candidate_id = f"s{suite_index:02d}-c{candidate_index:02d}"
            candidate_records.append({"candidate_id": candidate_id, "text": text})
            candidate_truth.append(
                {
                    "candidate_id": candidate_id,
                    "source_id": source_id,
                    "source_path": document["path"],
                    "source_sha256": source_hashes[source_id],
                    "offset": offset,
                }
            )
            source_audit.append(
                {
                    "suite_id": f"suite-{suite_index:02d}",
                    **candidate_truth[-1],
                    "characters": segment_length,
                }
            )
        all_candidate_truth.extend(
            {"suite_id": f"suite-{suite_index:02d}", **item} for item in candidate_truth
        )

        assignments = list(range(len(candidate_records)))
        parameter_rng.shuffle(assignments)
        public_queries = []
        for query_index, candidate_index in enumerate(assignments):
            width = widths[(suite_index + query_index) % len(widths)]
            square = "".join(parameter_rng.sample(LATIN25, len(LATIN25)))
            keyword = "".join(parameter_rng.sample(KEYWORD_ALPHABET, width))
            plaintext = candidate_records[candidate_index]["text"]
            intermediate, ciphertext, roundtrip = _pycipher_encipher(plaintext, square, keyword)
            broken_intermediate, unchanged_pairs = _shuffle_pairs(intermediate, broken_rng)
            broken_ciphertext = pycipher.ColTrans(keyword).encipher(broken_intermediate).upper()
            query_id = f"s{suite_index:02d}-q{query_index:02d}"
            public_queries.append(
                {
                    "query_id": query_id,
                    "ciphertext": ciphertext,
                    "broken_ciphertext": broken_ciphertext,
                }
            )
            order = sorted(range(width), key=lambda index: keyword[index])
            truth_queries.append(
                {
                    "suite_id": f"suite-{suite_index:02d}",
                    "query_id": query_id,
                    "correct_candidate_id": candidate_records[candidate_index]["candidate_id"],
                    "width": width,
                    "square": square,
                    "keyword": keyword,
                    "read_order": order,
                    "roundtrip": roundtrip,
                    "broken_unchanged_pair_positions": unchanged_pairs,
                    "pair_positions": len(plaintext),
                }
            )
            roundtrips.append(roundtrip)
        public_suites.append(
            {
                "suite_id": f"suite-{suite_index:02d}",
                "segment_characters": segment_length,
                "candidates": candidate_records,
                "queries": public_queries,
            }
        )

    public = {
        "schema_version": "1.0",
        "experiment_id": config["experiment_id"],
        "generated_at": datetime.now(UTC).isoformat(),
        "source_manifest": config["source_manifest"],
        "source_manifest_sha256": config["source_manifest_sha256"],
        "candidate_plaintext_supplied": True,
        "parameter_truth_included": False,
        "suites": public_suites,
    }
    public_path = root / config["separation"]["public_suite"]
    _write_immutable(public_path, public)
    public_hash = sha256_file(public_path)
    truth = {
        "schema_version": "1.0",
        "experiment_id": config["experiment_id"],
        "generated_at": datetime.now(UTC).isoformat(),
        "public_suite_sha256": public_hash,
        "generator_config": str(config_path.relative_to(root)),
        "generator_config_sha256": sha256_file(config_path),
        "generator_seeds": {
            "parameters": int(parameters["generator_seed"]),
            "segments": int(parameters["segment_seed"]),
            "broken_mapping": int(parameters["broken_mapping_seed"]),
        },
        "generator_implementation": "pycipher.PolybiusSquare + pycipher.ColTrans",
        "pycipher_commit": "8f1d7cf3cba4e12171e27d9ce723ad890194de19",
        "roundtrip_fraction": sum(roundtrips) / len(roundtrips),
        "source_audit": source_audit,
        "candidates": all_candidate_truth,
        "queries": truth_queries,
    }
    truth_path = root / config["separation"]["sealed_truth"]
    _write_immutable(truth_path, truth)
    return public, truth


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    public, truth = generate(args.config.resolve())
    print(
        orjson.dumps(
            {
                "suites": len(public["suites"]),
                "queries": len(truth["queries"]),
                "roundtrip_fraction": truth["roundtrip_fraction"],
            },
            option=orjson.OPT_INDENT_2,
        ).decode()
    )


if __name__ == "__main__":
    main()
