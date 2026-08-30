"""Bounded local-model review for control-calibration campaigns."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any

import orjson

from manuscript_lab.local_ai import LocalAIClient


def bounded_record(result: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    """Remove per-sample values and attach approved methodological context."""
    naibbe = {
        key: value for key, value in result["naibbe_positive_control"].items() if key != "samples"
    }
    targets = {
        witness: {key: value for key, value in summary.items() if key != "samples"}
        for witness, summary in result["voynich_targets"].items()
    }
    return {
        **result,
        "naibbe_positive_control": naibbe,
        "voynich_targets": targets,
        "full_result_sha256": hashlib.sha256(
            orjson.dumps(result, option=orjson.OPT_SORT_KEYS)
        ).hexdigest(),
        "review_semantics": [
            "Meaningful-similarity is a classifier score under this control corpus, "
            "not a posterior probability.",
            "Naibbe ciphertext is a known-payload positive control withheld from training.",
            "All chunks from a source document remain in one cross-validation fold.",
            "Voynich witnesses are out-of-distribution targets and are never training data.",
            "A failed interpretation gate forbids conclusions about meaning, language, "
            "cipher, or hoax.",
        ],
        "reference_context": packet["passages"],
        "reference_context_policy": packet["policy_note"],
    }


def _write(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"Immutable output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(orjson.dumps(value, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("qwen", "critic"))
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = orjson.loads(args.result.read_bytes())
    packet = orjson.loads(args.packet.read_bytes())
    record = bounded_record(result, packet)
    client = LocalAIClient()
    value = client.review_experiment(record) if args.operation == "qwen" else client.critic(record)
    _write(args.output, value)


if __name__ == "__main__":
    main()
