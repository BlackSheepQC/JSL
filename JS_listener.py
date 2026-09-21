#!/usr/bin/env python3

"""
JS Listener — Observation réseau et cartographie technique à faible impact.

Objectif :
    Observer une navigation manuelle sur une cible autorisée et produire un
    rapport exploitable hors ligne, sans générer de trafic artificiel.

Modes :
    CTV — Capture de trafic et de variables observables :
        - requêtes fetch et XHR ;
        - méthodes, URLs et types de ressources ;
        - statuts HTTP et types MIME ;
        - tailles de réponses ;
        - redirections et erreurs réseau ;
        - événements associés aux pages, frames et onglets ;
        - réponses JSON selon les limites configurées.

    CTG — Cartographie technique :
        - fichiers JavaScript et modules MJS ;
        - fichiers JSON ;
        - ressources chargées par les pages ;
        - domaines associés ;
        - dépendances entre pages et ressources ;
        - taille, type MIME, statut HTTP et empreinte SHA-256 ;
        - sauvegarde optionnelle des corps de réponses.

Fonctionnement :
    Le navigateur Playwright est conservé pendant toute la session.
    CTV et CTG utilisent le même contexte, les mêmes cookies en mémoire,
    le même périmètre et la même base SQLite.

    Le mode peut être basculé à chaud avec SIGUSR1 :
        CTV <-> CTG

    Le basculement ne capture pas rétroactivement les ressources déjà chargées.
    Une navigation volontaire est nécessaire pour observer les nouvelles
    ressources dans le mode actif.

Périmètre :
    Les URLs sont filtrées par un fichier in-scope contenant des domaines,
    wildcards ou expressions régulières. Les URLs hors périmètre sont ignorées.

Cookies et secrets :
    Les cookies ne sont pas capturés par défaut.
    --capture-cookies enregistre uniquement leurs métadonnées.
    --capture-cookie-values active explicitement l'enregistrement des valeurs
    dans un fichier secrets.json séparé et protégé.
    --clear-cookies supprime les cookies du contexte avant la navigation.

Stockage :
    Les données détaillées sont enregistrées dans SQLite, notamment dans :
        - pages ;
        - frames ;
        - network_events ;
        - resources ;
        - dependencies ;
        - mode_changes ;
        - cookies ;
        - events.

    Les anciennes tables scripts et events sont conservées pour compatibilité.

Profil de page :
    À la fin de la session, build_profile() génère un résumé hors ligne à
    partir de SQLite. Ce profil regroupe les pages, frames, ressources,
    appels API, domaines, statuts HTTP, erreurs, dépendances et changements
    de mode. Il n'effectue aucune nouvelle requête réseau.

Contrôle :
    SIGUSR1 : bascule CTV/CTG ;
    SIGTERM  : arrêt propre ;
    SIGUSR2  : arrêt d'urgence ;
    Ctrl+C   : arrêt manuel.

Sorties :
    - base SQLite ;
    - rapport JSON optionnel ;
    - journal JSONL des ressources ;
    - journal JSONL des cookies ;
    - fichier séparé de secrets ;
    - corps JS/JSON optionnels avec limite de taille.

Utilisation :
    Ce programme doit être utilisé uniquement sur des systèmes et domaines
    explicitement autorisés, notamment dans le cadre d'un test Bug Bounty
    conforme au périmètre défini.

Exemple :
    js-listener \
        --target https://example.com \
        --mode ctv \
        --in-scope /tmp/in-scope.txt

JS Listener — V1 CTV/CTG.

CTV : capture de trafic et de variables observables.
CTG : cartographie des ressources JS/MJS/JSON.

Utiliser uniquement sur des cibles explicitement autorisées.
"""

import argparse
import fnmatch
import hashlib
import json
import os
import re
import signal
import sqlite3
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


DEFAULT_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0"
DEFAULT_DB = "/tmp/js_listener.sqlite3"
DEFAULT_COOKIE_LOG = "/tmp/cookie_log.jsonl"
DEFAULT_JS_LOG = "/tmp/js_log.jsonl"
DEFAULT_SECRETS = "/tmp/secrets.json"


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_parent(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)


