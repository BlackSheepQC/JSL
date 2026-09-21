#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="$REPO_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    printf 'Erreur: Python introuvable: %s\n' "$PYTHON_BIN" >&2
    exit 1
fi

if [[ ! -x "$PYTHON" ]]; then
    printf 'Creation de l environnement Python: %s\n' "$VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

printf 'Installation des dependances Python\n'
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r "$REPO_DIR/requirements.txt"

printf 'Installation de Chromium pour Playwright\n'
"$PYTHON" -m playwright install chromium

chmod 755 \
    "$REPO_DIR/JS_listener.py" \
    "$REPO_DIR/test_js_listener.sh" \
    "$REPO_DIR/install_cli.sh"

"$REPO_DIR/install_cli.sh"

printf '\nInstallation terminee. Verification:\n'
"$PYTHON" "$REPO_DIR/JS_listener.py" --help >/dev/null
"$PYTHON" "$REPO_DIR/secret_scan.py" --help >/dev/null
printf '  js-listener, jslistener-db-reader, jslistener-secret-scan et jslistener-test sont disponibles.\n'
