"""Fresh software evidence plus explicitly reviewed open readiness requirements."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import orjson
import yaml

from manuscript_lab.ledger import git_provenance
from manuscript_lab.provenance import repository_root, sha256_file

CONFIG_PATH = Path("config/research/phase4-acceptance-v1.yaml")
REQUIREMENTS = {
    "uncertainty",
    "learned_transfer",
    "vocabulary",
    "adjacency",
    "layout",
    "drift",
    "compression",
    "finite_samples",
    "missingness",
    "reproducibility",
}


def load_acceptance_registry(root: Path) -> dict[str, Any]:
    config = yaml.safe_load((root / CONFIG_PATH).read_text())
    if (
        set(config) != {"report_id", "target_access", "requirements"}
        or config["report_id"] != "phase4-acceptance-v1"
        or config["target_access"] != "forbidden"
        or len(config["requirements"]) != len(REQUIREMENTS)
        or {row["id"] for row in config["requirements"]} != REQUIREMENTS
    ):
        raise ValueError("acceptance registry identity or requirement coverage differs")
    for row in config["requirements"]:
        if (
            set(row) != {"id", "label", "tests", "open_work"}
            or not row["label"]
            or not row["tests"]
            or not row["open_work"]
            or any(not isinstance(item, str) or not item for item in row["open_work"])
        ):
            raise ValueError(
                "each current requirement needs evidence and explicit reviewed open work"
            )
        for relative in row["tests"]:
            path = Path(relative)
            if (
                path.is_absolute()
                or path.parent != Path("tests")
                or not path.name.startswith("test_")
                or path.suffix != ".py"
                or not (root / path).is_file()
                or (root / path).resolve().parent != (root / "tests").resolve()
            ):
                raise ValueError("acceptance evidence must name existing in-repository test files")
    return config


def parse_test_evidence(xml_path: Path, test_paths: list[str]) -> dict[str, Any]:
    """Missing, skipped, failed or unidentifiable test evidence cannot pass."""
    evidence = {path: {"passed": 0, "failed": 0, "skipped": 0} for path in test_paths}
    if not xml_path.is_file():
        return evidence
    tree = ElementTree.parse(xml_path)
    for case in tree.iter("testcase"):
        classname = case.get("classname", "")
        matched = [
            path
            for path in test_paths
            if classname.split(".")[-1] == Path(path).stem
            or classname.startswith(f"tests.{Path(path).stem}.")
        ]
        if len(matched) != 1:
            continue
        entry = evidence[matched[0]]
        if case.find("failure") is not None or case.find("error") is not None:
            entry["failed"] += 1
        elif case.find("skipped") is not None:
            entry["skipped"] += 1
        else:
            entry["passed"] += 1
    return evidence


def build_acceptance_report(config: dict[str, Any], evidence: dict[str, Any], *, exit_code: int):
    rows = []
    for row in config["requirements"]:
        counts = [
            evidence.get(path, {"passed": 0, "failed": 0, "skipped": 0}) for path in row["tests"]
        ]
        verified = exit_code == 0 and all(
            c["passed"] > 0 and not c["failed"] and not c["skipped"] for c in counts
        )
        rows.append(
            {
                **row,
                "software_status": "verified_subset" if verified else "not_verified",
                "readiness_status": "open",
                "test_evidence": {path: evidence.get(path) for path in row["tests"]},
            }
        )
    return {
        "report_id": config["report_id"],
        "requirements": rows,
        "software_checks_passed": all(row["software_status"] == "verified_subset" for row in rows),
        "phase4_ready": False,
        "target_access": "forbidden",
        "joint_comparison_allowed": False,
        "pytest_exit_code": exit_code,
        "interpretation": (
            "Verified subsets are software evidence only; reviewed open work "
            "is not automatically inferred from test outcomes."
        ),
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "# Phase 4 executable acceptance report",
        "",
        "Phase 4 ready: **no**. Target access and joint scientific comparison remain forbidden.",
        "",
        "Software checks passing does not close reviewed readiness gaps.",
        "",
        "| Requirement | Fresh software evidence | Readiness | Remaining work |",
        "|---|---|---|---|",
    ]
    for row in report["requirements"]:
        remaining = "; ".join(row["open_work"]).replace("|", "\\|")
        lines.append(f"| {row['label']} | {row['software_status']} | open | {remaining} |")
    lines.extend(
        [
            "",
            "Test results, source hashes, command and provenance are in report.json.",
            "pytest.log and pytest.xml retain the fresh test evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New directory under artifacts/")
    parser.add_argument(
        "--require-ready", action="store_true", help="Exit 2 while readiness remains open"
    )
    args = parser.parse_args()
    root = repository_root()
    output = args.output.resolve()
    if not output.is_relative_to(root / "artifacts") or output.exists():
        parser.error("choose a new output directory under artifacts/")
    config = load_acceptance_registry(root)
    test_paths = sorted({path for row in config["requirements"] for path in row["tests"]})
    command = [
        sys.executable,
        "-m",
        "pytest",
        *test_paths,
        "-q",
        f"--junitxml={output / 'pytest.xml'}",
    ]
    before = git_provenance(root)
    files = [
        *test_paths,
        str(CONFIG_PATH),
        "uv.lock",
        "docs/PHASE4_ACCEPTANCE.md",
        "docs/CONTROL_EXPANSION_ROADMAP.md",
    ]
    hashes = {path: sha256_file(root / path) for path in files}
    output.mkdir(parents=True)
    try:
        process = subprocess.run(command, cwd=root, capture_output=True, timeout=300, check=False)
        exit_code, log = process.returncode, process.stdout + process.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code, log = (
            124,
            (exc.stdout or b"") + (exc.stderr or b"") + b"\nAcceptance tests timed out.\n",
        )
    (output / "pytest.log").write_bytes(log)
    evidence_error = None
    try:
        evidence = parse_test_evidence(output / "pytest.xml", test_paths)
    except ElementTree.ParseError as exc:
        evidence, evidence_error, exit_code = {}, str(exc), 125
    report = build_acceptance_report(config, evidence, exit_code=exit_code)
    stable = before == git_provenance(root) and hashes == {
        path: sha256_file(root / path) for path in files
    }
    if not stable:
        report["software_checks_passed"] = False
        for row in report["requirements"]:
            row["software_status"] = "not_verified"
    report["provenance"] = {
        **before,
        "files_sha256": hashes,
        "working_tree_stable_during_checks": stable,
        "command": command,
        "device": "cpu",
        "created_at": datetime.now(UTC).isoformat(),
        "output_path": str(output.relative_to(root)),
        "evidence_parse_error": evidence_error,
    }
    for name in ("pytest.log", "pytest.xml"):
        if (output / name).is_file():
            report["provenance"][f"{name}_sha256"] = sha256_file(output / name)
    (output / "report.json").write_bytes(orjson.dumps(report, option=orjson.OPT_INDENT_2))
    (output / "report.md").write_text(render_report(report), encoding="utf-8")
    print(
        f"{len(report['requirements'])} requirements; "
        f"software checks passed: {report['software_checks_passed']}; Phase 4 ready: False"
    )
    if not report["software_checks_passed"]:
        raise SystemExit(1)
    if args.require_ready:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