def is_js_url(url):
    return urlparse(url or "").path.lower().endswith((".js", ".mjs"))


def is_json_url(url):
    return urlparse(url or "").path.lower().endswith(".json")


def append_jsonl(path, payload):
    ensure_parent(path)

    with open(path, "a", encoding="utf-8") as handle:
        os.chmod(path, 0o600)
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_scope_file(path):
    if not path:
        return []

    patterns = []

    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()

            if line and not line.startswith("#"):
                patterns.append(line)

    return patterns


def url_in_scope(url, patterns):
    if not patterns:
        return False

    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    full_url = url.lower()

    for raw_pattern in patterns:
        pattern = raw_pattern.lower().strip()

        if pattern.startswith("re:"):
            try:
                expression = pattern[3:]

                if re.fullmatch(expression, hostname):
                    return True

                if re.fullmatch(expression, full_url):
                    return True

            except re.error as exc:
                print(f"[SCOPE-ERROR] {exc}", file=sys.stderr)

            continue

        if "://" in pattern:
            pattern = urlparse(pattern).hostname or pattern

        if fnmatch.fnmatchcase(hostname, pattern.rstrip(".")):
            return True

    return False


def connect_db(path):
    ensure_parent(path)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            target TEXT,
            started_at TEXT,
            ended_at TEXT,
            status TEXT,
            user_agent TEXT,
            headless INTEGER,
            mode TEXT,
            capture_enabled INTEGER,
            scope_file TEXT,
            capture_cookies INTEGER,
            capture_cookie_values INTEGER,
            stop_reason TEXT
        );

        CREATE TABLE IF NOT EXISTS scripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            request_key TEXT UNIQUE,
            ts TEXT,
            url TEXT,
            method TEXT,
            status_code INTEGER,
            resource_type TEXT,
            mime_type TEXT,
            size_bytes INTEGER,
            failure TEXT,
            response_body_path TEXT,
            redirect_chain TEXT,
            domain TEXT,
            path TEXT
        );

        CREATE TABLE IF NOT EXISTS cookies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            ts TEXT,
            domain TEXT,
            name TEXT,
            path TEXT,
            expires REAL,
            http_only INTEGER,
            secure INTEGER,
            same_site TEXT,
            session_only INTEGER
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            ts TEXT,
            event_name TEXT,
            event_data TEXT
        );

        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            page_key TEXT UNIQUE,
            url TEXT,
            title TEXT,
            opened_at TEXT,
            closed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS frames (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            page_key TEXT,
            frame_key TEXT UNIQUE,
            url TEXT,
            name TEXT,
            attached_at TEXT,
            detached_at TEXT
        );

        CREATE TABLE IF NOT EXISTS network_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            page_key TEXT,
            frame_key TEXT,
            request_key TEXT UNIQUE,
            ts TEXT,
            url TEXT,
            method TEXT,
            resource_type TEXT,
            status_code INTEGER,
            mime_type TEXT,
            request_size INTEGER,
            response_size INTEGER,
            failure TEXT,
            redirect_chain TEXT,
            is_json INTEGER
        );

        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            page_key TEXT,
            frame_key TEXT,
            request_key TEXT UNIQUE,
            ts TEXT,
            url TEXT,
            method TEXT,
            resource_type TEXT,
            status_code INTEGER,
            mime_type TEXT,
            size_bytes INTEGER,
            sha256 TEXT,
            body_path TEXT,
            domain TEXT,
            path TEXT
        );

        CREATE TABLE IF NOT EXISTS dependencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            page_key TEXT,
            source_url TEXT,
            target_url TEXT,
            dependency_type TEXT,
            ts TEXT
        );

        CREATE TABLE IF NOT EXISTS mode_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            ts TEXT,
            old_mode TEXT,
            new_mode TEXT,
            trigger TEXT
        );
        """
    )

    conn.commit()
    return conn


def log_event(conn, session_id, name, data):
    conn.execute(
        """
        INSERT INTO events(session_id, ts, event_name, event_data)
        VALUES (?, ?, ?, ?)
        """,
        (
            session_id,
            utc_now(),
            name,
            json.dumps(data, ensure_ascii=False),
        ),
    )
    conn.commit()


def page_key(page):
    return str(id(page))


def frame_key(frame):
    return str(id(frame))


def request_key(request):
    return str(id(request))


def register_page(conn, session_id, page):
    """
    Enregistre uniquement les pages réelles.
    about:blank sert de page initiale Playwright et est ignorée.
    """
    key = page_key(page)

    if page.url != "about:blank":
        conn.execute(
            """
            INSERT OR IGNORE INTO pages(
                session_id, page_key, url, title, opened_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, key, page.url, None, utc_now()),
        )
        conn.commit()

    return key


