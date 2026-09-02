"""Command-line entry point for lab operations."""

from __future__ import annotations

import re
from datetime import timedelta
from pathlib import Path
from typing import Annotated

import orjson
import typer
from rich.console import Console
from rich.table import Table

from manuscript_lab.cryptanalysis.statistics import (
    index_of_coincidence,
    lag_coincidence,
    periodic_slice_ic,
    repeated_ngram_spacings,
    shannon_entropy,
)
from manuscript_lab.human_control_pilot import HumanPilotError, validate_pilot_submission
from manuscript_lab.human_controls import HumanControlError, validate_submission
from manuscript_lab.ivtff import IVTFFFormatError, parse_ivtff, summarize_page_metadata
from manuscript_lab.ledger import ExperimentLedger, LedgerError
from manuscript_lab.local_ai import LocalAIClient, LocalAIError, diagnose_local_ai
from manuscript_lab.manuscript_map import load_iiif_canvases, mapping_audit
from manuscript_lab.numeric import artifact_paths, verify_numeric_artifact, write_numeric_artifact
from manuscript_lab.provenance import (
    build_manifest,
    dump_manifest,
    load_manifest,
    repository_root,
    validate_manifest,
    verify_manifest_files,
)
from manuscript_lab.runtime import collect_diagnostics, write_diagnostics
from manuscript_lab.witness_alignment import (
    build_alignment,
    load_witness_corpus,
    write_alignment,
)

app = typer.Typer(no_args_is_help=True, help="Operate and verify the Manuscript Lab.")
manifest_app = typer.Typer(
    no_args_is_help=True,
    help="Build and verify immutable source manifests.",
)
app.add_typer(manifest_app, name="manifest")
numeric_app = typer.Typer(no_args_is_help=True, help="Create and verify reversible integer data.")
app.add_typer(numeric_app, name="numeric")
crypt_app = typer.Typer(no_args_is_help=True, help="Run assumption-light cipher diagnostics.")
app.add_typer(crypt_app, name="crypt")
ivtff_app = typer.Typer(no_args_is_help=True, help="Inspect IVTFF sources without normalization.")
app.add_typer(ivtff_app, name="ivtff")
local_ai_app = typer.Typer(
    no_args_is_help=True,
    help="Use the managed local review and reference-retrieval stack.",
)
app.add_typer(local_ai_app, name="local-ai")
experiment_app = typer.Typer(
    no_args_is_help=True,
    help="Register and supervise reproducible experiments.",
)
app.add_typer(experiment_app, name="experiment")
controls_app = typer.Typer(
    no_args_is_help=True,
    help="Validate prospective external control submissions.",
)
app.add_typer(controls_app, name="controls")
console = Console()
SOURCE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@controls_app.command("validate-submission")
def controls_validate_submission(
    metadata: Annotated[Path, typer.Argument(help="Submission metadata YAML under data/raw/.")],
    output: Annotated[
        Path | None,
        typer.Option(help="Optional JSON validation report; must not already exist."),
    ] = None,
) -> None:
    """Validate one long-form human pseudo-text submission without interpreting it."""
    if output is not None and output.exists():
        raise typer.BadParameter(f"Output already exists and is immutable: {output}")
    try:
        report = validate_submission(metadata)
    except (OSError, UnicodeError, KeyError, HumanControlError) as exc:
        console.print(f"[red]FAIL[/red] {exc}")
        raise typer.Exit(code=1) from exc
    encoded = orjson.dumps(report, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded)
        console.print(f"Created {output}")
    console.print(
        f"[green]PASS[/green] {report['submission_id']}: "
        f"{report['counts']['groups']} groups, {report['counts']['pages']} pages, exact SHA-256"
    )


@controls_app.command("validate-pilot-submission")
def controls_validate_pilot_submission(
    metadata: Annotated[Path, typer.Argument(help="Pilot metadata YAML under private raw data.")],
    output: Annotated[
        Path | None,
        typer.Option(help="Optional JSON validation report; must not already exist."),
    ] = None,
) -> None:
    """Validate a paired v2 human-production pilot submission without interpreting it."""
    if output is not None and output.exists():
        raise typer.BadParameter(f"Output already exists and is immutable: {output}")
    try:
        report = validate_pilot_submission(metadata)
    except (OSError, UnicodeError, KeyError, HumanPilotError) as exc:
        console.print(f"[red]FAIL[/red] {exc}")
        raise typer.Exit(code=1) from exc
    encoded = orjson.dumps(report, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded)
        console.print(f"Created {output}")
    console.print(
        f"[green]PASS PILOT[/green] {report['submission_id']}: "
        f"{report['counts']['groups']} groups across {report['sessions']} sessions; "
        "confirmatory and manuscript use remain prohibited"
    )


