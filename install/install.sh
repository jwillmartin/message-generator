#!/bin/bash

set -e

# Set environment variables
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN=${PYTHON:-python3}
VENV_DIR="$REPO_ROOT/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"

# Dependencies
dependencies="python3 \
    python3-pip \
    python3-venv"

# Update package lists and install Python 3 and pip
sudo apt update
sudo apt install -y $dependencies

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# Install Python packages into the virtual environment
"$VENV_PYTHON" -m pip install --upgrade pip

# Ensure j2735_202409 package is present in the venv; clone/install only if missing
echo "Checking for Python module 'j2735_202409'…"
if ! "$VENV_PYTHON" -c "import importlib; importlib.import_module('j2735_202409')" >/dev/null 2>&1; then
  echo "'j2735_202409' not found; attempting to clone and install…"
  J2735_REPO_URL=${J2735_REPO_URL:-https://github.com/usdot-fhwa-stol/j2735_202409.git}
  git clone "$J2735_REPO_URL" j2735_202409
  pushd j2735_202409 >/dev/null
  "$VENV_PYTHON" -m pip install dist/j2735_202409-0.1.0-py3-none-any.whl
  popd >/dev/null
  rm -rf j2735_202409
  # Verify import after install
  if "$VENV_PYTHON" -c "import importlib; importlib.import_module('j2735_202409')" >/dev/null 2>&1; then
    echo "Installed and verified 'j2735_202409'"
  else
    echo "Warning: 'j2735_202409' still not importable after install attempt." >&2
  fi
else
  echo "'j2735_202409' already available; skipping clone/install."
fi

# Rewrite script shebangs to point at the venv's Python interpreter
for script in "$REPO_ROOT/src/srm/generate-srm.py" "$REPO_ROOT/src/sdsm/sdsmSim.py"; do
  if [ -f "$script" ]; then
    sed -i "1s|^#!.*|#!$VENV_PYTHON|" "$script"
    chmod +x "$script"
  fi
done
