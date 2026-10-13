from __future__ import annotations

from copy import deepcopy

import pytest
import yaml

from manuscript_lab.phase4_acceptance import (
    CONFIG_PATH,
    build_acceptance_report,
    load_acceptance_registry,
    parse_test_evidence,
    render_report,
)
from manuscript_lab.provenance import repository_root


def test_current_registry_covers_all_requirements_without_promoting_readiness():
    config = load_acceptance_registry(repository_root())
    evidence = {
        path: {"passed": 1, "failed": 0, "skipped": 0}
        for row in config["requirements"]
        for path in row["tests"]
    }
    report = build_acceptance_report(config, evidence, exit_code=0)
    assert len(report["requirements"]) == 10
    assert report["software_checks_passed"]
    assert not report["phase4_ready"]
    assert not report["joint_comparison_allowed"]
    assert all(row["readiness_status"] == "open" for row in report["requirements"])
    assert "Phase 4 ready: **no**" in render_report(report)


@pytest.mark.parametrize("failure", ["missing", "failed", "skipped", "exit"])
def test_missing_or_failed_evidence_never_passes(failure):
    config = load_acceptance_registry(repository_root())
    evidence = {
        path: {"passed": 1, "failed": 0, "skipped": 0}
        for row in config["requirements"]
        for path in row["tests"]
    }
    key = next(iter(evidence))
    if failure == "missing":
        del evidence[key]
    elif failure in {"failed", "skipped"}:
        evidence[key][failure] = 1
    report = build_acceptance_report(config, evidence, exit_code=1 if failure == "exit" else 0)
    assert not report["software_checks_passed"]
    assert not report["phase4_ready"]


def test_junit_counts_success_failure_skip_and_missing_files(tmp_path):
    path = tmp_path / "pytest.xml"
    path.write_text("""<testsuites><testsuite>
      <testcase classname="tests.test_a" name="ok"/>
      <testcase classname="tests.test_a" name="bad"><failure/></testcase>
      <testcase classname="tests.test_b" name="skip"><skipped/></testcase>
      <testcase classname="tests.test_unknown" name="unmapped"/>
    </testsuite></testsuites>""")
    result = parse_test_evidence(path, ["tests/test_a.py", "tests/test_b.py", "tests/test_c.py"])
    assert result["tests/test_a.py"] == {"passed": 1, "failed": 1, "skipped": 0}
    assert result["tests/test_b.py"]["skipped"] == 1
    assert result["tests/test_c.py"]["passed"] == 0
    assert (
        parse_test_evidence(tmp_path / "missing.xml", ["tests/test_a.py"])["tests/test_a.py"][
            "passed"
        ]
        == 0
    )


@pytest.mark.parametrize("failure", ["coverage", "open_work", "path", "target"])
def test_registry_cannot_hide_gaps_or_reference_arbitrary_paths(tmp_path, failure):
    config = deepcopy(load_acceptance_registry(repository_root()))
    if failure == "coverage":
        config["requirements"].pop()
    elif failure == "open_work":
        config["requirements"][0]["open_work"] = []
    elif failure == "path":
        config["requirements"][0]["tests"] = ["../secret.py"]
    else:
        config["target_access"] = "allowed"
    (tmp_path / CONFIG_PATH).parent.mkdir(parents=True)
    (tmp_path / CONFIG_PATH).write_text(yaml.safe_dump(config))
    # Give valid references their expected locations so the selected violation is exercised.
    (tmp_path / "tests").mkdir()
    for row in config["requirements"]:
        for relative in row["tests"]:
            if relative.startswith("tests/"):
                (tmp_path / relative).touch()
    with pytest.raises(ValueError):
        load_acceptance_registry(tmp_path)
