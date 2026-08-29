"""Offline CPU/GPU inference diagnostics."""

from __future__ import annotations

import importlib
import importlib.metadata
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REQUIRED_COMMANDS = (
    "cbc",
    "dot",
    "fplll",
    "fstcompile",
    "fstcompose",
    "gap",
    "git",
    "git-lfs",
    "glpsol",
    "gp",
    "tesseract",
    "pdftoppm",
    "pdfinfo",
    "ffmpeg",
    "convert",
    "jq",
    "minizinc",
    "openssl",
    "snakemake",
    "sqlite3",
)

IMPORT_PROBES = {
    "Crypto": "pycryptodome",
    "accelerate": "accelerate",
    "bitsandbytes": "bitsandbytes",
    "cv2": "opencv-python-headless",
    "cryptography": "cryptography",
    "datasets": "datasets",
    "deap": "deap",
    "duckdb": "duckdb",
    "gmpy2": "gmpy2",
    "numpy": "numpy",
    "ortools": "ortools",
    "pandas": "pandas",
    "PIL": "pillow",
    "polars": "polars",
    "pynini": "pynini",
    "pydivsufsort": "pydivsufsort",
    "regex": "regex",
    "scipy": "scipy",
    "skimage": "scikit-image",
    "sklearn": "scikit-learn",
    "simanneal": "simanneal",
    "snakemake": "snakemake",
    "torch": "torch",
    "torchvision": "torchvision",
    "transformers": "transformers",
    "z3": "z3-solver",
}


