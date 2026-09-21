#!/usr/bin/env python3
"""Scan a JSL tree for likely secrets and sensitive runtime artifacts."""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


DEFAULT_EXCLUDED_DIRS = {".git", ".venv", "__pycache__", "node_modules"}
SENSITIVE_FILENAMES = {
    "secrets.json": "cookie values or other secrets file",
    "cookie_log.jsonl": "cookie metadata log",
    "js_log.jsonl": "resource log",
    "in-scope.txt": "client scope file",
    "scope.txt": "client scope file",
}
SENSITIVE_SUFFIXES = (
    ".sqlite",
    ".sqlite3",
    ".sqlite3-wal",
    ".sqlite3-shm",
    ".db",
    ".db-wal",
    ".db-shm",
)
PATTERNS = (
    ("critical", "private key", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----")),
    ("critical", "GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("critical", "AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("high", "bearer token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}")),
    ("high", "JWT-like token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("high", "credential assignment", re.compile(r"\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|password|passwd)\s*[:=]\s*['\"]?[^\s'\"]{8,}")),
    ("medium", "database URL credentials", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/@:]+:[^\s/@]+@")),
)


def git_output(root, args):
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []
    return [line for line in result.stdout.splitlines() if line]


def relative_path(root, path):
    return path.relative_to(root).as_posix()


def should_skip(path, root):
    return any(part in DEFAULT_EXCLUDED_DIRS for part in path.relative_to(root).parts)


def classify_artifact(path):
    name = path.name.lower()
    if name in SENSITIVE_FILENAMES:
        return SENSITIVE_FILENAMES[name]
    if name.endswith(SENSITIVE_SUFFIXES):
        return "database or SQLite sidecar"
    if name.endswith(".jsonl") and any(word in name for word in ("cookie", "log", "event")):
        return "runtime JSONL log"
    if "response" in name or "capture" in name:
        return "captured response or local capture"
    return None


def scan_file(path, root, findings):
    artifact = classify_artifact(path)
    rel = relative_path(root, path)
    if artifact:
        findings.append({"severity": "high", "kind": "artifact", "path": rel, "detail": artifact})

    try:
        if path.stat().st_size > 10 * 1024 * 1024:
            findings.append({"severity": "medium", "kind": "skipped", "path": rel, "detail": "file larger than 10 MiB"})
            return
        data = path.read_bytes()
        text = data.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return

    for line_number, line in enumerate(text.splitlines(), 1):
        for severity, detail, pattern in PATTERNS:
            if pattern.search(line):
                findings.append({
                    "severity": severity,
                    "kind": "pattern",
                    "path": rel,
                    "line": line_number,
                    "detail": detail,
                })


def scan_tree(root):
    findings = []
    for path in root.rglob("*"):
        if path.is_file() and not should_skip(path, root):
            scan_file(path, root, findings)
    return findings


def scan_git_history(root, findings):
    commits = git_output(root, ["rev-list", "--all"])
    for commit in commits:
        files = git_output(root, ["ls-tree", "-r", "--name-only", commit])
        for file_name in files:
            path = root / file_name
            if should_skip(path, root):
                continue
            try:
                content = subprocess.run(
                    ["git", "-C", str(root), "show", f"{commit}:{file_name}"],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
            except (OSError, subprocess.CalledProcessError, UnicodeDecodeError):
                continue
            for severity, detail, pattern in PATTERNS:
                if pattern.search(content):
                    findings.append({
                        "severity": severity,
                        "kind": "history-pattern",
                        "commit": commit,
                        "path": file_name,
                        "detail": detail,
                    })


def main():
    parser = argparse.ArgumentParser(description="Scan JSL source, runtime artifacts, and Git history for exposure.")
    parser.add_argument("--root", default=Path(__file__).resolve().parent, type=Path)
    parser.add_argument("-o", "--output", type=Path, help="write the JSON exposure report")
    parser.add_argument("--history", action="store_true", help="also scan reachable Git history")
    args = parser.parse_args()
    root = args.root.resolve()
    findings = scan_tree(root)
    if args.history:
        scan_git_history(root, findings)

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings.sort(key=lambda item: (severity_order.get(item["severity"], 9), item.get("path", ""), item.get("line", 0)))
    report = {
        "root": str(root),
        "history_scanned": args.history,
        "findings": findings,
        "summary": {
            "critical": sum(item["severity"] == "critical" for item in findings),
            "high": sum(item["severity"] == "high" for item in findings),
            "medium": sum(item["severity"] == "medium" for item in findings),
            "total": len(findings),
        },
        "limitations": [
            "This is a heuristic scanner; it cannot prove that arbitrary client data is absent.",
            "Review scope files, SQLite databases, logs, response bodies, and Git history manually before publication.",
        ],
    }
    output = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
        os.chmod(args.output, 0o600)
    print(output)
    return 1 if report["summary"]["critical"] or report["summary"]["high"] else 0


if __name__ == "__main__":
    sys.exit(main())
