"""E-013 external calibration of the fixed E-012 eight-effect signature."""

from __future__ import annotations

import hashlib
import math
import multiprocessing
import platform
import random
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
import orjson
import yaml
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, brier_score_loss, roc_auc_score

from manuscript_lab.control_corpus import load_control_documents, normalize_tokens
from manuscript_lab.ledger import git_provenance
from manuscript_lab.mechanism_test import (
    PageSequence,
    _family_samples,
    evaluate_predictive_structure,
    generate_variant,
)
from manuscript_lab.provenance import repository_root, sha256_file

START_MARKER = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK", re.I)
END_MARKER = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK", re.I)

EFFECTS = (
    ("R1", "within_page_group_shuffle", "heldout_group_bigram_gain_bits"),
    ("R2", "within_page_group_shuffle", "heldout_local_copy_rate"),
    ("R3", "within_group_symbol_shuffle", "heldout_char_trigram_gain_bits"),
    ("R4", "within_group_symbol_shuffle", "heldout_local_copy_rate"),
    ("R5", "global_group_resample", "heldout_group_bigram_gain_bits"),
    ("R6", "global_group_resample", "heldout_local_copy_rate"),
    ("R7", "iid_symbol_length_matched", "heldout_char_trigram_gain_bits"),
    ("R8", "iid_symbol_length_matched", "heldout_local_copy_rate"),
)


@dataclass(frozen=True)
class Case:
    """One independently sourced control document/mechanism case."""

    case_id: str
    document_id: str
    cohort: str
    family: str
    label: int
    tokens: tuple[str, ...]
    source_ref: str
    source_sha256: str
    selected_start: int
    source_group_count: int
    fold: int | None
    roundtrip: bool