@app.command()
def doctor(
    strict: Annotated[
        bool,
        typer.Option(help="Exit non-zero unless every CPU/GPU/tool probe passes."),
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option(help="Write the complete machine-readable report to this JSON path."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the complete JSON report."),
    ] = False,
) -> None:
    """Probe required packages, command-line tools, CPU inference, and CUDA inference."""
    report = collect_diagnostics()
    if output is not None:
        write_diagnostics(report, output)

    if json_output:
        console.print(orjson.dumps(report, option=orjson.OPT_INDENT_2).decode())
    else:
        table = Table(title="Manuscript Lab diagnostics")
        table.add_column("Probe")
        table.add_column("Result")
        table.add_row("Python", report["platform"]["python"])
        table.add_row("WSL distribution", str(report["platform"]["wsl_distro"]))
        table.add_row("CPU inference", "pass" if report["cpu_inference"]["passed"] else "FAIL")
        table.add_row(
            "CPU language model",
            "pass" if report["cpu_language_model_inference"]["passed"] else "FAIL",
        )
        table.add_row(
            "Cryptanalysis solvers",
            "pass" if report["cryptanalysis"]["passed"] else "FAIL",
        )
        table.add_row(
            "Finite-state transducers",
            "pass" if report["finite_state"]["passed"] else "FAIL",
        )
        gpu = report["gpu"]
        table.add_row("CUDA", gpu.get("name", "not available"))
        table.add_row("GPU inference", "pass" if gpu.get("inference", {}).get("passed") else "FAIL")
        table.add_row(
            "GPU language model",
            "pass" if gpu.get("language_model_inference", {}).get("passed") else "FAIL",
        )
        table.add_row(
            "GPU 8-bit inference",
            "pass" if gpu.get("quantized_inference", {}).get("passed") else "FAIL",
        )
        missing_commands = [
            name for name, value in report["commands"].items() if not value["available"]
        ]
        failed_packages = [
            name for name, value in report["packages"].items() if not value["available"]
        ]
        command_result = (
            "pass" if not missing_commands else f"missing: {', '.join(missing_commands)}"
        )
        package_result = "pass" if not failed_packages else f"failed: {', '.join(failed_packages)}"
        table.add_row("External tools", command_result)
        table.add_row("Python imports", package_result)
        table.add_row("Overall", "PASS" if report["passed"] else "FAIL")
        console.print(table)
        if output is not None:
            console.print(f"Full report: {output}")

    if strict and not report["passed"]:
        raise typer.Exit(code=1)


@manifest_app.command("build")
def manifest_build(
    source_id: Annotated[str, typer.Argument(help="Neutral lowercase source slug.")],
    paths: Annotated[list[Path], typer.Argument(help="One or more files inside data/raw/.")],
    output: Annotated[
        Path | None,
        typer.Option(help="Defaults to data/manifests/SOURCE_ID.yaml."),
    ] = None,
    force: Annotated[bool, typer.Option(help="Replace an existing manifest path.")] = False,
) -> None:
    """Hash immutable raw files and create an editable source manifest."""
    if SOURCE_ID.fullmatch(source_id) is None:
        raise typer.BadParameter(
            "Use lowercase ASCII words separated by hyphens",
            param_hint="source_id",
        )
    root = repository_root()
    output = output or root / "data" / "manifests" / f"{source_id}.yaml"
    output = output if output.is_absolute() else root / output
    if output.exists() and not force:
        raise typer.BadParameter(f"Manifest already exists: {output}; pass --force to replace it")
    try:
        manifest = build_manifest(source_id, paths, root)
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(str(exc), param_hint="paths") from exc
    errors = validate_manifest(manifest, root)
    if errors:
        raise typer.BadParameter(
            "Generated manifest failed schema validation: " + "; ".join(errors)
        )
    dump_manifest(manifest, output)
    console.print(f"Created {output}")
    console.print("Complete acquisition, rights, and transcription metadata before analysis.")


@manifest_app.command("verify")
def manifest_verify(
    path: Annotated[Path, typer.Argument(help="Tracked YAML manifest to validate and re-hash.")],
) -> None:
    """Validate a manifest and verify every referenced file's size and SHA-256."""
    root = repository_root()
    path = path if path.is_absolute() else root / path
    try:
        manifest = load_manifest(path)
    except (OSError, ValueError) as exc:
        console.print(f"[red]Invalid manifest:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    errors = validate_manifest(manifest, root)
    if not errors:
        errors = verify_manifest_files(manifest, root)
    if errors:
        for error in errors:
            console.print(f"[red]FAIL[/red] {error}")
        raise typer.Exit(code=1)
    console.print(f"[green]PASS[/green] {path}: schema, sizes, and SHA-256 hashes verified")


@numeric_app.command("encode")
def numeric_encode(
    source: Annotated[Path, typer.Argument(help="Untouched source file to encode.")],
    output_prefix: Annotated[
        Path, typer.Option("--output-prefix", "-o", help="Prefix for .npy and .symbols.json.")
    ],
    mode: Annotated[
        str, typer.Option(help="Unit definition: byte, codepoint, or grapheme.")
    ] = "byte",
    codec: Annotated[str, typer.Option(help="Strict text codec for non-byte modes.")] = "utf-8",
    ordering: Annotated[str, typer.Option(help="Symbol-ID order: first or sorted.")] = "first",
    force: Annotated[bool, typer.Option(help="Replace both output files.")] = False,
) -> None:
    """Encode source bytes as reversible symbol IDs and write a provenance manifest."""
    try:
        artifact = write_numeric_artifact(
            source,
            output_prefix,
            mode=mode,  # type: ignore[arg-type]
            codec=codec,
            ordering=ordering,  # type: ignore[arg-type]
            force=force,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        console.print(f"[red]FAIL[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"Created {artifact.sequence_path}")
    console.print(f"Created {artifact.manifest_path}")


@numeric_app.command("verify")
def numeric_verify(
    output_prefix: Annotated[Path, typer.Argument(help="Prefix used by numeric encode.")],
) -> None:
    """Verify the array, symbol table, and reconstructed source hash."""
    try:
        manifest = verify_numeric_artifact(output_prefix)
    except (OSError, ValueError, KeyError) as exc:
        console.print(f"[red]FAIL[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(
        f"[green]PASS[/green] {output_prefix}: {manifest['sequence']['length']} units, "
        "exact source SHA-256 reconstruction"
    )


@crypt_app.command("analyze")
def crypt_analyze(
    output_prefix: Annotated[Path, typer.Argument(help="Verified numeric-artifact prefix.")],
    max_lag: Annotated[int, typer.Option(help="Largest coincidence lag.")] = 64,
    max_period: Annotated[int, typer.Option(help="Largest candidate period.")] = 32,
    ngram_width: Annotated[int, typer.Option(help="Repeated n-gram width.")] = 3,
    output: Annotated[Path | None, typer.Option(help="Optional JSON report path.")] = None,
) -> None:
    """Describe sequence structure without guessing a plaintext language."""
    import numpy as np

    try:
        manifest = verify_numeric_artifact(output_prefix)
        values = np.load(artifact_paths(output_prefix).sequence_path, allow_pickle=False).tolist()
        repeats = repeated_ngram_spacings(values, ngram_width)
        report = {
            "schema_version": "1.0",
            "numeric_artifact_sha256": manifest["sequence"]["sha256"],
            "length": len(values),
            "alphabet_size": len(manifest["symbols"]),
            "shannon_entropy_bits_per_unit": shannon_entropy(values),
            "index_of_coincidence": index_of_coincidence(values),
            "lag_coincidence": {
                str(lag): score for lag, score in lag_coincidence(values, max_lag).items()
            },
            "periodic_slice_ic": {
                str(period): score
                for period, score in periodic_slice_ic(values, max_period).items()
            },
            "repeated_ngrams": [
                {"units": list(gram), "spacings": spacings}
                for gram, spacings in sorted(repeats.items())
            ],
        }
    except (OSError, ValueError, KeyError) as exc:
        console.print(f"[red]FAIL[/red] {exc}")
        raise typer.Exit(code=1) from exc
    encoded = orjson.dumps(report, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded)
        console.print(f"Created {output}")
    else:
        console.print(encoded.decode())


@ivtff_app.command("summarize")
def ivtff_summarize(
    source: Annotated[Path, typer.Argument(help="Untouched IVTFF source file.")],
    output: Annotated[Path | None, typer.Option(help="Optional JSON report path.")] = None,
) -> None:
    """Count page metadata such as Currier stratum and scribal hand."""
    try:
        report = summarize_page_metadata(source)
    except (OSError, UnicodeError, ValueError) as exc:
        console.print(f"[red]FAIL[/red] {exc}")
        raise typer.Exit(code=1) from exc
    encoded = orjson.dumps(report, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded)
        console.print(f"Created {output}")
    else:
        console.print(encoded.decode())


@ivtff_app.command("validate")
def ivtff_validate(
    source: Annotated[Path, typer.Argument(help="Untouched IVTFF 2.x witness file.")],
) -> None:
    """Strictly parse a witness and verify byte-for-byte reconstruction."""
    try:
        document = parse_ivtff(source)
        if document.render_bytes() != source.read_bytes():
            raise IVTFFFormatError("physical-line reconstruction differs from source bytes")
    except (OSError, UnicodeError, IVTFFFormatError) as exc:
        console.print(f"[red]FAIL[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(
        f"[green]PASS[/green] {source}: {len(document.pages)} pages, "
        f"{len(document.loci)} loci, exact byte reconstruction"
    )


@ivtff_app.command("map-audit")
def ivtff_map_audit(
    source: Annotated[Path, typer.Argument(help="Untouched IVTFF 2.x witness file.")],
    iiif_manifest: Annotated[Path, typer.Argument(help="Canonical IIIF Presentation 3 manifest.")],
    output: Annotated[Path | None, typer.Option(help="Optional JSON audit path.")] = None,
) -> None:
    """Audit every locus against all matching ordered manuscript canvases."""
    try:
        document = parse_ivtff(source)
        canvases = load_iiif_canvases(iiif_manifest)
        report = mapping_audit(document, canvases, iiif_manifest)
    except (OSError, UnicodeError, ValueError, KeyError) as exc:
        console.print(f"[red]FAIL[/red] {exc}")
        raise typer.Exit(code=1) from exc
    encoded = orjson.dumps(report, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded)
        console.print(f"Created {output}")
    else:
        console.print(encoded.decode())
    if report["unlinked_locus_ids"]:
        raise typer.Exit(code=1)


@ivtff_app.command("align")
def ivtff_align(
    registry: Annotated[Path, typer.Argument(help="Tracked witness-lineage registry YAML.")],
    output: Annotated[
        Path, typer.Option("--output", "-o", help="New lossless lattice JSONL path.")
    ],
    audit_output: Annotated[
        Path, typer.Option("--audit-output", help="New alignment-audit JSON path.")
    ],
) -> None:
    """Build a deterministic witness-preserving locus alignment lattice."""
    try:
        corpus = load_witness_corpus(registry)
        result = build_alignment(corpus)
        write_alignment(result, output, audit_output)
    except (OSError, UnicodeError, ValueError, KeyError) as exc:
        console.print(f"[red]FAIL[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(
        f"[green]PASS[/green] {len(result.cells)} canonical loci, "
        f"{result.audit['output_reading_count']} preserved readings"
    )
    console.print(f"Created {output}")
    console.print(f"Created {audit_output}")


@local_ai_app.command("doctor")
def local_ai_doctor(
    live: Annotated[
        bool,
        typer.Option(help="Also run a tiny schema-constrained generation probe."),
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option(help="Optional JSON report path."),
    ] = None,
) -> None:
    """Verify the pinned worker, inventory, endpoint, and content policy."""
    try:
        report = diagnose_local_ai(live=live)
    except (OSError, ValueError, KeyError, LocalAIError) as exc:
        console.print(f"[red]FAIL[/red] {exc}")
        raise typer.Exit(code=1) from exc
    encoded = orjson.dumps(report, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded)
    console.print(
        f"[{'green' if report['passed'] else 'red'}]"
        f"{'PASS' if report['passed'] else 'FAIL'}[/] local-AI stack"
    )
    if output is not None:
        console.print(f"Full report: {output}")
    if not report["passed"]:
        raise typer.Exit(code=1)


@local_ai_app.command("review")
def local_ai_review(
    record: Annotated[Path, typer.Argument(help="Experiment result JSON to review.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Review output JSON.")],
) -> None:
    """Ask Qwen for a strict, routine scientific review."""
    if output.exists():
        raise typer.BadParameter(f"Output already exists and is immutable: {output}")
    try:
        value = orjson.loads(record.read_bytes())
        if not isinstance(value, dict):
            raise LocalAIError("Experiment record must be a JSON object")
        result = LocalAIClient().review_experiment(value)
    except (OSError, orjson.JSONDecodeError, LocalAIError) as exc:
        console.print(f"[red]FAIL[/red] {exc}")
        raise typer.Exit(code=1) from exc
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(orjson.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE))
    console.print(f"Created {output}")


@local_ai_app.command("embed-reference")
def local_ai_embed_reference(
    source: Annotated[Path, typer.Argument(help="JSON array of reference passages.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Embedding output JSON.")],
    content_kind: Annotated[
        str,
        typer.Option(help="Allowed kind: reference, metadata, or research-note."),
    ] = "reference",
) -> None:
    """Embed non-manuscript reference text under exclusive GPU management."""
    if output.exists():
        raise typer.BadParameter(f"Output already exists and is immutable: {output}")
    try:
        texts = orjson.loads(source.read_bytes())
        if not isinstance(texts, list) or not all(isinstance(item, str) for item in texts):
            raise LocalAIError("Embedding input must be a JSON array of strings")
        result = LocalAIClient().embed_reference(texts, content_kind=content_kind)  # type: ignore[arg-type]
    except (OSError, orjson.JSONDecodeError, LocalAIError) as exc:
        console.print(f"[red]FAIL[/red] {exc}")
        raise typer.Exit(code=1) from exc
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(orjson.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE))
    console.print(f"Created {output}")


@local_ai_app.command("rerank-reference")
def local_ai_rerank_reference(
    source: Annotated[
        Path,
        typer.Argument(help="JSON object with query, documents, and optional instruction."),
    ],
    output: Annotated[Path, typer.Option("--output", "-o", help="Ranking output JSON.")],
    content_kind: Annotated[
        str,
        typer.Option(help="Allowed kind: reference, metadata, or research-note."),
    ] = "reference",
) -> None:
    """Rerank non-manuscript reference passages under exclusive GPU management."""
    if output.exists():
        raise typer.BadParameter(f"Output already exists and is immutable: {output}")
    try:
        request = orjson.loads(source.read_bytes())
        if not isinstance(request, dict):
            raise LocalAIError("Reranking input must be a JSON object")
        result = LocalAIClient().rerank_reference(
            request["query"],
            request["documents"],
            content_kind=content_kind,  # type: ignore[arg-type]
            instruction=request.get("instruction"),
        )
    except (OSError, KeyError, TypeError, orjson.JSONDecodeError, LocalAIError) as exc:
        console.print(f"[red]FAIL[/red] {exc}")
        raise typer.Exit(code=1) from exc
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(orjson.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE))
    console.print(f"Created {output}")


@experiment_app.command("init")
def experiment_init(
    database: Annotated[
        Path | None,
        typer.Option(help="DuckDB path; defaults under artifacts/state/."),
    ] = None,
) -> None:
    """Initialize the experiment ledger idempotently."""
    ledger = ExperimentLedger(database)
    ledger.initialize()
    console.print(f"Initialized {ledger.path}")


@experiment_app.command("register")
def experiment_register(
    config: Annotated[Path, typer.Argument(help="Preregistered experiment YAML.")],
    database: Annotated[Path | None, typer.Option(help="Optional DuckDB path.")] = None,
) -> None:
    """Register a schema-valid PENDING experiment with source and Git provenance."""
    try:
        record = ExperimentLedger(database).register_file(config)
    except (OSError, ValueError, KeyError, LedgerError) as exc:
        console.print(f"[red]FAIL[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"Registered {record['experiment_id']} as {record['status']}")


@experiment_app.command("show")
def experiment_show(
    experiment_id: Annotated[str, typer.Argument(help="Experiment identifier.")],
    database: Annotated[Path | None, typer.Option(help="Optional DuckDB path.")] = None,
) -> None:
    """Print one complete experiment record as JSON."""
    try:
        record = ExperimentLedger(database).get(experiment_id)
    except LedgerError as exc:
        console.print(f"[red]FAIL[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(orjson.dumps(record, option=orjson.OPT_INDENT_2).decode())


@experiment_app.command("list")
def experiment_list(
    status: Annotated[str | None, typer.Option(help="Optional exact status filter.")] = None,
    database: Annotated[Path | None, typer.Option(help="Optional DuckDB path.")] = None,
) -> None:
    """List experiment state without loading result payloads."""
    try:
        rows = ExperimentLedger(database).list(status=status)
    except LedgerError as exc:
        console.print(f"[red]FAIL[/red] {exc}")
        raise typer.Exit(code=1) from exc
    table = Table(title="Experiment ledger")
    table.add_column("Experiment")
    table.add_column("Status")
    table.add_column("Updated")
    table.add_column("Lease")
    for row in rows:
        table.add_row(
            row["experiment_id"], row["status"], row["updated_at"], row["lease_owner"] or ""
        )
    console.print(table)


@experiment_app.command("transition")
def experiment_transition(
    experiment_id: Annotated[str, typer.Argument(help="Experiment identifier.")],
    status: Annotated[str, typer.Argument(help="Validated destination status.")],
    note: Annotated[str, typer.Option(help="Reason recorded in the event chain.")] = "",
    database: Annotated[Path | None, typer.Option(help="Optional DuckDB path.")] = None,
) -> None:
    """Apply one explicit, validated state transition."""
    try:
        record = ExperimentLedger(database).transition(
            experiment_id,
            status,
            details={"note": note} if note else {},
        )
    except LedgerError as exc:
        console.print(f"[red]FAIL[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"{experiment_id}: {record['status']}")


@experiment_app.command("verify")
def experiment_verify(
    database: Annotated[Path | None, typer.Option(help="Optional DuckDB path.")] = None,
) -> None:
    """Verify every link in the append-only event hash chain."""
    report = ExperimentLedger(database).verify_event_chain()
    console.print(
        f"[{'green' if report['passed'] else 'red'}]"
        f"{'PASS' if report['passed'] else 'FAIL'}[/] {report['event_count']} ledger events"
    )
    for error in report["errors"]:
        console.print(f"[red]{error}[/red]")
    if not report["passed"]:
        raise typer.Exit(code=1)


@experiment_app.command("stale")
def experiment_stale(
    hours: Annotated[float, typer.Option(help="Heartbeat age threshold in hours.")] = 6.0,
    database: Annotated[Path | None, typer.Option(help="Optional DuckDB path.")] = None,
) -> None:
    """Report stale RUNNING leases without mutating them."""
    if hours <= 0:
        raise typer.BadParameter("hours must be positive")
    rows = ExperimentLedger(database).stale(older_than=timedelta(hours=hours))
    console.print(orjson.dumps(rows, option=orjson.OPT_INDENT_2).decode())


@experiment_app.command(
    "execute",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def experiment_execute(
    context: typer.Context,
    experiment_id: Annotated[str, typer.Argument(help="Registered PENDING/REPLICATE experiment.")],
    database: Annotated[Path | None, typer.Option(help="Optional DuckDB path.")] = None,
    heartbeat_seconds: Annotated[
        float,
        typer.Option(help="Seconds between durable heartbeats."),
    ] = 60.0,
) -> None:
    """Execute argv after `--`, with logging, heartbeats, and terminal state."""
    from manuscript_lab.experiment_runner import execute_experiment

    if heartbeat_seconds <= 0:
        raise typer.BadParameter("heartbeat-seconds must be positive")
    command = list(context.args)
    try:
        return_code = execute_experiment(
            experiment_id,
            command,
            ledger_path=database,
            heartbeat_seconds=heartbeat_seconds,
        )
    except LedgerError as exc:
        console.print(f"[red]FAIL[/red] {exc}")
        raise typer.Exit(code=1) from exc
    if return_code != 0:
        raise typer.Exit(code=return_code)


if __name__ == "__main__":
    app()
