"""E-005 known-payload retrieval through held-out classical cipher families."""

from __future__ import annotations

import argparse
import importlib.metadata
import platform
import random
import re
import sys
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
import orjson
import pycipher
import yaml
from jsonschema import Draft202012Validator
from sklearn.metrics import roc_auc_score

from manuscript_lab.control_calibration import _fit_model, _models
from manuscript_lab.feature_panel import extract_sequence_features
from manuscript_lab.ledger import git_provenance
from manuscript_lab.provenance import repository_root, sha256_file

START_MARKER = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK", re.I)
END_MARKER = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK", re.I)
ALLOWED_CIPHERS = {
    name: getattr(pycipher, name)
    for name in (
        "Affine",
        "Vigenere",
        "Autokey",
        "Beaufort",
        "Bifid",
        "ColTrans",
        "Railfence",
        "Enigma",
        "ADFGX",
    )
}


def normalize_gutenberg(raw: str) -> str:
    """Extract the framed ebook body and normalize to the common 25-letter alphabet."""
    start = START_MARKER.search(raw)
    end = END_MARKER.search(raw)
    if start is None or end is None or end.start() <= start.end():
        raise ValueError("Project Gutenberg start/end framing was not found")
    body_start = raw.find("\n", start.end())
    if body_start < 0 or body_start >= end.start():
        raise ValueError("Project Gutenberg start marker has no following body")
    letters = "".join(re.findall(r"[A-Za-z]", raw[body_start + 1 : end.start()])).upper()
    normalized = letters.replace("J", "I")
    if not normalized:
        raise ValueError("Normalized Project Gutenberg body is empty")
    return normalized


def fixed_groups(text: str, *, width: int) -> tuple[str, ...]:
    if width < 1 or len(text) % width:
        raise ValueError("Text length must be divisible by positive group width")
    return tuple(text[index : index + width] for index in range(0, len(text), width))


def document_segments(text: str, *, segment_characters: int, count: int) -> list[tuple[int, str]]:
    if count < 1 or len(text) < segment_characters * count:
        raise ValueError("Document is too short for fixed nonoverlapping segments")
    maximum_start = len(text) - segment_characters
    starts = (
        [round(index * maximum_start / (count - 1)) for index in range(count)] if count > 1 else [0]
    )
    if any(right - left < segment_characters for left, right in pairwise(starts)):
        raise ValueError("Configured document segments overlap")
    return [(start, text[start : start + segment_characters]) for start in starts]


def _cipher_parameters(spec: dict[str, Any]) -> dict[str, Any]:
    parameters = dict(spec["parameters"])
    if spec["class"] == "Enigma":
        for key in ("settings", "rotors", "ringstellung"):
            parameters[key] = tuple(parameters[key])
        parameters["steckers"] = [tuple(pair) for pair in parameters["steckers"]]
    return parameters


def cipher_object(spec: dict[str, Any]) -> Any:
    try:
        cipher_class = ALLOWED_CIPHERS[str(spec["class"])]
    except KeyError as exc:
        raise ValueError(f"Unapproved cipher class: {spec['class']}") from exc
    return cipher_class(**_cipher_parameters(spec))


def encipher_roundtrip(plaintext: str, spec: dict[str, Any]) -> tuple[str, bool]:
    ciphertext = cipher_object(spec).encipher(plaintext).upper()
    recovered = cipher_object(spec).decipher(ciphertext).upper()
    return ciphertext, recovered == plaintext


def pair_feature_vector(plain: np.ndarray, cipher: np.ndarray) -> np.ndarray:
    """Use bounded relative differences; omit either vector's absolute domain values."""
    denominator = np.abs(plain) + np.abs(cipher) + 1e-9
    return np.abs(plain - cipher) / denominator


def retrieval_metrics(score_matrix: np.ndarray) -> dict[str, float]:
    if score_matrix.ndim != 2 or score_matrix.shape[0] != score_matrix.shape[1]:
        raise ValueError("Retrieval matrix must be square with one correct diagonal pairing")
    candidate_count = score_matrix.shape[1]
    ranks = []
    for index, scores in enumerate(score_matrix):
        order = np.argsort(-scores, kind="stable")
        ranks.append(int(np.flatnonzero(order == index)[0]) + 1)
    mrr = float(np.mean([1.0 / rank for rank in ranks]))
    chance_mrr = float(sum(1.0 / rank for rank in range(1, candidate_count + 1)) / candidate_count)
    chance_top1 = 1.0 / candidate_count
    top1 = float(np.mean(np.asarray(ranks) == 1))
    return {
        "queries": candidate_count,
        "mean_reciprocal_rank": mrr,
        "normalized_mrr": (mrr - chance_mrr) / (1.0 - chance_mrr),
        "top1_accuracy": top1,
        "top1_lift_over_chance": top1 / chance_top1,
        "median_rank": float(np.median(ranks)),
        "chance_mrr": chance_mrr,
        "chance_top1": chance_top1,
    }


