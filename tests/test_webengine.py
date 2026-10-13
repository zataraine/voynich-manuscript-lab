from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

import pytest
import yaml

from manuscript_lab.provenance import repository_root
from manuscript_lab.webengine import (
    ReferenceTools,
    WebEngineError,
    _data,
    build_reference_review_record,
)


class FakeSession:
    def __init__(self):
        self.requests = []

    async def call_tool(self, tool, arguments):
        self.requests.append((tool, arguments))
        if tool == "search":
            return SimpleNamespace(
                isError=False,
                content=[],
                structuredContent={
                    "items": [
                        {"url": "https://aclanthology.org/W11-1511/", "title": "Allowed paper"},
                        {"url": "https://voynichresearch.com/viewer.html", "title": "Excluded"},
                    ]
                },
            )
        return SimpleNamespace(isError=False, structuredContent={"ok": True}, content=[])


def _client():
    config = yaml.safe_load((repository_root() / "config/webengine.yaml").read_text())
    schemas = {
        "search": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
        "fetch": {
            "type": "object",
            "required": ["urls"],
            "properties": {
                "urls": {"type": "array", "items": {"type": "string"}},
                "max_chars": {"type": "integer"},
                "format": {"type": "string"},
                "render": {"type": "string"},
            },
        },
    }
    return ReferenceTools(
        FakeSession(), schemas, {"optional_fields": {}}, config, deadline=time.monotonic() + 120
    )


@pytest.mark.parametrize(
    "tool,arguments,kind",
    [
        ("drive", {}, "reference"),
        ("search", {"query": "x", "invented": True}, "reference"),
        ("search", {"query": "x", "limit": 100}, "reference"),
        ("search", {"query": "x"}, "voynichese"),
        ("fetch", {"urls": ["https://voynichresearch.com/viewer.html"]}, "reference"),
        ("fetch", {"urls": ["http://127.0.0.1/private"]}, "reference"),
        ("fetch", {"urls": ["https://aclanthology.org:443/W11-1511/"]}, "reference"),
        ("fetch", {"urls": ["https://aclanthology.org/W11-1511/"], "raw": True}, "reference"),
    ],
)
def test_request_policy_rejects_out_of_scope_or_unknown_arguments(tool, arguments, kind):
    client = _client()
    with pytest.raises(WebEngineError):
        asyncio.run(client.call(tool, arguments, content_kind=kind))
    assert client.session.requests == []


def test_defaults_are_bounded_and_packets_record_schema_and_response_identity():
    client = _client()
    packet = asyncio.run(
        client.call(
            "fetch", {"urls": ["https://aclanthology.org/W11-1511/"]}, content_kind="reference"
        )
    )
    args = client.session.requests[0][1]
    assert args["max_chars"] == 6000
    assert args["format"] == "text"
    assert args["render"] == "never"
    assert len(packet["response_sha256"]) == 64
    assert len(packet["tool_schema_sha256"]) == 64
    assert len(packet["capabilities_sha256"]) == 64


@pytest.mark.parametrize("expired", [True, False])
def test_call_and_time_budgets_stop_before_execution(expired):
    client = _client()
    if expired:
        client.deadline = time.monotonic() - 1
    else:
        client.calls = client.config["max_calls"]
    with pytest.raises(WebEngineError, match="budget exhausted"):
        asyncio.run(client.call("search", {"query": "entropy"}, content_kind="reference"))
    assert client.session.requests == []


def test_protocol_error_cannot_be_presented_as_reference_evidence():
    with pytest.raises(WebEngineError, match="tool error"):
        _data(SimpleNamespace(isError=True))


def test_large_response_is_rejected_instead_of_silently_truncated():
    client = _client()
    client.config["max_response_bytes"] = 1
    with pytest.raises(WebEngineError, match="retained-byte budget"):
        asyncio.run(client.call("search", {"query": "entropy"}, content_kind="reference"))


def test_search_results_are_filtered_before_becoming_model_reference_input():
    client = _client()
    packet = asyncio.run(client.call("search", {"query": "entropy"}, content_kind="reference"))
    assert packet["response"]["excluded_result_count"] == 1
    assert [item["title"] for item in packet["response"]["items"]] == ["Allowed paper"]
    assert packet["raw_response_sha256"] != packet["response_sha256"]


def test_multiple_mcp_text_blocks_are_decoded_individually():
    result = SimpleNamespace(
        isError=False,
        structuredContent=None,
        content=[
            SimpleNamespace(type="text", text='{"url":"https://aclanthology.org/a"}'),
            SimpleNamespace(type="text", text='{"url":"https://arxiv.org/b"}'),
        ],
    )
    assert len(_data(result)["items"]) == 2


def test_reference_review_has_auditable_current_project_context():
    packet = asyncio.run(_client().call("search", {"query": "entropy"}, content_kind="reference"))
    record = build_reference_review_record(
        packet, question="What can this reference support?", job_id="test-reference-intake"
    )
    assert record["record_kind"] == "reference-intake-review"
    assert record["reference_packets"] == [packet]
    assert [item["path"] for item in record["project_context"]["documents"]] == [
        "README.md",
        "docs/MECHANISM_COMPATIBILITY_ESTIMAND.md",
        "docs/PHASE4_ACCEPTANCE.md",
    ]
    assert all(len(item["sha256"]) == 64 for item in record["project_context"]["documents"])
    packet["new_field"] = "must not enter the frozen review input"
    assert "new_field" not in record["reference_packets"][0]