def _command_version(command: str) -> dict[str, Any]:
    path = shutil.which(command)
    if path is None:
        return {"available": False, "path": None, "version": None}
    version_args = [command, "--version"]
    if command in {"fstcompile", "fstcompose"}:
        version_args = [command, "--help"]
    elif command == "dot":
        version_args = [command, "-V"]
    elif command == "pdftoppm" or command == "pdfinfo":
        version_args = [command, "-v"]
    elif command == "openssl":
        version_args = [command, "version"]
    elif command == "gap":
        version_args = [command, "-q", "-c", "Print(GAPInfo.Version);QUIT;"]
    try:
        completed = subprocess.run(
            version_args,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        text = (completed.stdout or completed.stderr).splitlines()
        version = text[0].strip() if text else "unknown"
    except (OSError, subprocess.TimeoutExpired) as exc:
        version = f"error: {exc}"
    return {"available": True, "path": path, "version": version}


def _package_probe(import_name: str, distribution: str) -> dict[str, Any]:
    try:
        importlib.import_module(import_name)
        version = importlib.metadata.version(distribution)
        return {"available": True, "version": version, "error": None}
    except Exception as exc:  # diagnostic must report every import failure
        return {"available": False, "version": None, "error": f"{type(exc).__name__}: {exc}"}


def _inference_probe(device: str) -> dict[str, Any]:
    import torch

    started = time.perf_counter()
    torch.manual_seed(20260829)
    generator = torch.Generator(device=device).manual_seed(20260829)
    model = torch.nn.Sequential(
        torch.nn.Linear(64, 128),
        torch.nn.GELU(),
        torch.nn.Linear(128, 16),
    ).to(device)
    inputs = torch.randn((32, 64), generator=generator, device=device)
    with torch.inference_mode():
        output = model(inputs)
    if device == "cuda":
        torch.cuda.synchronize()
    return {
        "passed": bool(torch.isfinite(output).all().item()),
        "shape": list(output.shape),
        "checksum": round(float(output.float().sum().cpu()), 6),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
    }


def _language_model_probe(device: str) -> dict[str, Any]:
    """Run a tiny, randomly initialized masked-LM forward pass without network I/O."""
    import torch
    from transformers import BertConfig, BertForMaskedLM

    torch.manual_seed(20260829)
    config = BertConfig(
        vocab_size=128,
        hidden_size=32,
        intermediate_size=64,
        num_hidden_layers=1,
        num_attention_heads=4,
        max_position_embeddings=32,
    )
    model = BertForMaskedLM(config).to(device).eval()
    input_ids = torch.tensor([[1, 5, 9, 2, 0, 0]], dtype=torch.long, device=device)
    started = time.perf_counter()
    with torch.inference_mode():
        logits = model(input_ids=input_ids).logits
    if device == "cuda":
        torch.cuda.synchronize()
    return {
        "passed": bool(torch.isfinite(logits).all().item()),
        "shape": list(logits.shape),
        "checksum": round(float(logits.float().sum().cpu()), 6),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "offline_random_weights": True,
    }


def _quantized_gpu_probe() -> dict[str, Any]:
    """Exercise the bitsandbytes CUDA 8-bit linear inference path."""
    import bitsandbytes as bnb
    import torch

    torch.manual_seed(20260829)
    layer = bnb.nn.Linear8bitLt(32, 8, has_fp16_weights=False).cuda()
    inputs = torch.randn(4, 32, device="cuda", dtype=torch.float16)
    started = time.perf_counter()
    with torch.inference_mode():
        output = layer(inputs)
    torch.cuda.synchronize()
    return {
        "passed": bool(torch.isfinite(output).all().item()),
        "shape": list(output.shape),
        "checksum": round(float(output.float().sum().cpu()), 6),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "bitsandbytes_version": bnb.__version__,
    }


def _cryptanalysis_probe() -> dict[str, Any]:
    """Exercise constraint solvers and a standard cryptographic primitive offline."""
    from Crypto.Cipher import AES
    from ortools.sat.python import cp_model
    from z3 import Distinct, Ints, Solver, sat

    left, right = Ints("left right")
    z3_solver = Solver()
    z3_solver.add(left >= 0, right >= 0, left < 3, right < 3, Distinct(left, right))
    z3_solver.add(left + right == 2)
    z3_passed = z3_solver.check() == sat

    model = cp_model.CpModel()
    x = model.new_int_var(0, 2, "x")
    y = model.new_int_var(0, 2, "y")
    model.add(x != y)
    model.add(x + y == 2)
    cp_status = cp_model.CpSolver().solve(model)
    cp_passed = cp_status in (cp_model.FEASIBLE, cp_model.OPTIMAL)

    key = bytes(range(16))
    plain = b"offline-probe-16"
    cipher = AES.new(key, AES.MODE_ECB)
    crypto_passed = cipher.decrypt(cipher.encrypt(plain)) == plain
    return {
        "passed": z3_passed and cp_passed and crypto_passed,
        "z3": z3_passed,
        "or_tools_cp_sat": cp_passed,
        "pycryptodome_aes_round_trip": crypto_passed,
    }


def _fst_probe() -> dict[str, Any]:
    """Compile, compose, and invert a tiny weighted string transduction."""
    import pynini

    encoder = pynini.string_map([("a", "qo"), ("b", "dy")]).closure()
    ciphertext = pynini.compose("abba", encoder).string()
    decoder = pynini.invert(encoder)
    plaintext = pynini.compose(ciphertext, decoder).string()
    return {
        "passed": ciphertext == "qodydyqo" and plaintext == "abba",
        "ciphertext": ciphertext,
        "round_trip": plaintext,
    }


def collect_diagnostics() -> dict[str, Any]:
    """Collect an offline environment and inference report."""
    import torch

    commands = {name: _command_version(name) for name in REQUIRED_COMMANDS}
    packages = {
        distribution: _package_probe(import_name, distribution)
        for import_name, distribution in IMPORT_PROBES.items()
    }
    cuda_available = torch.cuda.is_available()
    gpu: dict[str, Any] = {"available": cuda_available}
    if cuda_available:
        properties = torch.cuda.get_device_properties(0)
        gpu.update(
            {
                "name": properties.name,
                "compute_capability": list(torch.cuda.get_device_capability(0)),
                "total_memory_bytes": properties.total_memory,
                "torch_cuda_runtime": torch.version.cuda,
                "cudnn_version": torch.backends.cudnn.version(),
                "inference": _inference_probe("cuda"),
                "language_model_inference": _language_model_probe("cuda"),
                "quantized_inference": _quantized_gpu_probe(),
            }
        )

    report: dict[str, Any] = {
        "schema_version": "1.0",
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "wsl_distro": os.environ.get("WSL_DISTRO_NAME"),
            "python": sys.version.split()[0],
            "executable": sys.executable,
            "logical_cpus": os.cpu_count(),
        },
        "runtime_paths": {
            name: os.environ.get(name)
            for name in (
                "MANUSCRIPT_LAB_ROOT",
                "MANUSCRIPT_LAB_RUNTIME_ROOT",
                "UV_PROJECT_ENVIRONMENT",
                "UV_CACHE_DIR",
                "HF_HOME",
                "TORCH_HOME",
            )
        },
        "commands": commands,
        "packages": packages,
        "cpu_inference": _inference_probe("cpu"),
        "cpu_language_model_inference": _language_model_probe("cpu"),
        "cryptanalysis": _cryptanalysis_probe(),
        "finite_state": _fst_probe(),
        "gpu": gpu,
    }
    report["passed"] = (
        all(item["available"] for item in commands.values())
        and all(item["available"] for item in packages.values())
        and report["cpu_inference"]["passed"]
        and report["cpu_language_model_inference"]["passed"]
        and report["cryptanalysis"]["passed"]
        and report["finite_state"]["passed"]
        and gpu.get("inference", {}).get("passed", False)
        and gpu.get("language_model_inference", {}).get("passed", False)
        and gpu.get("quantized_inference", {}).get("passed", False)
    )
    return report


def write_diagnostics(report: dict[str, Any], path: Path) -> None:
    """Write diagnostics as formatted JSON."""
    import orjson

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(orjson.dumps(report, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE))