def _fit_pair_ensemble(
    matrix: np.ndarray,
    labels: np.ndarray,
    groups: np.ndarray,
    *,
    seed: int,
    workers: int,
    trees: int,
) -> list[Any]:
    models = _models(seed, workers=workers, trees=trees)
    for model in models:
        _fit_model(model, matrix, labels, groups)
    return models


def _predict_pair_ensemble(models: list[Any], matrix: np.ndarray) -> np.ndarray:
    return np.mean([model.predict_proba(matrix)[:, 1] for model in models], axis=0)


def _training_pairs(
    plain_matrix: np.ndarray,
    cipher_matrices: dict[str, np.ndarray],
    document_ids: np.ndarray,
    train: np.ndarray,
    train_families: list[str],
    *,
    negatives: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = random.Random(seed)
    rows = []
    labels = []
    groups = []
    for family in train_families:
        for index in train:
            candidates = [
                int(candidate)
                for candidate in train
                if document_ids[candidate] != document_ids[index]
            ]
            selected = rng.sample(candidates, negatives)
            for candidate, label in [(int(index), 1), *((value, 0) for value in selected)]:
                rows.append(
                    pair_feature_vector(plain_matrix[candidate], cipher_matrices[family][index])
                )
                labels.append(label)
                groups.append(f"{family}:{document_ids[index]}:{index}")
    return np.asarray(rows), np.asarray(labels), np.asarray(groups)


def run_benchmark(config_path: Path) -> dict[str, Any]:
    root = repository_root()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    params = config["parameters"]
    segment_characters = int(params["segment_characters"])
    group_characters = int(params["group_characters"])
    segments_per_document = int(params["segments_per_document"])
    documents = list(params["documents"])
    cipher_specs = list(params["cipher_families"])
    if {spec["class"] for spec in cipher_specs} != set(ALLOWED_CIPHERS):
        raise ValueError("Config must use the complete approved independent cipher suite")

    segments = []
    source_audit = []
    for document in documents:
        path = root / document["path"]
        raw = path.read_text(encoding="utf-8-sig")
        normalized = normalize_gutenberg(raw)
        selected = document_segments(
            normalized, segment_characters=segment_characters, count=segments_per_document
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

    feature_rows = [
        extract_sequence_features(fixed_groups(item["text"], width=group_characters))
        for item in segments
    ]
    feature_names = sorted(feature_rows[0])
    plain_matrix = np.asarray([[row[name] for name in feature_names] for row in feature_rows])
    document_ids = np.asarray([item["document_id"] for item in segments])
    folds = np.asarray([item["fold"] for item in segments])

    cipher_matrices: dict[str, np.ndarray] = {}
    roundtrip: dict[str, Any] = {}
    for spec in cipher_specs:
        family = str(spec["id"])
        rows = []
        exact = []
        lengths = []
        for item in segments:
            ciphertext, passed = encipher_roundtrip(item["text"], spec)
            exact.append(passed)
            lengths.append(len(ciphertext))
            features = extract_sequence_features(fixed_groups(ciphertext, width=group_characters))
            rows.append([features[name] for name in feature_names])
        cipher_matrices[family] = np.asarray(rows)
        roundtrip[family] = {
            "pairs": len(exact),
            "exact": int(sum(exact)),
            "fraction": float(np.mean(exact)),
            "ciphertext_character_range": [min(lengths), max(lengths)],
        }

    workers = int(params["workers"])
    trees = int(params["extra_trees_estimators"])
    seed = int(config["seed"])
    families = [str(spec["id"]) for spec in cipher_specs]
    family_results: dict[str, Any] = {}
    retrieval_cases: list[dict[str, Any]] = []
    for family_number, family in enumerate(families):
        fold_results = []
        for fold in sorted(set(folds)):
            train = np.flatnonzero(folds != fold)
            test = np.flatnonzero(folds == fold)
            train_x, train_y, train_groups = _training_pairs(
                plain_matrix,
                cipher_matrices,
                document_ids,
                train,
                [candidate for candidate in families if candidate != family],
                negatives=int(params["negatives_per_positive"]),
                seed=seed + family_number * 100 + int(fold),
            )
            models = _fit_pair_ensemble(
                train_x,
                train_y,
                train_groups,
                seed=seed + family_number * 100 + int(fold),
                workers=workers,
                trees=trees,
            )
            candidate_rows = np.asarray(
                [
                    pair_feature_vector(plain_matrix[candidate], cipher_matrices[family][query])
                    for query in test
                    for candidate in test
                ]
            )
            scores = _predict_pair_ensemble(models, candidate_rows).reshape(len(test), len(test))
            metrics = retrieval_metrics(scores)
            pair_labels = np.eye(len(test), dtype=int).ravel()
            metrics["pair_roc_auc"] = float(roc_auc_score(pair_labels, scores.ravel()))
            metrics["fold"] = int(fold)
            fold_results.append(metrics)
            retrieval_cases.append({"family": family, "fold": int(fold), "scores": scores})
        family_results[family] = {
            "folds": fold_results,
            "mean_normalized_mrr": float(
                np.mean([value["normalized_mrr"] for value in fold_results])
            ),
            "mean_top1_lift_over_chance": float(
                np.mean([value["top1_lift_over_chance"] for value in fold_results])
            ),
            "mean_pair_roc_auc": float(np.mean([value["pair_roc_auc"] for value in fold_results])),
        }
        print(f"known-payload retrieval: completed held-out family {family}", flush=True)

    observed = float(
        np.mean([retrieval_metrics(case["scores"])["normalized_mrr"] for case in retrieval_cases])
    )
    rng = random.Random(seed + 90_000)
    null_values = []
    for _iteration in range(int(params["permutation_iterations"])):
        values = []
        for case in retrieval_cases:
            scores = case["scores"]
            permutation = list(range(len(scores)))
            rng.shuffle(permutation)
            values.append(retrieval_metrics(scores[:, permutation])["normalized_mrr"])
        null_values.append(float(np.mean(values)))

    family_mrr = [value["mean_normalized_mrr"] for value in family_results.values()]
    family_lift = [value["mean_top1_lift_over_chance"] for value in family_results.values()]
    family_auc = [value["mean_pair_roc_auc"] for value in family_results.values()]
    roundtrip_fraction = sum(value["exact"] for value in roundtrip.values()) / sum(
        value["pairs"] for value in roundtrip.values()
    )
    permutation_p = (1 + sum(value >= observed for value in null_values)) / (len(null_values) + 1)
    aggregate = {
        "median_family_normalized_mrr": float(np.median(family_mrr)),
        "worst_family_normalized_mrr": float(min(family_mrr)),
        "median_family_top1_lift_over_chance": float(np.median(family_lift)),
        "worst_family_pair_roc_auc": float(min(family_auc)),
        "exact_roundtrip_fraction": float(roundtrip_fraction),
    }
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
    }
    passed = all(checks.values())
    return {
        "schema_version": "1.0",
        "experiment_id": config["experiment_id"],
        "hypothesis_id": config["hypothesis_id"],
        "run_finished_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source_audit": source_audit,
        "normalization": config["normalization"],
        "feature_panel": {
            "version": "relative-surface-sequence-pair-v1",
            "base_features": feature_names,
            "comparison": "absolute difference divided by summed absolute magnitudes",
        },
        "cipher_suite": {
            "implementation": "pycipher",
            "installed_version": importlib.metadata.version("pycipher"),
            "revision": params["pycipher_revision"],
            "families": cipher_specs,
            "roundtrip": roundtrip,
        },
        "family_results": family_results,
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
                "replicate with another implementation suite; no Voynich target comparison"
                if passed
                else "revise pair representation; no Voynich target comparison"
            ),
            "voynich_scored": False,
            "posterior_probability": None,
        },
        "provenance": {
            "source_manifest": config["source_manifest"],
            "source_manifest_sha256": sha256_file(root / config["source_manifest"]),
            "source_code_archive": params["source_code_archive"],
            "source_code_archive_sha256": sha256_file(root / params["source_code_archive"]),
            "config_path": config_path.relative_to(root).as_posix(),
            "config_sha256": sha256_file(config_path),
            "seed": seed,
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
        (repository_root() / "schemas" / "known-payload-retrieval-result.schema.json").read_bytes()
    )
    Draft202012Validator(schema).validate(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Immutable output already exists: {args.output}")
    result = run_benchmark(args.config.resolve())
    validate_result(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(
        orjson.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE)
    )


if __name__ == "__main__":
    main()
