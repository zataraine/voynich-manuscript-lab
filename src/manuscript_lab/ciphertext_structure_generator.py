"""Independent E-009 ciphertext-only control generator."""

from __future__ import annotations

import argparse
import hashlib
import random
from collections import Counter, defaultdict
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

import orjson
import pycipher
import yaml

from manuscript_lab.known_payload_retrieval import normalize_gutenberg
from manuscript_lab.provenance import repository_root, sha256_file

LATIN25 = "ABCDEFGHIKLMNOPQRSTUVWXYZ"
CONTROL_FAMILIES = (
    "natural",
    "unigram_shuffle",
    "markov1",
    "block8_shuffle",
    "copy_mutate",
)


def _write_immutable(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"Immutable output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(orjson.dumps(value, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n")


def unigram_shuffle(text: str, rng: random.Random) -> str:
    values = list(text)
    rng.shuffle(values)
    return "".join(values)


def markov1(text: str, rng: random.Random) -> str:
    unigram = Counter(text)
    transitions: dict[str, Counter[str]] = defaultdict(Counter)
    for left, right in pairwise(text):
        transitions[left][right] += 1
    alphabet = sorted(unigram)
    unigram_weights = [unigram[symbol] for symbol in alphabet]
    output = [rng.choices(alphabet, weights=unigram_weights, k=1)[0]]
    while len(output) < len(text):
        choices = transitions.get(output[-1])
        if choices:
            symbols = sorted(choices)
            weights = [choices[symbol] for symbol in symbols]
        else:
            symbols = alphabet
            weights = unigram_weights
        output.append(rng.choices(symbols, weights=weights, k=1)[0])
    return "".join(output)


def block8_shuffle(text: str, rng: random.Random) -> str:
    blocks = [text[index : index + 8] for index in range(0, len(text), 8)]
    rng.shuffle(blocks)
    return "".join(blocks)


def copy_mutate(text: str, rng: random.Random, mutation_probability: float = 0.12) -> str:
    unigram = Counter(text)
    alphabet = sorted(unigram)
    weights = [unigram[symbol] for symbol in alphabet]
    output = rng.choices(alphabet, weights=weights, k=min(32, len(text)))
    while len(output) < len(text):
        span = min(rng.randint(3, 12), len(output), len(text) - len(output))
        start = rng.randrange(0, len(output) - span + 1)
        copied = output[start : start + span]
        for symbol in copied:
            if rng.random() < mutation_probability:
                symbol = rng.choices(alphabet, weights=weights, k=1)[0]
            output.append(symbol)
    return "".join(output)


def matched_controls(text: str, rng: random.Random) -> dict[str, str]:
    return {
        "natural": text,
        "unigram_shuffle": unigram_shuffle(text, rng),
        "markov1": markov1(text, rng),
        "block8_shuffle": block8_shuffle(text, rng),
        "copy_mutate": copy_mutate(text, rng),
    }


def _encipher(text: str, square: str, keyword: str) -> tuple[str, bool]:
    polybius = pycipher.PolybiusSquare(key=square, size=5, chars="ADFGX")
    columnar = pycipher.ColTrans(keyword)
    fractionated = polybius.encipher(text).upper()
    ciphertext = columnar.encipher(fractionated).upper()
    recovered = polybius.decipher(columnar.decipher(ciphertext)).upper()
    return ciphertext, recovered == text


def generate(config_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = repository_root()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if sha256_file(root / config["source_manifest"]) != config["source_manifest_sha256"]:
        raise ValueError("Frozen E-009 source manifest hash changed")
    predecessor = config["predecessor"]
    if sha256_file(root / predecessor["result"]) != predecessor["result_sha256"]:
        raise ValueError("Frozen E-008 result hash changed")
    scorer_path = root / config["separation"]["scorer_config"]
    if sha256_file(scorer_path) != config["separation"]["scorer_config_sha256"]:
        raise ValueError("Frozen E-009 scorer config hash changed")

    parameters = config["parameters"]
    if tuple(parameters["control_families"]) != CONTROL_FAMILIES:
        raise ValueError("Control family order must match the preregistration")
    segment_rng = random.Random(int(parameters["segment_seed"]))
    generator_rng = random.Random(int(parameters["generator_seed"]))
    control_rng = random.Random(int(parameters["control_seed"]))
    lengths = [int(value) for value in parameters["segment_characters"]]
    widths = [int(value) for value in parameters["widths"]]
    public_queries = []
    truth_queries = []
    base_index = 0
    for document in parameters["documents"]:
        path = root / document["path"]
        normalized = normalize_gutenberg(path.read_text(encoding="utf-8-sig"))
        maximum_start = len(normalized) - max(lengths)
        starts = [
            round(index * maximum_start / (len(lengths) - 1)) for index in range(len(lengths))
        ]
        segment_rng.shuffle(starts)
        for length_index, length in enumerate(lengths):
            offset = starts[length_index]
            natural = normalized[offset : offset + length]
            controls = matched_controls(natural, control_rng)
            width = widths[base_index % len(widths)]
            square = "".join(generator_rng.sample(LATIN25, len(LATIN25)))
            keyword = "".join(generator_rng.sample("ABCDEFGHIJKLMNOPQRSTUVWXYZ", width))
            order = sorted(range(width), key=lambda index: keyword[index])
            base_id = f"base-{base_index:02d}"
            family_queries = []
            for family, payload in controls.items():
                ciphertext, roundtrip = _encipher(payload, square, keyword)
                query_id = f"query-{len(truth_queries):03d}"
                family_queries.append({"query_id": query_id, "ciphertext": ciphertext})
                truth_queries.append(
                    {
                        "query_id": query_id,
                        "base_id": base_id,
                        "family": family,
                        "source_id": document["id"],
                        "source_path": document["path"],
                        "source_sha256": sha256_file(path),
                        "offset": offset,
                        "characters": length,
                        "plaintext_sha256": hashlib.sha256(payload.encode()).hexdigest(),
                        "width": width,
                        "square": square,
                        "keyword": keyword,
                        "read_order": order,
                        "roundtrip": roundtrip,
                    }
                )
            generator_rng.shuffle(family_queries)
            public_queries.extend(family_queries)
            base_index += 1
    generator_rng.shuffle(public_queries)
    public = {
        "schema_version": "1.0",
        "experiment_id": config["experiment_id"],
        "generated_at": datetime.now(UTC).isoformat(),
        "input_fields": ["query_id", "ciphertext"],
        "plaintext_included": False,
        "candidate_plaintext_included": False,
        "truth_included": False,
        "queries": public_queries,
    }
    public_path = root / config["separation"]["public_suite"]
    _write_immutable(public_path, public)
    truth = {
        "schema_version": "1.0",
        "experiment_id": config["experiment_id"],
        "generated_at": datetime.now(UTC).isoformat(),
        "public_suite_sha256": sha256_file(public_path),
        "generator_config_sha256": sha256_file(config_path),
        "generator_implementation": "pycipher.PolybiusSquare + pycipher.ColTrans",
        "pycipher_commit": "8f1d7cf3cba4e12171e27d9ce723ad890194de19",
        "roundtrip_fraction": sum(item["roundtrip"] for item in truth_queries) / len(truth_queries),
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
                "queries": len(public["queries"]),
                "roundtrip_fraction": truth["roundtrip_fraction"],
            },
            option=orjson.OPT_INDENT_2,
        ).decode()
    )


if __name__ == "__main__":
    main()
