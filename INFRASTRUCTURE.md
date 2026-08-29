# Infrastructure

This file is the operational contract for the lab. Package-level versions are
locked in `uv.lock`; a successful machine snapshot is written to
`artifacts/diagnostics/latest.json` by the smoke test.

## Verified host baseline

| Component | Baseline |
|---|---|
| Host OS | Windows 11 Pro Insider Preview, build 28020 |
| WSL | WSL 2.7.3.0, kernel 6.6.114.1 |
| Distribution | Ubuntu 24.04.4 LTS (`Ubuntu-24.04`) |
| CPU | AMD Ryzen 7 5800X3D, 8 cores / 16 threads |
| Host memory | 128 GiB |
| WSL memory ceiling seen after local-AI setup | 94 GiB plus 24 GiB swap |
| GPU | NVIDIA GeForce RTX 4070, 12,282 MiB VRAM, compute capability 8.9 |
| Windows NVIDIA driver | 610.88 |
| WSL CUDA driver interface | CUDA 13.3 capability |
| Repository filesystem | Windows NTFS mounted at `/mnt/c/.../Voynich` |
| Runtime filesystem | WSL ext4 under `/home/nyx/.local/share/manuscript-lab` |

## Runtime topology

```text
Windows repository (tracked and reviewable)
  C:\Users\adminion\Documents\ChatGPT\Voynich
  /mnt/c/Users/adminion/Documents/ChatGPT/Voynich
        |
        +-- scripts/run exports package-specific cache paths
        v
WSL ext4 runtime (disposable and not tracked)
  /home/nyx/.local/share/manuscript-lab/
    venv/                 locked project environment
    cache/uv/             package cache
    cache/huggingface/    downloaded model and dataset cache
    cache/torch/          torch hub cache
    cache/matplotlib/     font/config cache
    cache/numba/          compiled CPU kernels

Separate local-AI runtime (pinned and stateful)
  /home/nyx/voynich-local-ai/
    bin/                   pinned llama.cpp and resource controls
    models/                rerankers
    cache/                 GGUF/model caches
    state/                 paths, hashes, environment, selected split
```

Keeping the environment on ext4 avoids the metadata and small-file penalty of
placing a multi-gigabyte Linux virtual environment on `/mnt/c`. Source data
stays beside the repository so it remains visible to the user and backup tools.

## Software layers

- Ubuntu packages: compilers, OpenFST/Graphviz, and file/PDF/image/OCR utilities.
- `uv` 0.12.7: project environment, exact sync, and cross-platform lockfile.
- Python 3.12: pinned by `.python-version` and `requires-python`.
- PyTorch 2.13 CUDA 13.0 wheel on Linux. The same wheel runs explicit CPU tests;
  no second environment is needed.
- Transformers, Accelerate, bitsandbytes, Datasets, OpenCV, scientific Python,
  JupyterLab, and test/format tools are declared in `pyproject.toml`.
- Z3, OR-Tools CP-SAT, DEAP, simanneal, PyCryptodome, cryptography, GMP bindings,
  and suffix-array tooling cover constraint and cipher experiments.
- Pynini supplies the Python weighted-FST interface; Ubuntu OpenFST provides CLI
  inspection and Graphviz rendering. Snakemake 9 owns reproducible workflow DAGs
  under `workflow/`.
- PARI/GP, GAP, MiniZinc, CBC, GLPK, and fplll are system-level specialist
  backends for modular algebra, groups, constraint/integer models, and lattices.
- llama.cpp b9553 serves the main local Qwen model; Ollama and local Transformers
  are mutually exclusive auxiliary tiers managed by a shared GPU lock.

PyTorch wheels contain their CUDA user-space runtime, and WSL maps the Windows
driver into Linux. A Linux NVIDIA display driver is unnecessary and prohibited.
CUDA toolkit 13.3 is installed at `/usr/local/cuda-13.3` for the reviewed local
llama.cpp build; do not replace it or add another toolkit without a measured
compile requirement.

## Commands

```bash
# Execute any command in the locked environment
./scripts/run python -V
./scripts/run pytest

# Lab diagnostics, solver/crypto, CPU/GPU tensor, masked-LM, and 8-bit probes
./scripts/lab doctor
./scripts/lab local-ai doctor --live

# Full acceptance gate
./scripts/smoke.sh

# Rebuild after a deliberate dependency change
./scripts/bootstrap_wsl.sh
```

`scripts/run` refuses to proceed when `uv.lock` is stale. Regenerate the lock
only when changing dependencies, review the diff, then run the full smoke test.

## Resource policy

- Default CPU worker ceiling: 12 threads, leaving four logical processors for
  Windows and the desktop application.
- Default GPU memory fraction: 0.90. Plan for roughly 10 GiB usable model space
  after display and framework overhead.
- Prefer BF16/FP16 or reviewed 8-bit/4-bit weights for larger local models.
- Leave Qwen active and auxiliary models unloaded. Batch embeddings, reranking,
  and critic calls through `ai-aux-run`; never make Qwen and GLM resident together.
- Store caches and weights on WSL ext4. Store immutable source data and selected
  reviewed outputs in the repository tree according to `.gitignore`.
- Avoid training on the only complete book until leakage-safe splits and null
  baselines exist. Inference and feature extraction are the initial workload.

## Rebuild and recovery

The WSL environment is disposable; the raw data is not.

```bash
cd /mnt/c/Users/adminion/Documents/ChatGPT/Voynich
./scripts/bootstrap_wsl.sh
./scripts/smoke.sh
```

Recovery requires the Git repository, untracked `data/raw/` files, and their
tracked manifests. Re-download model weights from recorded registry revisions.
Never treat a cache as the only copy of source data.

## Known boundaries

- The Windows Insider build is newer than typical production baselines; retain
  the diagnostic snapshot when comparing performance over time.
- WSL currently receives about half of host RAM. Change `.wslconfig` only if a
  measured workload needs it; this repository does not mutate global WSL config.
- The RTX 4070 has excellent single-GPU inference support but 12 GiB VRAM limits
  unquantized large multimodal models.
- No manuscript-specific OCR or pretrained model is installed yet. Selecting
  one before seeing the scans and encoding would bake in unsupported assumptions.