def register_frame(conn, session_id, page, frame):
    key = frame_key(frame)

    conn.execute(
        """
        INSERT OR IGNORE INTO frames(
            session_id, page_key, frame_key, url, name, attached_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            page_key(page),
            key,
            frame.url,
            frame.name,
            utc_now(),
        ),
    )
    conn.commit()

    return key


def update_page_after_navigation(conn, session_id, page):
    if page.url == "about:blank":
        return

    key = page_key(page)

    try:
        title = page.title()
    except Exception:
        title = None

    conn.execute(
        """
        INSERT OR IGNORE INTO pages(
            session_id, page_key, url, title, opened_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            session_id,
            key,
            page.url,
            title,
            utc_now(),
        ),
    )

    conn.execute(
        """
        UPDATE pages
        SET url=?, title=?
        WHERE page_key=?
        """,
        (page.url, title, key),
    )

    conn.commit()


def save_response_body(response, output_dir, max_size):
    body = response.body()

    if len(body) > max_size:
        return None, len(body), None

    digest = hashlib.sha256(body).hexdigest()
    extension = ".json" if is_json_url(response.url) else ".js"
    path = os.path.join(output_dir, f"{digest}{extension}")

    ensure_parent(path)

    with open(path, "wb") as handle:
        handle.write(body)

    os.chmod(path, 0o600)

    return path, len(body), digest


def redirect_chain(request):
    chain = []
    previous = request.redirected_from

    while previous:
        chain.append(previous.url)
        previous = previous.redirected_from

    return list(reversed(chain))


def insert_network_event(conn, session_id, page, request):
    key = request_key(request)

    conn.execute(
        """
        INSERT OR IGNORE INTO network_events(
            session_id, page_key, frame_key, request_key, ts,
            url, method, resource_type, status_code, mime_type,
            request_size, response_size, failure, redirect_chain, is_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            page_key(page),
            frame_key(request.frame),
            key,
            utc_now(),
            request.url,
            request.method,
            request.resource_type,
            None,
            None,
            None,
            None,
            None,
            json.dumps(redirect_chain(request), ensure_ascii=False),
            int(is_json_url(request.url)),
        ),
    )
    conn.commit()


def update_network_response(conn, request, response):
    mime = response.headers.get("content-type", "").split(";", 1)[0]
    size = response.headers.get("content-length")

    try:
        size = int(size) if size else None
    except ValueError:
        size = None

    conn.execute(
        """
        UPDATE network_events
        SET status_code=?, mime_type=?, response_size=?
        WHERE request_key=?
        """,
        (
            response.status,
            mime,
            size,
            request_key(request),
        ),
    )
    conn.commit()


def insert_resource(conn, session_id, page, request, response):
    key = request_key(request)
    parsed = urlparse(response.url)
    mime = response.headers.get("content-type", "").split(";", 1)[0]

    conn.execute(
        """
        INSERT OR IGNORE INTO resources(
            session_id, page_key, frame_key, request_key, ts,
            url, method, resource_type, status_code, mime_type,
            size_bytes, sha256, body_path, domain, path
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            page_key(page),
            frame_key(request.frame),
            key,
            utc_now(),
            response.url,
            request.method,
            request.resource_type,
            response.status,
            mime,
            None,
            None,
            None,
            parsed.netloc,
            parsed.path,
        ),
    )
    conn.commit()


