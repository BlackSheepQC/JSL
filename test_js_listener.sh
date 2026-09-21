#!/usr/bin/env bash
# filepath: /home/riftx56/Documents/Scripts/Upload/JSL/test_js_listener.sh

set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PYTHON="${PYTHON:-python3}"
LISTENER="$SCRIPT_DIR/JS_listener.py"
DB="/tmp/js_listener_test.sqlite3"
LOG="/tmp/js_listener_test.log"
SCOPE="/tmp/in-scope.txt"
INACTIVITY=180

rm -f "$DB" "$LOG"
printf '%s\n' 'example.com' > "$SCOPE"

echo "[TEST] lancement en mode CTV"
"$PYTHON" "$LISTENER" \
  -t "https://example.com" \
    --mode ctv \
  --in-scope "$SCOPE" \
  --db "$DB" \
  --inactivity "$INACTIVITY" \
  --sleep 1 \
  >"$LOG" 2>&1 &

PID=$!

echo "[TEST] PID: $PID"
echo "[TEST] navigateur lancé"
sleep 8

if ! kill -0 "$PID" 2>/dev/null; then
    echo "[ERREUR] le processus est déjà arrêté"
    cat "$LOG"
    exit 1
fi

echo "[TEST] vérification du mode CTV"
grep -E "\[MODE\]|\[CTG\]|\[ERROR\]" "$LOG" || true

echo "[TEST] bascule CTV -> CTG"
kill -USR1 "$PID"
sleep 5

if ! kill -0 "$PID" 2>/dev/null; then
    echo "[ERREUR] le processus s'est arrêté après SIGUSR1"
    cat "$LOG"
    exit 1
fi

echo "[TEST] bascule CTG -> CTV"
kill -USR1 "$PID"
sleep 5

if ! kill -0 "$PID" 2>/dev/null; then
    echo "[ERREUR] le processus s'est arrêté après la seconde bascule"
    cat "$LOG"
    exit 1
fi

echo
echo "[TEST] résumé des événements"
grep -E "\[MODE\]|\[CTG\]|\[ERROR\]" "$LOG" || true

echo
echo "[TEST] vérification SQLite"

if [ ! -f "$DB" ]; then
    echo "[ERREUR] base SQLite absente: $DB"
    exit 1
fi

sqlite3 "$DB" <<'SQL'
.headers on
.mode column

SELECT
    id,
    target,
    mode,
    capture_enabled,
    status,
    stop_reason
FROM sessions;

SELECT
    COUNT(*) AS resources_captured
FROM resources;

SELECT
    COUNT(*) AS network_events_captured
FROM network_events;

SELECT
    COUNT(*) AS cookies_captured
FROM cookies;

SELECT
    event_name,
    COUNT(*) AS total
FROM events
GROUP BY event_name
ORDER BY event_name;

SELECT
    old_mode,
    new_mode,
    COUNT(*) AS total
FROM mode_changes
GROUP BY old_mode, new_mode;
SQL

echo
echo "[TEST] arrêt propre"
kill -TERM "$PID"

wait "$PID" 2>/dev/null || true

echo
echo "[TEST] sortie finale"
tail -n 30 "$LOG"

echo
echo "[TEST] fichiers:"
echo "  Log : $LOG"
echo "  DB  : $DB"

echo
echo "[TEST] terminé"