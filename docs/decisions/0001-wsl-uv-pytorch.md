# Decision 0001: WSL ext4 runtime with uv and PyTorch CUDA wheels

- Status: accepted
- Date: 2026-08-29

## Context

The host provides WSL 2 and an NVIDIA RTX 4070. The repository is on Windows
NTFS, while the default Ubuntu distribution has ample ext4 storage. The lab must
support both CPU and GPU inference without contaminating the Windows Python 3.14
installation or depending on mutable global Python packages.

## Decision

Use Ubuntu 24.04, Python 3.12, and a uv-managed environment located under
`/home/nyx/.local/share/manuscript-lab/venv`. Use the official PyTorch CUDA 13.0
Linux wheel; it supports explicit CPU inference as well. Keep the Windows NVIDIA
driver as the only GPU driver and do not install a Linux display driver or CUDA
toolkit in the baseline.

## Consequences

- Python packages and model caches remain isolated and fast on ext4.
- The tracked `uv.lock` plus bootstrap script can recreate the environment.
- Commands must go through `scripts/run` so uv sees the external environment path.
- CUDA extension builds need a later, explicit decision and toolkit review.
- The environment path is host-local and disposable; raw sources are separately
  protected by manifests and backups.
