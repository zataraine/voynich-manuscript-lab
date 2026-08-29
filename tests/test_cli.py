from __future__ import annotations

from pathlib import Path

import orjson
from typer.testing import CliRunner

from manuscript_lab.cli import app


def test_numeric_to_cryptanalysis_cli(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_bytes("ABAB e\u0301\r\n".encode())
    prefix = tmp_path / "sequence.v1"
    report = tmp_path / "report.json"
    runner = CliRunner()

    encoded = runner.invoke(
        app,
        [
            "numeric",
            "encode",
            str(source),
            "--output-prefix",
            str(prefix),
            "--mode",
            "grapheme",
        ],
    )
    assert encoded.exit_code == 0, encoded.output
    verified = runner.invoke(app, ["numeric", "verify", str(prefix)])
    assert verified.exit_code == 0, verified.output
    analyzed = runner.invoke(
        app,
        ["crypt", "analyze", str(prefix), "--max-lag", "4", "--output", str(report)],
    )
    assert analyzed.exit_code == 0, analyzed.output
    payload = orjson.loads(report.read_bytes())
    assert payload["length"] == 7
    assert "1" in payload["lag_coincidence"]