def update_resource(conn, request, body_path, body_size, digest):
    conn.execute(
        """
        UPDATE resources
        SET size_bytes=?, sha256=?, body_path=?
        WHERE request_key=?
        """,
        (
            body_size,
            digest,
            body_path,
            request_key(request),
        ),
    )
    conn.commit()


def add_dependency(conn, session_id, page, source_url, target_url, kind):
    conn.execute(
        """
        INSERT INTO dependencies(
            session_id, page_key, source_url, target_url,
            dependency_type, ts
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            page_key(page),
            source_url,
            target_url,
            kind,
            utc_now(),
        ),
    )
    conn.commit()


def cookie_identity(cookie):
    raw = "|".join(
        str(cookie.get(value, ""))
        for value in ("domain", "name", "path", "value")
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def write_secrets(path, records):
    ensure_parent(path)
    temporary = f"{path}.tmp"

    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2, ensure_ascii=False)

    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def flush_cookies(
    conn,
    session_id,
    context,
    cookie_log,
    secrets_path,
    scope,
    capture_values,
    seen,
    secrets,
):
    for cookie in context.cookies():
        domain = cookie.get("domain", "")
        test_url = f"https://{domain.lstrip('.')}"

        if not url_in_scope(test_url, scope):
            continue

        identity = cookie_identity(cookie)

        if identity in seen:
            continue

        seen.add(identity)

        metadata = {
            "ts": utc_now(),
            "domain": cookie.get("domain"),
            "name": cookie.get("name"),
            "path": cookie.get("path"),
            "expires": cookie.get("expires"),
            "httpOnly": bool(cookie.get("httpOnly")),
            "secure": bool(cookie.get("secure")),
            "sameSite": cookie.get("sameSite"),
            "session": bool(cookie.get("session")),
        }

        conn.execute(
            """
            INSERT INTO cookies(
                session_id, ts, domain, name, path, expires,
                http_only, secure, same_site, session_only
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                utc_now(),
                cookie.get("domain"),
                cookie.get("name"),
                cookie.get("path"),
                cookie.get("expires"),
                int(bool(cookie.get("httpOnly"))),
                int(bool(cookie.get("secure"))),
                cookie.get("sameSite"),
                int(bool(cookie.get("session"))),
            ),
        )
        conn.commit()

        append_jsonl(cookie_log, metadata)

        if capture_values:
            secret = dict(metadata)
            secret["session_id"] = session_id
            secret["value"] = cookie.get("value")
            secrets.append(secret)
            write_secrets(secrets_path, secrets)


def rows(conn, table, session_id):
    return [
        dict(row)
        for row in conn.execute(
            f"SELECT * FROM {table} WHERE session_id=? ORDER BY id",
            (session_id,),
        ).fetchall()
    ]


