#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PYTHON="$REPO_DIR/.venv/bin/python"
BIN_DIR="${HOME}/.local/bin"

if [[ ! -x "$PYTHON" ]]; then
    printf 'Erreur: interpreteur introuvable: %s\n' "$PYTHON" >&2
    printf 'Creez d’abord l’environnement .venv dans le depot.\n' >&2
    exit 1
fi

mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/js-listener" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec "$PYTHON" "$REPO_DIR/JS_listener.py" "\$@"
EOF

cat > "$BIN_DIR/jslistener-db-reader" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec "$PYTHON" "$REPO_DIR/JSlistenerDB_reader.py" "\$@"
EOF

cat > "$BIN_DIR/jslistener-secret-scan" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec "$PYTHON" "$REPO_DIR/secret_scan.py" "\$@"
EOF

cat > "$BIN_DIR/jslistener-test" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export PYTHON="$PYTHON"
exec "$REPO_DIR/test_js_listener.sh" "\$@"
EOF

chmod 755 \
    "$BIN_DIR/js-listener" \
    "$BIN_DIR/jslistener-db-reader" \
    "$BIN_DIR/jslistener-secret-scan" \
    "$BIN_DIR/jslistener-test"

printf 'Commandes installees dans %s\n' "$BIN_DIR"
printf '%s\n' \
    "  js-listener" \
    "  jslistener-db-reader" \
    "  jslistener-secret-scan" \
    "  jslistener-test"