def _stable_seed(seed: int, *parts: str) -> int:
    digest = hashlib.sha256(":".join((str(seed), *parts)).encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _gutenberg_tokens(path: Path) -> tuple[str, ...]:
    raw = path.read_text(encoding="utf-8-sig")
    start = START_MARKER.search(raw)
    end = END_MARKER.search(raw)
    if start is None or end is None or end.start() <= start.end():
        raise ValueError(f"Project Gutenberg framing not found: {path}")
    body_start = raw.find("\n", start.end())
    if body_start < 0 or body_start >= end.start():
        raise ValueError(f"Project Gutenberg body not found: {path}")
    return normalize_tokens(raw[body_start + 1 : end.start()])


def _select_window(
    tokens: tuple[str, ...],
    *,
    document_id: str,
    seed: int,
    minimum: int,
    maximum: int,
    block_size: int,
) -> tuple[tuple[str, ...], int]:
    if len(tokens) < minimum:
        raise ValueError("document is shorter than the frozen minimum")
    count = min(len(tokens), maximum)
    count -= count % block_size
    maximum_start = len(tokens) - count
    start = _stable_seed(seed, document_id, "window") % (maximum_start + 1)
    return tokens[start : start + count], start


def _substitution(
    tokens: tuple[str, ...], rng: random.Random
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    alphabet = sorted({char for token in tokens for char in token})
    target = alphabet.copy()
    rng.shuffle(target)
    mapping = dict(zip(alphabet, target, strict=True))
    inverse = {value: key for key, value in mapping.items()}
    encoded = tuple("".join(mapping[char] for char in token) for token in tokens)
    decoded = tuple("".join(inverse[char] for char in token) for token in encoded)
    return encoded, decoded


def _polyalphabetic(
    tokens: tuple[str, ...], rng: random.Random, *, progressive: bool
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    alphabet = sorted({char for token in tokens for char in token})
    index = {char: offset for offset, char in enumerate(alphabet)}
    modulus = len(alphabet)
    period = 7
    key = [rng.randrange(modulus) for _ in range(period)]
    encoded: list[str] = []
    decoded: list[str] = []
    position = 0
    for token in tokens:
        cipher = []
        plain = []
        for char in token:
            shift = key[position % period] + (position if progressive else 0)
            value = alphabet[(index[char] + shift) % modulus]
            cipher.append(value)
            plain.append(alphabet[(index[value] - shift) % modulus])
            position += 1
        encoded.append("".join(cipher))
        decoded.append("".join(plain))
    return tuple(encoded), tuple(decoded)


def _homophonic(
    tokens: tuple[str, ...], rng: random.Random, *, base: int = 0xE000
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    alphabet = sorted({char for token in tokens for char in token})
    table: dict[str, tuple[str, ...]] = {}
    inverse: dict[str, str] = {}
    code = base
    for char in alphabet:
        values = tuple(chr(code + index) for index in range(3))
        code += 3
        table[char] = values
        inverse.update({value: char for value in values})
    encoded = tuple("".join(rng.choice(table[char]) for char in token) for token in tokens)
    decoded = tuple("".join(inverse[char] for char in token) for token in encoded)
    return encoded, decoded


def _nomenclator(
    tokens: tuple[str, ...], rng: random.Random
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    frequent = [token for token, _ in Counter(tokens).most_common(32)]
    codebook = {
        token: chr(0xF000 + index * 2) + chr(0xF001 + index * 2)
        for index, token in enumerate(frequent)
    }
    inverse_codebook = {value: key for key, value in codebook.items()}
    alphabet = sorted({char for token in tokens for char in token})
    table: dict[str, tuple[str, ...]] = {}
    inverse_chars: dict[str, str] = {}
    code = 0xE000
    for char in alphabet:
        values = tuple(chr(code + index) for index in range(3))
        code += 3
        table[char] = values
        inverse_chars.update({value: char for value in values})
    encoded = tuple(
        codebook[token] if token in codebook else "".join(rng.choice(table[char]) for char in token)
        for token in tokens
    )
    decoded = tuple(
        inverse_codebook[token]
        if token in inverse_codebook
        else "".join(inverse_chars[char] for char in token)
        for token in encoded
    )
    return encoded, decoded


def _weighted_choice(counter: Counter[str], rng: random.Random) -> str:
    values = sorted(counter)
    return rng.choices(values, weights=[counter[value] for value in values], k=1)[0]


def _character_markov(tokens: tuple[str, ...], rng: random.Random) -> tuple[str, ...]:
    unigram = Counter(char for token in tokens for char in token)
    starts = Counter(token[0] for token in tokens if token)
    transitions: dict[str, Counter[str]] = defaultdict(Counter)
    for token in tokens:
        for left, right in pairwise(token):
            transitions[left][right] += 1
    output = []
    for template in tokens:
        chars = [_weighted_choice(starts or unigram, rng)]
        while len(chars) < len(template):
            chars.append(_weighted_choice(transitions.get(chars[-1], unigram), rng))
        output.append("".join(chars))
    return tuple(output)


def _token_markov(tokens: tuple[str, ...], rng: random.Random) -> tuple[str, ...]:
    unigram = Counter(tokens)
    transitions: dict[str, Counter[str]] = defaultdict(Counter)
    for left, right in pairwise(tokens):
        transitions[left][right] += 1
    output = [_weighted_choice(unigram, rng)]
    while len(output) < len(tokens):
        output.append(_weighted_choice(transitions.get(output[-1], unigram), rng))
    return tuple(output)


def _positional_slot(tokens: tuple[str, ...], rng: random.Random) -> tuple[str, ...]:
    unigram = Counter(char for token in tokens for char in token)
    slots = [Counter() for _ in range(5)]
    for token in tokens:
        denominator = max(1, len(token) - 1)
        for index, char in enumerate(token):
            slots[round(4 * index / denominator)][char] += 1
    return tuple(
        "".join(
            _weighted_choice(slots[round(4 * index / max(1, len(token) - 1))] or unigram, rng)
            for index in range(len(token))
        )
        for token in tokens
    )


def _tokens_to_pages(tokens: tuple[str, ...], block_size: int, case_id: str) -> list[PageSequence]:
    if len(tokens) % block_size:
        raise ValueError("case token count must be divisible by block size")
    return [
        PageSequence(
            page_id=f"{case_id}:block:{index // block_size:03d}",
            currier=None,
            hand=None,
            section=None,
            groups=tokens[index : index + block_size],
            source_line_count=1,
            excluded_group_count=0,
        )
        for index in range(0, len(tokens), block_size)
    ]


def _copy_mutate(
    tokens: tuple[str, ...], rng_seed: int, mutation_rate: float, block_size: int
) -> tuple[str, ...]:
    pages = _tokens_to_pages(tokens, block_size, "generator")
    generated = generate_variant(
        pages,
        "copy_mutate_pseudotext",
        seed=rng_seed,
        mutation_rate=mutation_rate,
    )
    return tuple(group for page in generated for group in page.groups)


def transform_family(
    tokens: tuple[str, ...],
    family: str,
    *,
    seed: int,
    mutation_rates: dict[str, float],
    block_size: int,
) -> tuple[tuple[str, ...], bool]:
    """Apply one frozen payload transform or no-intended-payload generator."""
    rng = random.Random(seed)
    if family == "natural":
        return tokens, True
    if family == "monoalphabetic":
        encoded, decoded = _substitution(tokens, rng)
    elif family == "vigenere":
        encoded, decoded = _polyalphabetic(tokens, rng, progressive=False)
    elif family == "progressive_key":
        encoded, decoded = _polyalphabetic(tokens, rng, progressive=True)
    elif family == "homophonic":
        encoded, decoded = _homophonic(tokens, rng)
    elif family == "nomenclator_hybrid":
        encoded, decoded = _nomenclator(tokens, rng)
    elif family == "character_markov1":
        return _character_markov(tokens, rng), True
    elif family == "token_markov1":
        return _token_markov(tokens, rng), True
    elif family in mutation_rates:
        return _copy_mutate(tokens, seed, float(mutation_rates[family]), block_size), True
    elif family == "positional_slot":
        return _positional_slot(tokens, rng), True
    else:
        raise ValueError(f"unknown E-013 family: {family}")
    return encoded, decoded == tokens


def _manifest_documents(root: Path, manifest_path: Path) -> list[tuple[str, Path, str]]:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    documents = []
    for item in manifest["files"]:
        if item["media_type"] != "text/plain":
            continue
        path = root / item["path"]
        if sha256_file(path) != item["sha256"]:
            raise ValueError(f"source hash changed: {path}")
        documents.append((path.stem, path, item["sha256"]))
    return documents


def build_cases(config: dict[str, Any]) -> tuple[list[Case], dict[str, Any]]:
    """Construct development, independent, and external cases without target data."""
    root = repository_root()
    norm = config["normalization"]
    minimum = int(norm["minimum_groups"])
    maximum = int(norm["maximum_groups"])
    block_size = int(norm["groups_per_block"])
    seed = int(config["seed"])
    payload = tuple(config["parameters"]["payload_families"])
    no_payload = tuple(config["parameters"]["no_payload_families"])
    mutation_rates = dict(config["parameters"]["mutation_rates"])
    cases: list[Case] = []
    source_counts: dict[str, int] = {}

    cohorts = [("development", root / config["sources"]["development_manifest"])]
    cohorts.extend(
        ("independent", root / item["path"]) for item in config["sources"]["independent_manifests"]
    )
    for cohort, manifest in cohorts:
        documents = _manifest_documents(root, manifest)
        source_counts[str(manifest.relative_to(root))] = len(documents)
        folds = int(config["parameters"]["development_folds"])
        fold_map = {
            document_id: index % folds
            for index, (_order, document_id) in enumerate(
                sorted(
                    (_stable_seed(seed, document_id, "fold"), document_id)
                    for document_id, _path, _sha in documents
                )
            )
        }
        for document_id, path, source_sha in documents:
            raw_tokens = _gutenberg_tokens(path)
            selected, start = _select_window(
                raw_tokens,
                document_id=document_id,
                seed=seed,
                minimum=minimum,
                maximum=maximum,
                block_size=block_size,
            )
            fold = fold_map[document_id]
            for family in (*payload, *no_payload):
                transformed, roundtrip = transform_family(
                    selected,
                    family,
                    seed=_stable_seed(seed, document_id, family),
                    mutation_rates=mutation_rates,
                    block_size=block_size,
                )
                cases.append(
                    Case(
                        case_id=f"{cohort}:{document_id}:{family}",
                        document_id=f"{cohort}:{document_id}",
                        cohort=cohort,
                        family=family,
                        label=int(family in payload),
                        tokens=transformed,
                        source_ref=str(path.relative_to(root)),
                        source_sha256=source_sha,
                        selected_start=start,
                        source_group_count=len(raw_tokens),
                        fold=int(fold) if cohort == "development" else None,
                        roundtrip=roundtrip,
                    )
                )

    archive_path = root / config["sources"]["external_archive"]
    external_documents = load_control_documents(archive_path)
    excluded = Counter()
    included = Counter()
    for document in external_documents:
        if len(document.tokens) < minimum:
            excluded[document.family] += 1
            continue
        selected, start = _select_window(
            document.tokens,
            document_id=document.document_id,
            seed=seed,
            minimum=minimum,
            maximum=maximum,
            block_size=block_size,
        )
        family = {
            "meaningful": "external_meaningful",
            "human_gibberish": "external_human_gibberish",
            "naibbe_payload": "external_naibbe",
        }[document.family]
        cases.append(
            Case(
                case_id=f"external:{document.document_id}:{family}",
                document_id=f"external:{document.document_id}",
                cohort="external",
                family=family,
                label=int(document.family != "human_gibberish"),
                tokens=selected,
                source_ref=document.member,
                source_sha256=document.member_sha256,
                selected_start=start,
                source_group_count=len(document.tokens),
                fold=None,
                roundtrip=True,
            )
        )
        included[document.family] += 1
    audit = {
        "case_count": len(cases),
        "development_case_count": sum(case.cohort == "development" for case in cases),
        "independent_case_count": sum(case.cohort == "independent" for case in cases),
        "external_case_count": sum(case.cohort == "external" for case in cases),
        "source_document_counts": source_counts,
        "external_included": dict(included),
        "external_excluded_too_short": dict(excluded),
        "minimum_groups": minimum,
        "maximum_groups": maximum,
        "groups_per_block": block_size,
    }
    return cases, audit


def extract_case_signature(
    case: Case,
    *,
    null_families: tuple[str, ...],
    replicates: int,
    seed: int,
    block_size: int,
    train_fraction: float,
) -> dict[str, Any]:
    """Calculate the eight signed E-012 effects for one control case."""
    pages = _tokens_to_pages(case.tokens, block_size, case.case_id)
    train_count = max(1, min(len(pages) - 1, math.floor(len(pages) * train_fraction)))
    train = pages[:train_count]
    heldout = pages[train_count:]
    train_ids = [page.page_id for page in train]
    heldout_ids = [page.page_id for page in heldout]
    observed = evaluate_predictive_structure(train, heldout, alpha=0.1)
    metrics = sorted({metric for _, _, metric in EFFECTS})
    samples: dict[str, dict[str, list[float]]] = {}
    for family_index, family in enumerate(null_families):
        returned_family, values = _family_samples(
            pages,
            train_ids,
            heldout_ids,
            family,
            family_index,
            _stable_seed(seed, case.case_id, "null"),
            replicates,
            0.18,
            0.1,
            metrics,
        )
        if returned_family != family:
            raise ValueError("null family worker mismatch")
        samples[family] = values
    null_summary: dict[str, Any] = {}
    effects: dict[str, float] = {}
    for effect_id, family, metric in EFFECTS:
        values = samples[family][metric]
        mean = float(np.mean(values))
        standard_deviation = float(np.std(values, ddof=1))
        effect = observed[metric] - mean
        effects[effect_id] = effect
        null_summary.setdefault(family, {})[metric] = {
            "mean": mean,
            "standard_deviation": standard_deviation,
            "observed_minus_null": effect,
            "samples": values,
        }
    return {
        **{key: value for key, value in asdict(case).items() if key != "tokens"},
        "selected_group_count": len(case.tokens),
        "selected_sha256": hashlib.sha256("\u241f".join(case.tokens).encode()).hexdigest(),
        "train_block_count": len(train),
        "heldout_block_count": len(heldout),
        "effects": effects,
        "observed_metrics": observed,
        "null_summary": null_summary,
    }


def _fit_model(
    rows: list[dict[str, Any]], labels: np.ndarray, *, c: float, seed: int
) -> tuple[np.ndarray, np.ndarray, LogisticRegression]:
    matrix = np.asarray(
        [[row["effects"][effect_id] for effect_id, _, _ in EFFECTS] for row in rows]
    )
    median = np.median(matrix, axis=0)
    q25, q75 = np.percentile(matrix, [25, 75], axis=0)
    scale = q75 - q25
    scale[scale == 0] = 1.0
    model = LogisticRegression(
        C=c,
        class_weight="balanced",
        max_iter=2000,
        random_state=seed,
        solver="liblinear",
    )
    model.fit((matrix - median) / scale, labels)
    return median, scale, model


def _predict(
    rows: list[dict[str, Any]], median: np.ndarray, scale: np.ndarray, model: LogisticRegression
) -> np.ndarray:
    matrix = np.asarray(
        [[row["effects"][effect_id] for effect_id, _, _ in EFFECTS] for row in rows]
    )
    return model.predict_proba((matrix - median) / scale)[:, 1]


def _cross_family_predictions(
    rows: list[dict[str, Any]],
    family_labels: dict[str, int],
    *,
    folds: int,
    c: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    predictions: list[float] = []
    labels: list[int] = []
    families: list[str] = []
    for fold in range(folds):
        for family in sorted(family_labels):
            train = [row for row in rows if int(row["fold"]) != fold and row["family"] != family]
            test = [row for row in rows if int(row["fold"]) == fold and row["family"] == family]
            if not test:
                continue
            train_labels = np.asarray([family_labels[row["family"]] for row in train])
            median, scale, model = _fit_model(train, train_labels, c=c, seed=seed + fold)
            predictions.extend(_predict(test, median, scale, model).tolist())
            labels.extend([family_labels[family]] * len(test))
            families.extend([family] * len(test))
    return np.asarray(predictions), np.asarray(labels), families


def _classification_summary(
    scores: np.ndarray, labels: np.ndarray, families: list[str], threshold: float
) -> dict[str, Any]:
    predicted = (scores >= threshold).astype(int)
    recalls = {}
    for family in sorted(set(families)):
        indexes = np.asarray([value == family for value in families])
        recalls[family] = float(np.mean(predicted[indexes] == labels[indexes]))
    result = {
        "cases": len(labels),
        "balanced_accuracy": float(balanced_accuracy_score(labels, predicted)),
        "roc_auc": float(roc_auc_score(labels, scores)),
        "brier": float(brier_score_loss(labels, scores)),
        "family_recall": recalls,
        "worst_family_recall": min(recalls.values()),
    }
    return result


def evaluate_controls(
    config: dict[str, Any], rows: list[dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fit only on development controls and apply all frozen gates."""
    params = config["parameters"]
    payload = tuple(params["payload_families"])
    no_payload = tuple(params["no_payload_families"])
    family_labels = {family: int(family in payload) for family in (*payload, *no_payload)}
    development = [row for row in rows if row["cohort"] == "development"]
    independent = [row for row in rows if row["cohort"] == "independent"]
    external = [row for row in rows if row["cohort"] == "external"]
    threshold = float(params["probability_threshold"])
    c = float(params["logistic_c"])
    seed = int(config["seed"])
    folds = int(params["development_folds"])

    dev_scores, dev_labels, dev_families = _cross_family_predictions(
        development, family_labels, folds=folds, c=c, seed=seed
    )
    development_summary = _classification_summary(dev_scores, dev_labels, dev_families, threshold)
    rng = random.Random(_stable_seed(seed, "family-label-permutation"))
    families = sorted(family_labels)
    label_values = [family_labels[family] for family in families]
    null_values = []
    for _ in range(int(params["permutation_replicates"])):
        permuted = label_values.copy()
        rng.shuffle(permuted)
        mapping = dict(zip(families, permuted, strict=True))
        scores, labels, names = _cross_family_predictions(
            development, mapping, folds=folds, c=c, seed=seed
        )
        null_values.append(
            _classification_summary(scores, labels, names, threshold)["balanced_accuracy"]
        )
    permutation_p = (
        1 + sum(value >= development_summary["balanced_accuracy"] for value in null_values)
    ) / (len(null_values) + 1)

    train_labels = np.asarray([row["label"] for row in development])
    median, scale, model = _fit_model(development, train_labels, c=c, seed=seed)
    independent_scores = _predict(independent, median, scale, model)
    independent_labels = np.asarray([row["label"] for row in independent])
    independent_families = [str(row["family"]) for row in independent]
    independent_summary = _classification_summary(
        independent_scores, independent_labels, independent_families, threshold
    )

    external_scores = _predict(external, median, scale, model)
    external_records = [
        {"case_id": row["case_id"], "family": row["family"], "score": float(score)}
        for row, score in zip(external, external_scores, strict=True)
    ]
    by_family = {
        family: np.asarray([item["score"] for item in external_records if item["family"] == family])
        for family in ("external_meaningful", "external_human_gibberish", "external_naibbe")
    }
    external_summary = {
        "meaningful_cases": len(by_family["external_meaningful"]),
        "meaningful_recall": float(np.mean(by_family["external_meaningful"] >= threshold)),
        "human_gibberish_cases": len(by_family["external_human_gibberish"]),
        "human_gibberish_specificity": float(
            np.mean(by_family["external_human_gibberish"] < threshold)
        ),
        "naibbe_cases": len(by_family["external_naibbe"]),
        "naibbe_recall": float(np.mean(by_family["external_naibbe"] >= threshold)),
        "naibbe_median_payload_score": float(np.median(by_family["external_naibbe"])),
        "records": external_records,
    }
    gates_config = config["metrics"]["interpretation_gates"]
    gates = {
        "development_balanced_accuracy": development_summary["balanced_accuracy"]
        >= float(gates_config["minimum_development_balanced_accuracy"]),
        "worst_development_family_recall": development_summary["worst_family_recall"]
        >= float(gates_config["minimum_worst_development_family_recall"]),
        "family_label_permutation": permutation_p
        <= float(gates_config["maximum_family_label_permutation_p"]),
        "independent_balanced_accuracy": independent_summary["balanced_accuracy"]
        >= float(gates_config["minimum_independent_balanced_accuracy"]),
        "worst_independent_family_recall": independent_summary["worst_family_recall"]
        >= float(gates_config["minimum_worst_independent_family_recall"]),
        "external_meaningful_recall": external_summary["meaningful_recall"]
        >= float(gates_config["minimum_external_meaningful_recall"]),
        "external_human_gibberish_specificity": external_summary["human_gibberish_specificity"]
        >= float(gates_config["minimum_external_human_gibberish_specificity"]),
        "naibbe_payload_recall": external_summary["naibbe_recall"]
        >= float(gates_config["minimum_naibbe_payload_recall"]),
        "naibbe_median_payload_score": external_summary["naibbe_median_payload_score"]
        >= float(gates_config["minimum_naibbe_median_payload_score"]),
    }
    result = {
        "development": development_summary,
        "family_label_permutation_p": permutation_p,
        "family_label_permutation_null": null_values,
        "independent": independent_summary,
        "external": external_summary,
        "gates": gates,
    }
    model_record = {
        "effect_order": [effect_id for effect_id, _, _ in EFFECTS],
        "median": median.tolist(),
        "iqr": scale.tolist(),
        "coefficient": model.coef_[0].tolist(),
        "intercept": float(model.intercept_[0]),
        "probability_threshold": threshold,
        "training_case_ids": [row["case_id"] for row in development],
    }
    return result, model_record


def _preregistration_revision(root: Path, config_path: Path) -> str:
    result = subprocess.run(
        [
            "git",
            "log",
            "--diff-filter=A",
            "-1",
            "--format=%H",
            "--",
            str(config_path.relative_to(root)),
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _write_immutable(path: Path, payload: bytes) -> None:
    if path.exists():
        raise FileExistsError(f"immutable E-013 output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def run_campaign(config_path: Path) -> dict[str, Any]:
    """Run E-013 without loading or scoring any manuscript transcription."""
    started = time.monotonic()
    root = repository_root()
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config.get("experiment_id") != "E-013-external-signature-calibration":
        raise ValueError("not the frozen E-013 config")
    if (
        sha256_file(root / config["predecessor"]["result"])
        != config["predecessor"]["result_sha256"]
    ):
        raise ValueError("frozen E-012 result hash changed")
    source_specs = [
        (
            config["sources"]["development_manifest"],
            config["sources"]["development_manifest_sha256"],
        ),
        *[(item["path"], item["sha256"]) for item in config["sources"]["independent_manifests"]],
        (config["sources"]["external_manifest"], config["sources"]["external_manifest_sha256"]),
        (config["sources"]["external_archive"], config["sources"]["external_archive_sha256"]),
    ]
    for path, expected in source_specs:
        if sha256_file(root / path) != expected:
            raise ValueError(f"frozen E-013 source hash changed: {path}")
    provenance = git_provenance(root)
    if provenance["git_dirty"]:
        raise ValueError("E-013 calculation requires a clean committed worktree")

    cases, corpus_audit = build_cases(config)
    params = config["parameters"]
    workers = min(int(params["workers"]), len(cases))
    rows: list[dict[str, Any]] = []
    with ProcessPoolExecutor(
        max_workers=workers, mp_context=multiprocessing.get_context("spawn")
    ) as executor:
        futures = {
            executor.submit(
                extract_case_signature,
                case,
                null_families=tuple(params["null_families"]),
                replicates=int(params["null_replicates"]),
                seed=int(config["seed"]),
                block_size=int(config["normalization"]["groups_per_block"]),
                train_fraction=float(config["normalization"]["train_fraction"]),
            ): case.case_id
            for case in cases
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            rows.append(future.result())
            if completed % 20 == 0 or completed == len(cases):
                print(f"E-013 signatures {completed}/{len(cases)}", flush=True)
    rows.sort(key=lambda row: row["case_id"])
    evaluation, model_record = evaluate_controls(config, rows)
    controls = {
        "manuscript_transcription_absent": all(
            not row["source_ref"].startswith("data/raw/transcriptions/") for row in rows
        ),
        "all_payload_roundtrips_exact": all(row["roundtrip"] for row in rows),
        "case_ids_unique": len({row["case_id"] for row in rows}) == len(rows),
        "development_and_independent_documents_disjoint": not (
            {row["source_sha256"] for row in rows if row["cohort"] == "development"}
            & {row["source_sha256"] for row in rows if row["cohort"] == "independent"}
        ),
        "feature_shape_exact": all(
            set(row["effects"]) == {item[0] for item in EFFECTS} for row in rows
        ),
        "finite_features": all(
            math.isfinite(value) for row in rows for value in row["effects"].values()
        ),
    }
    gates = {"construction_controls": all(controls.values()), **evaluation["gates"]}
    destination = root / config["artifacts"]["root"]
    feature_path = root / config["artifacts"]["case_features"]
    model_path = root / config["artifacts"]["model"]
    result_path = root / config["artifacts"]["result"]
    destination.mkdir(parents=True, exist_ok=True)
    _write_immutable(
        feature_path,
        b"".join(orjson.dumps(row, option=orjson.OPT_SORT_KEYS) + b"\n" for row in rows),
    )
    _write_immutable(
        model_path,
        orjson.dumps(model_record, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n",
    )
    result = {
        "schema_version": "1.0",
        "experiment_id": config["experiment_id"],
        "hypothesis_id": config["hypothesis_id"],
        "question_id": config["question_id"],
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "pass" if all(gates.values()) else "fail",
        "target_application_permitted": all(gates.values()),
        "target_scored": False,
        "corpus_audit": corpus_audit,
        "controls": controls,
        "evaluation": evaluation,
        "gates": gates,
        "runtime_seconds": time.monotonic() - started,
        "provenance": {
            **provenance,
            "preregistration_git_commit": _preregistration_revision(root, config_path),
            "config_sha256": sha256_file(config_path),
            "protocol_sha256": sha256_file(root / config["protocol"]),
            "case_features_sha256": sha256_file(feature_path),
            "model_sha256": sha256_file(model_path),
            "seed": int(config["seed"]),
            "workers": int(params["workers"]),
            "device": "CPU",
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "uv_lock_sha256": sha256_file(root / "uv.lock"),
        },
        "interpretation": (
            "External calibration of a fixed low-level signature only; scores are not posterior "
            "probabilities of meaning, language, cipher, construction, or hoaxing."
        ),
    }
    _write_immutable(
        result_path,
        orjson.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n",
    )
    return result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/E-013-external-signature-calibration.yaml"),
    )
    args = parser.parse_args()
    result = run_campaign(args.config)
    print(
        orjson.dumps(
            {
                "status": result["status"],
                "target_application_permitted": result["target_application_permitted"],
                "corpus_audit": result["corpus_audit"],
                "controls": result["controls"],
                "evaluation": {
                    "development": result["evaluation"]["development"],
                    "family_label_permutation_p": result["evaluation"][
                        "family_label_permutation_p"
                    ],
                    "independent": result["evaluation"]["independent"],
                    "external": {
                        key: value
                        for key, value in result["evaluation"]["external"].items()
                        if key != "records"
                    },
                },
                "gates": result["gates"],
                "runtime_seconds": result["runtime_seconds"],
            },
            option=orjson.OPT_INDENT_2,
        ).decode()
    )


if __name__ == "__main__":
    main()
