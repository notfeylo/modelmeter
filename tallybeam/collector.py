"""Read local session usage only. Prompts and responses never leave source files."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
SOURCES = {
    "claude": HOME / ".claude" / "projects",
    "codex": HOME / ".codex" / "sessions",
    "gemini": HOME / ".gemini" / "tmp",
}


def number(value):
    try:
        return max(0, int(value or 0))
    except (ValueError, TypeError):
        return 0


def timestamp(value):
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc).isoformat()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
        except ValueError:
            pass
    return None


def event(provider, model, when, session, usage, source):
    when = timestamp(when)
    if not when:
        return None
    inp = number(usage.get("input_tokens", usage.get("input", 0)))
    out = number(usage.get("output_tokens", usage.get("output", 0)))
    read = number(usage.get("cache_read_input_tokens", usage.get("cached_input_tokens", usage.get("cached", 0))))
    write = number(usage.get("cache_creation_input_tokens", usage.get("cache_write_input_tokens", 0)))
    if provider == "Codex":
        inp = max(0, inp - read - write)
    if provider == "Gemini":
        inp = max(0, inp - read)
        out += number(usage.get("thoughts"))
    if not inp + out + read + write:
        return None
    return {"provider": provider, "model": str(model or "Unknown model"), "timestamp": when,
            "session": str(session or "Unknown session"), "input": inp, "output": out,
            "cache_read": read, "cache_write": write, "total": inp + out + read + write,
            "source": source}


def json_lines(path):
    try:
        with path.open("r", encoding="utf-8", errors="replace") as stream:
            for line in stream:
                try:
                    value = json.loads(line)
                    if isinstance(value, dict):
                        yield value
                except json.JSONDecodeError:
                    continue
    except (OSError, UnicodeError):
        return


def source_files(root, suffix):
    """Use the optional Rust indexer when present; always keep a Python fallback."""
    binary = os.environ.get("TALLYBEAM_INDEXER")
    if binary and Path(binary).is_file():
        try:
            result = subprocess.run([binary, str(root), suffix], check=True, capture_output=True, text=True, timeout=30)
            return [Path(line) for line in result.stdout.splitlines() if line]
        except (OSError, subprocess.SubprocessError):
            pass
    return list(root.rglob("*" + suffix)) if root.exists() else []


def scan_claude(root):
    results = []
    for path in source_files(root, ".jsonl"):
        seen = {}
        for row in json_lines(path):
            if row.get("type") != "assistant":
                continue
            msg = row.get("message") or {}
            usage = msg.get("usage") or {}
            key = msg.get("id") or row.get("requestId") or row.get("uuid")
            item = event("Claude", msg.get("model"), row.get("timestamp"), row.get("sessionId") or path.stem, usage, "Claude Code")
            if item and key:
                # Streaming snapshots can repeat a message ID. Keep the final/largest usage.
                if key not in seen or item["total"] >= seen[key]["total"]:
                    seen[key] = item
        results.extend(seen.values())
    return results


def scan_codex(root):
    results, latest_limit = [], None
    for path in source_files(root, ".jsonl"):
        previous = None
        session, model = path.stem, "Codex"
        for row in json_lines(path):
            payload = row.get("payload") or {}
            if row.get("type") == "session_meta":
                session = (payload.get("id") or session)
            if row.get("type") == "turn_context":
                model = payload.get("model") or model
            if payload.get("type") != "token_count":
                continue
            limits = payload.get("rate_limits") or {}
            if limits and (not latest_limit or str(row.get("timestamp", "")) > latest_limit[0]):
                latest_limit = (str(row.get("timestamp", "")), limits)
            info = payload.get("info") or {}
            total = info.get("total_token_usage") or {}
            if not total:
                continue
            fields = ("input_tokens", "output_tokens", "cached_input_tokens", "cache_write_input_tokens")
            if previous is None or any(number(total.get(k)) < number(previous.get(k)) for k in fields):
                delta = total
            else:
                delta = {k: number(total.get(k)) - number(previous.get(k)) for k in fields}
            previous = total
            item = event("Codex", model, row.get("timestamp"), session, delta, "Codex CLI")
            if item:
                results.append(item)
    return results, (latest_limit[1] if latest_limit else None)


def scan_gemini(root):
    results = []
    for path in source_files(root, ".json"):
        if not path.name.startswith("session-"):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        for message in data.get("messages", []):
            if message.get("type") != "gemini":
                continue
            item = event("Gemini", message.get("model"), message.get("timestamp"), data.get("sessionId") or path.stem,
                         message.get("tokens") or {}, "Gemini CLI")
            if item:
                results.append(item)
    return results


def scan(enabled=None, roots=None):
    enabled = enabled or list(SOURCES)
    roots = roots or SOURCES
    events, connections = [], []
    limit = None
    for source, title, scanner in (("claude", "Claude Code", scan_claude),
                                   ("codex", "Codex CLI", scan_codex),
                                   ("gemini", "Gemini CLI", scan_gemini)):
        root = Path(roots[source])
        active = source in enabled
        found = root.exists()
        if active and found:
            if source == "codex":
                batch, limit = scanner(root)
            else:
                batch = scanner(root)
            events.extend(batch)
        connections.append({"id": source, "name": title, "path": str(root), "enabled": active,
                            "detected": found, "events": len(batch) if active and found else 0})
    return events, connections, limit
