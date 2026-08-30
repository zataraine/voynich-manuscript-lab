"""Internal auxiliary worker launched only through the exclusive GPU wrapper."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any

import orjson
from jsonschema import Draft202012Validator

from manuscript_lab.local_ai import LocalAIError, _request_json

ALLOWED_CONTENT = {"reference", "metadata", "research-note"}


def _require_allowed(request: dict[str, Any]) -> None:
    if request.get("content_kind") not in ALLOWED_CONTENT:
        raise LocalAIError("Auxiliary semantic operation rejected by content policy")


def _embed(request: dict[str, Any]) -> dict[str, Any]:
    _require_allowed(request)
    result = _request_json(
        f"{request['ollama_url']}/api/embed",
        {
            "model": request["embedding_model"],
            "input": request["texts"],
            "keep_alive": 0,
        },
        timeout=1200,
    )
    embeddings = result.get("embeddings")
    if not isinstance(embeddings, list) or len(embeddings) != len(request["texts"]):
        raise LocalAIError("Embedding service returned the wrong number of vectors")
    dimensions = {len(item) for item in embeddings if isinstance(item, list)}
    vector_count = sum(isinstance(item, list) for item in embeddings)
    if len(dimensions) != 1 or len(embeddings) != vector_count:
        raise LocalAIError("Embedding service returned inconsistent vectors")
    return {
        "model": request["embedding_model"],
        "content_kind": request["content_kind"],
        "dimensions": dimensions.pop(),
        "embeddings": embeddings,
    }


def _rerank(request: dict[str, Any]) -> dict[str, Any]:
    _require_allowed(request)
    import torch
    from sentence_transformers import CrossEncoder

    prompts = None
    default_prompt_name = None
    if request.get("instruction"):
        prompts = {"lab": request["instruction"]}
        default_prompt_name = "lab"
    model = CrossEncoder(
        request["reranker_path"],
        device="cuda" if torch.cuda.is_available() else "cpu",
        trust_remote_code=False,
        model_kwargs={"torch_dtype": torch.float16} if torch.cuda.is_available() else None,
        prompts=prompts,
        default_prompt_name=default_prompt_name,
    )
    ranked = model.rank(request["query"], request["documents"], show_progress_bar=False)
    results = [
        {"corpus_id": int(item["corpus_id"]), "score": float(item["score"])} for item in ranked
    ]
    return {
        "model_path": request["reranker_path"],
        "content_kind": request["content_kind"],
        "results": results,
    }


def _critic(request: dict[str, Any]) -> dict[str, Any]:
    record = request.get("record")
    if not isinstance(record, dict) or not isinstance(record.get("experiment_id"), str):
        raise LocalAIError("Critic review requires an experiment record")
    schema = request["review_schema"]
    payload = {
        "model": request["critic_model"],
        "messages": [
            {
                "role": "system",
                "content": request["system_prompt"],
            },
            {
                "role": "user",
                "content": request["user_prompt"].format(record_json=orjson.dumps(record).decode()),
            },
        ],
        "format": schema,
        "stream": False,
        "keep_alive": 0,
        "options": {"temperature": 0, "seed": 20260829},
    }
    result = _request_json(f"{request['ollama_url']}/api/chat", payload, timeout=1800)
    try:
        review = orjson.loads(result["message"]["content"])
    except (KeyError, TypeError, orjson.JSONDecodeError) as exc:
        raise LocalAIError("Critic returned invalid structured content") from exc
    Draft202012Validator(schema).validate(review)
    if review["experiment_id"] != record["experiment_id"]:
        raise LocalAIError("Critic returned the wrong experiment_id")
    return {
        "review": review,
        "provenance": {
            "provider": "local-ollama",
            "model": request["critic_model"],
            "input_sha256": hashlib.sha256(orjson.dumps(record)).hexdigest(),
            "prompt_hashes": request["prompt_hashes"],
            "prompt_eval_count": result.get("prompt_eval_count"),
            "eval_count": result.get("eval_count"),
        },
    }


def run(request: dict[str, Any]) -> dict[str, Any]:
    operation = request.get("operation")
    if operation == "embed":
        return _embed(request)
    if operation == "rerank":
        return _rerank(request)
    if operation == "critic":
        return _critic(request)
    raise LocalAIError(f"Unknown auxiliary operation: {operation!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request = orjson.loads(args.request.read_bytes())
    if not isinstance(request, dict):
        raise LocalAIError("Auxiliary request must be an object")
    result = run(request)
    args.output.write_bytes(orjson.dumps(result, option=orjson.OPT_INDENT_2))


if __name__ == "__main__":
    main()