def build_profile(conn, session_id):
    session = conn.execute(
        "SELECT * FROM sessions WHERE id=?",
        (session_id,),
    ).fetchone()

    pages = rows(conn, "pages", session_id)
    frames = rows(conn, "frames", session_id)
    network_events = rows(conn, "network_events", session_id)
    resources = rows(conn, "resources", session_id)
    dependencies = rows(conn, "dependencies", session_id)
    mode_changes = rows(conn, "mode_changes", session_id)

    domains = {}
    statuses = {}
    api = []
    errors = []

    def count_domain(url):
        domain = urlparse(url or "").netloc or "unknown"
        domains[domain] = domains.get(domain, 0) + 1

    def count_status(status):
        if status is not None:
            key = str(status)
            statuses[key] = statuses.get(key, 0) + 1

    for event in network_events:
        url = event.get("url")
        status = event.get("status_code")

        count_domain(url)
        count_status(status)

        if event.get("resource_type") in {"fetch", "xhr"}:
            parsed = urlparse(url or "")

            api.append(
                {
                    "method": event.get("method"),
                    "url": url,
                    "path": parsed.path,
                    "domain": parsed.netloc,
                    "status_code": status,
                    "mime_type": event.get("mime_type"),
                }
            )

        if event.get("failure"):
            errors.append(
                {
                    "type": "network",
                    "method": event.get("method"),
                    "url": url,
                    "failure": event.get("failure"),
                }
            )

        if status is not None and status >= 400:
            errors.append(
                {
                    "type": "http",
                    "method": event.get("method"),
                    "url": url,
                    "status_code": status,
                }
            )

    javascript = 0
    json_resources = 0
    other_resources = 0

    for resource in resources:
        url = resource.get("url")
        status = resource.get("status_code")
        mime = (resource.get("mime_type") or "").lower()

        count_domain(url)
        count_status(status)

        is_javascript = (
            "javascript" in mime
            or is_js_url(url)
            or resource.get("resource_type") == "script"
        )

        is_json = "json" in mime or is_json_url(url)

        if is_javascript:
            javascript += 1
        elif is_json:
            json_resources += 1
        else:
            other_resources += 1

        if status is not None and status >= 400:
            errors.append(
                {
                    "type": "http",
                    "url": url,
                    "status_code": status,
                }
            )

    page_profiles = []

    for page in pages:
        current_page_key = page.get("page_key")

        page_profiles.append(
            {
                "page_key": current_page_key,
                "url": page.get("url"),
                "title": page.get("title"),
                "opened_at": page.get("opened_at"),
                "closed_at": page.get("closed_at"),
                "network_events": sum(
                    event.get("page_key") == current_page_key
                    for event in network_events
                ),
                "resources": sum(
                    resource.get("page_key") == current_page_key
                    for resource in resources
                ),
            }
        )

    modes = []

    if session and session["mode"]:
        modes.append(session["mode"])

    for change in mode_changes:
        mode = change.get("new_mode")

        if mode and mode not in modes:
            modes.append(mode)

    return {
        "session_id": session_id,
        "pages": page_profiles,
        "frames": frames,
        "resources": {
            "total": len(resources),
            "javascript": javascript,
            "json": json_resources,
            "other": other_resources,
        },
        "api": api,
        "domains": dict(sorted(domains.items())),
        "http_statuses": dict(
            sorted(statuses.items(), key=lambda item: int(item[0]))
        ),
        "errors": errors,
        "dependencies": dependencies,
        "mode_changes": mode_changes,
        "summary": {
            "pages": len(pages),
            "frames": len(frames),
            "network_events": len(network_events),
            "resources": len(resources),
            "api_endpoints": len(api),
            "errors": len(errors),
            "domains": len(domains),
            "modes": modes,
        },
    }


def export_session(conn, session_id):
    session = conn.execute(
        "SELECT * FROM sessions WHERE id=?",
        (session_id,),
    ).fetchone()

    report = {
        "session": dict(session) if session else {},
        "pages": rows(conn, "pages", session_id),
        "frames": rows(conn, "frames", session_id),
        "network_events": rows(conn, "network_events", session_id),
        "resources": rows(conn, "resources", session_id),
        "dependencies": rows(conn, "dependencies", session_id),
        "mode_changes": rows(conn, "mode_changes", session_id),
        "cookies": rows(conn, "cookies", session_id),
        "events": rows(conn, "events", session_id),
    }

    report["profile"] = build_profile(conn, session_id)
    return report


