#!/usr/bin/env bash
set -euo pipefail

if [[ ! -r /etc/os-release ]] || ! grep -q '^ID=ubuntu$' /etc/os-release; then
  echo "This bootstrap targets Ubuntu under WSL 2." >&2
  exit 1
fi

if [[ -z "${WSL_DISTRO_NAME:-}" ]]; then
  echo "WSL_DISTRO_NAME is not set; run this script inside WSL 2." >&2
  exit 1
fi

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_root="${MANUSCRIPT_LAB_RUNTIME_ROOT:-${HOME}/.local/share/manuscript-lab}"
uv_version="0.12.7"

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  build-essential \
  ca-certificates \
  cmake \
  coinor-cbc \
  curl \
  ffmpeg \
  fplll-tools \
  graphviz \
  gap \
  git \
  git-lfs \
  glpk-utils \
  imagemagick \
  jq \
  libfst-dev \
  libfst-tools \
  libgmp-dev \
  libgl1 \
  libglib2.0-0t64 \
  libgomp1 \
  libmpfr-dev \
  libssl-dev \
  libsm6 \
  libxext6 \
  libxrender1 \
  ninja-build \
  minizinc \
  pari-gp \
  pkg-config \
  poppler-utils \
  python3-dev \
  python3-venv \
  ripgrep \
  sqlite3 \
  tesseract-ocr

if ! command -v uv >/dev/null 2>&1 && [[ ! -x "${HOME}/.local/bin/uv" ]]; then
  installer="$(mktemp)"
  trap 'rm -f "${installer}"' EXIT
  curl --proto '=https' --tlsv1.2 -LsSf \
    "https://astral.sh/uv/${uv_version}/install.sh" \
    -o "${installer}"
  UV_UNMANAGED_INSTALL="${HOME}/.local/bin" UV_NO_MODIFY_PATH=1 sh "${installer}"
fi

uv_bin="$(command -v uv || true)"
if [[ -z "${uv_bin}" ]]; then
  uv_bin="${HOME}/.local/bin/uv"
fi

actual_uv_version="$(${uv_bin} --version | awk '{print $2}')"
if [[ "${actual_uv_version}" != "${uv_version}" ]]; then
  echo "Expected uv ${uv_version}, found ${actual_uv_version}." >&2
  echo "Install the pinned version or update the infrastructure decision deliberately." >&2
  exit 1
fi

mkdir -p \
  "${runtime_root}/cache/uv" \
  "${runtime_root}/cache/huggingface" \
  "${runtime_root}/cache/torch" \
  "${runtime_root}/cache/matplotlib" \
  "${runtime_root}/cache/numba"

export UV_PROJECT_ENVIRONMENT="${runtime_root}/venv"
export UV_CACHE_DIR="${runtime_root}/cache/uv"
cd "${project_root}"

if [[ -f uv.lock ]]; then
  "${uv_bin}" sync --locked --all-groups
else
  "${uv_bin}" lock
  "${uv_bin}" sync --locked --all-groups
fi

git lfs install --local
./scripts/smoke.sh