def main():
    parser = argparse.ArgumentParser(
        description="JS Listener V1 — CTV/CTG faible impact."
    )

    parser.add_argument("-t", "--target", required=True)
    parser.add_argument("-u", "--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument("--mode", choices=("ctv", "ctg"), default="ctv")
    parser.add_argument("--in-scope")
    parser.add_argument(
        "--clear-cookies",
        action="store_true",
        help="supprime les cookies avant la navigation",
    )
    parser.add_argument("--capture-cookies", action="store_true")
    parser.add_argument("--capture-cookie-values", action="store_true")
    parser.add_argument("--secrets", default=DEFAULT_SECRETS)
    parser.add_argument("--inactivity", type=float, default=180)
    parser.add_argument("--sleep", type=float, default=1)
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--cookie-log", default=DEFAULT_COOKIE_LOG)
    parser.add_argument("--js-log", default=DEFAULT_JS_LOG)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--capture-response-bodies", action="store_true")
    parser.add_argument(
        "--response-dir",
        default="/tmp/js_listener_responses",
    )
    parser.add_argument("--max-response-size", type=int, default=2097152)
    parser.add_argument("-j", "--json", action="store_true")
    parser.add_argument("-o", "--output")

    args = parser.parse_args()

    if args.capture_cookie_values and not args.capture_cookies:
        parser.error(
            "--capture-cookie-values nécessite --capture-cookies"
        )

    if args.max_response_size <= 0:
        parser.error("--max-response-size doit être positif")

    scope = load_scope_file(args.in_scope)
    conn = connect_db(args.db)
    session_id = f"session_{int(time.time() * 1000)}"

    runtime = {
        "mode": args.mode,
        "shutdown": False,
        "emergency": False,
        "stop_reason": None,
    }

    last_activity = time.time()
    browser = None
    seen_cookies = set()
    secrets = []

    def mark_activity(*_args):
        nonlocal last_activity
        last_activity = time.time()

    def toggle_mode(_signum, _frame):
        old = runtime["mode"]
        new = "ctg" if old == "ctv" else "ctv"
        runtime["mode"] = new

        conn.execute(
            """
            INSERT INTO mode_changes(
                session_id, ts, old_mode, new_mode, trigger
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, utc_now(), old, new, "SIGUSR1"),
        )
        conn.commit()

        log_event(
            conn,
            session_id,
            "mode_changed",
            {
                "from": old,
                "to": new,
                "trigger": "SIGUSR1",
            },
        )

        print(f"[MODE] {old} -> {new}")

    def graceful_shutdown(_signum, _frame):
        runtime["shutdown"] = True
        runtime["stop_reason"] = "signal_SIGTERM"
        print("[SHUTDOWN] arrêt propre demandé")

    def emergency_shutdown(_signum, _frame):
        runtime["shutdown"] = True
        runtime["emergency"] = True
        runtime["stop_reason"] = "signal_SIGUSR2"
        print("[EMERGENCY] arrêt d'urgence demandé")

    signal.signal(signal.SIGUSR1, toggle_mode)
    signal.signal(signal.SIGTERM, graceful_shutdown)
    signal.signal(signal.SIGUSR2, emergency_shutdown)

    conn.execute(
        """
        INSERT INTO sessions(
            id, target, started_at, status, user_agent, headless,
            mode, capture_enabled, scope_file, capture_cookies,
            capture_cookie_values
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            args.target,
            utc_now(),
            "running",
            args.user_agent,
            int(args.headless),
            args.mode,
            1,
            args.in_scope,
            int(args.capture_cookies),
            int(args.capture_cookie_values),
        ),
    )
    conn.commit()

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=args.headless,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--start-maximized",
                ],
            )

            context = browser.new_context(
                ignore_https_errors=True,
                user_agent=args.user_agent,
                no_viewport=True,
            )

            if args.clear_cookies:
                context.clear_cookies()
                print("[COOKIES] cookies du contexte supprimés")

            def register(page):
                key = register_page(conn, session_id, page)

                # Exposé une seule fois par page, pas à chaque navigation.
                try:
                    page.expose_binding(
                        "__jsListenerActivity",
                        lambda source: mark_activity(),
                    )
                    page.add_init_script(
                        """
                        ['click', 'keydown', 'scroll', 'mousemove'].forEach(evt => {
                            window.addEventListener(evt, () => {
                                if (window.__jsListenerActivity) {
                                    window.__jsListenerActivity();
                                }
                            }, { passive: true });
                        });
                        """
                    )
                except Exception as exc:
                    print(f"[BINDING-ERROR] {exc}", file=sys.stderr)

                def on_close():
                    conn.execute(
                        """
                        UPDATE pages
                        SET closed_at=?
                        WHERE page_key=?
                        """,
                        (utc_now(), key),
                    )
                    conn.commit()

                    if not runtime["shutdown"]:
                        runtime["shutdown"] = True
                        runtime["stop_reason"] = "browser_closed_by_user"
                        print("[CLOSE] fenêtre du navigateur fermée manuellement")

                def on_frame_navigated(frame):
                    mark_activity()
                    register_frame(conn, session_id, page, frame)

                    if frame == page.main_frame:
                        update_page_after_navigation(
                            conn,
                            session_id,
                            page,
                        )

                    conn.execute(
                        """
                        UPDATE frames
                        SET url=?
                        WHERE frame_key=?
                        """,
                        (frame.url, frame_key(frame)),
                    )
                    conn.commit()

                def on_frame_attached(frame):
                    mark_activity()
                    register_frame(conn, session_id, page, frame)

                def on_frame_detached(frame):
                    conn.execute(
                        """
                        UPDATE frames
                        SET detached_at=?
                        WHERE frame_key=?
                        """,
                        (utc_now(), frame_key(frame)),
                    )
                    conn.commit()

                def on_request(request):
                    mark_activity()

                    if not url_in_scope(request.url, scope):
                        return

                    if (
                        runtime["mode"] == "ctv"
                        and request.resource_type in {"fetch", "xhr"}
                    ):
                        insert_network_event(
                            conn,
                            session_id,
                            page,
                            request,
                        )

                def on_response(response):
                    mark_activity()

                    request = response.request

                    if not url_in_scope(response.url, scope):
                        return

                    mime = response.headers.get(
                        "content-type",
                        "",
                    ).lower()

                    is_network = request.resource_type in {
                        "fetch",
                        "xhr",
                    }

                    is_json = "application/json" in mime

                    is_resource = (
                        is_js_url(response.url)
                        or is_json_url(response.url)
                        or (is_network and is_json)
                    )

                    if runtime["mode"] == "ctv" and is_network:
                        insert_network_event(
                            conn,
                            session_id,
                            page,
                            request,
                        )
                        update_network_response(
                            conn,
                            request,
                            response,
                        )

                    if runtime["mode"] != "ctg" or not is_resource:
                        return

                    insert_resource(
                        conn,
                        session_id,
                        page,
                        request,
                        response,
                    )

                    body_path = None
                    body_size = None
                    digest = None

                    if args.capture_response_bodies:
                        try:
                            (
                                body_path,
                                body_size,
                                digest,
                            ) = save_response_body(
                                response,
                                args.response_dir,
                                args.max_response_size,
                            )
                        except Exception as exc:
                            print(
                                f"[BODY-ERROR] {exc}",
                                file=sys.stderr,
                            )

                    update_resource(
                        conn,
                        request,
                        body_path,
                        body_size,
                        digest,
                    )

                    add_dependency(
                        conn,
                        session_id,
                        page,
                        page.url,
                        response.url,
                        "resource",
                    )

                    append_jsonl(
                        args.js_log,
                        {
                            "ts": utc_now(),
                            "mode": "ctg",
                            "url": response.url,
                            "method": request.method,
                            "status_code": response.status,
                            "resource_type": request.resource_type,
                            "mime_type": mime,
                            "body_path": body_path,
                            "body_size": body_size,
                            "domain": urlparse(
                                response.url
                            ).netloc,
                            "path": urlparse(
                                response.url
                            ).path,
                        },
                    )

                    print(f"[CTG] {response.status} {response.url}")

                def on_request_failed(request):
                    if runtime["mode"] != "ctv":
                        return

                    if request.resource_type not in {"fetch", "xhr"}:
                        return

                    if not url_in_scope(request.url, scope):
                        return

                    insert_network_event(
                        conn,
                        session_id,
                        page,
                        request,
                    )

                    conn.execute(
                        """
                        UPDATE network_events
                        SET failure=?
                        WHERE request_key=?
                        """,
                        (
                            request.failure,
                            request_key(request),
                        ),
                    )
                    conn.commit()

                page.on("close", on_close)
                page.on("framenavigated", on_frame_navigated)
                page.on("frameattached", on_frame_attached)
                page.on("framedetached", on_frame_detached)
                page.on("request", on_request)
                page.on("response", on_response)
                page.on("requestfailed", on_request_failed)
                page.on("domcontentloaded", mark_activity)
                page.on("load", mark_activity)

                log_event(
                    conn,
                    session_id,
                    "page_registered",
                    {
                        "url": page.url,
                        "page_key": key,
                    },
                )

            def on_context_close():
                if not runtime["shutdown"]:
                    runtime["shutdown"] = True
                    runtime["stop_reason"] = "browser_closed_by_user"
                    print("[CLOSE] navigateur fermé manuellement")

            context.on("close", on_context_close)

            # Première page : enregistrée manuellement.
            page = context.new_page()
            register(page)

            # S'applique uniquement aux futurs onglets/popups.
            context.on("page", register)

            print(f"[NAVIGATE] {args.target}")

            page.goto(
                args.target,
                wait_until="domcontentloaded",
                timeout=120000,
            )

            print(f"[MODE] {runtime['mode']}")
            print(
                "[LISTEN] "
                "USR1=toggle CTV/CTG, "
                "SIGTERM=stop, "
                "SIGUSR2=emergency"
            )

            while not runtime["shutdown"]:
                if not browser.is_connected():
                    runtime["stop_reason"] = "browser_closed_by_user"
                    print("[CLOSE] connexion au navigateur perdue")
                    break

                try:
                    if page.is_closed():
                        runtime["stop_reason"] = "page_closed"
                        break
                except Exception:
                    runtime["stop_reason"] = "browser_closed_by_user"
                    print("[CLOSE] page inaccessible, navigateur fermé")
                    break

                if (
                    args.capture_cookies
                    and not runtime["emergency"]
                ):
                    try:
                        flush_cookies(
                            conn,
                            session_id,
                            context,
                            args.cookie_log,
                            args.secrets,
                            scope,
                            args.capture_cookie_values,
                            seen_cookies,
                            secrets,
                        )
                    except Exception:
                        runtime["stop_reason"] = "browser_closed_by_user"
                        print("[CLOSE] contexte inaccessible, navigateur fermé")
                        break

                time.sleep(args.sleep)

                if (
                    args.inactivity > 0
                    and time.time() - last_activity > args.inactivity
                ):
                    runtime["stop_reason"] = "inactivity"
                    print("[AUTO-STOP] inactivity")
                    break

    except KeyboardInterrupt:
        runtime["stop_reason"] = "keyboard_interrupt"
        print("[CTRL-C] arrêt manuel")

    except Exception as exc:
        runtime["stop_reason"] = "error"
        print(f"[ERROR] {exc}", file=sys.stderr)

    finally:
        try:
            if browser:
                browser.close()
        except Exception:
            pass

        if not runtime["stop_reason"]:
            runtime["stop_reason"] = "completed"

        status = "emergency" if runtime["emergency"] else "stopped"

        conn.execute(
            """
            UPDATE sessions
            SET ended_at=?,
                status=?,
                mode=?,
                capture_enabled=?,
                stop_reason=?
            WHERE id=?
            """,
            (
                utc_now(),
                status,
                runtime["mode"],
                1,
                runtime["stop_reason"],
                session_id,
            ),
        )
        conn.commit()

        report = export_session(conn, session_id)

        if args.output:
            ensure_parent(args.output)

            with open(
                args.output,
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    report,
                    handle,
                    indent=2,
                    ensure_ascii=False,
                )

        if args.json or args.output:
            print(
                json.dumps(
                    report,
                    indent=2,
                    ensure_ascii=False,
                )
            )

        print("[STOP] navigateur fermé")
        print(f"[DB] {args.db}")
        conn.close()


if __name__ == "__main__":
    main()