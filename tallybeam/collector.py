"""Read local session usage only. Prompts and responses never leave source files."""
from __future__ import annotations

import json
import os
import subprocess
import sqlite3
from hashlib import blake2b
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME = Path.home()
SOURCES = {
    "claude": HOME / ".claude" / "projects",
    "codex": HOME / ".codex" / "sessions",
    "gemini": HOME / ".gemini" / "tmp",
    "opencode": HOME / ".local" / "share" / "opencode",
}


def source_roots(source, extras=None):
    """Known session locations plus user-added roots; never crawl the whole disk."""
    if source == "opencode" and os.environ.get("OPENCODE_DB_PATH"):
        candidates = [Path(os.environ["OPENCODE_DB_PATH"]).expanduser()]
    else:
        candidates = [SOURCES[source]]
        if source == "codex":
            candidates.append(SOURCES[source].parent / "archived_sessions")
        overrides = {
            "claude": ("CLAUDE_CONFIG_DIR", "projects"),
            "codex": ("CODEX_HOME", "sessions"),
            "gemini": ("GEMINI_CLI_HOME", ".gemini/tmp"),
            "opencode": ("XDG_DATA_HOME", "opencode"),
        }
        variable, child = overrides[source]
        if os.environ.get(variable):
            candidates.append(Path(os.environ[variable]).expanduser() / child)
            if source == "codex":
                candidates.append(Path(os.environ[variable]).expanduser() / "archived_sessions")
    if isinstance(extras, (str, os.PathLike)):
        extras = [extras]
    candidates.extend(Path(value).expanduser() for value in (extras or []))
    result, seen = [], set()
    for path in candidates:
        key = os.path.normcase(str(path.resolve(strict=False)))
        if key not in seen:
            seen.add(key)
            result.append(path)
    return [path for path in result if not any(other != path and other in path.parents for other in result)]


def number(value):
    try:
        result = int(value or 0)
        return result if 0 <= result <= 9_007_199_254_740_991 else 0
    except (ValueError, TypeError, OverflowError):
        return 0


def timestamp(value):
    parsed = None
    if isinstance(value, (int, float)):
        try:
            parsed = datetime.fromtimestamp(value, timezone.utc)
        except (ValueError, OverflowError, OSError):
            return None
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            return None
    if parsed is None or not datetime(2018, 1, 1, tzinfo=timezone.utc) <= parsed <= datetime.now(timezone.utc) + timedelta(days=1):
        return None
    return parsed.isoformat()


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


class FileCache:
    """Local normalized-counter cache; never stores transcript text or credentials."""

    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        try:
            self.db.execute("CREATE TABLE IF NOT EXISTS files (kind TEXT NOT NULL, path TEXT NOT NULL, size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(kind,path))")
        except sqlite3.DatabaseError:
            self.db.close()
            raise

    def read(self, kind, path, parse):
        try:
            before = path.stat()
        except OSError:
            return parse(path)
        key = str(path.resolve(strict=False))
        try:
            row = self.db.execute("SELECT size,mtime_ns,payload FROM files WHERE kind=? AND path=?", (kind, key)).fetchone()
        except sqlite3.DatabaseError:
            return parse(path)
        if row and (row[0], row[1]) == (before.st_size, before.st_mtime_ns):
            try:
                return json.loads(row[2])
            except (TypeError, ValueError):
                pass
        value = parse(path)
        try:
            after = path.stat()
            if (after.st_size, after.st_mtime_ns) == (before.st_size, before.st_mtime_ns):
                self.db.execute("INSERT OR REPLACE INTO files VALUES (?,?,?,?,?)",
                                (kind, key, before.st_size, before.st_mtime_ns, json.dumps(value)))
        except (OSError, sqlite3.DatabaseError):
            pass
        return value

    def close(self):
        try:
            self.db.commit()
        except sqlite3.DatabaseError:
            pass
        finally:
            self.db.close()


def source_signature(enabled=None, roots=None):
    """Fingerprint local data and OpenCode WAL files without reading their contents."""
    enabled = list(SOURCES) if enabled is None else enabled
    roots = roots or {}
    digest = blake2b(digest_size=16)
    for source in sorted(enabled):
        digest.update(source.encode())
        paths = []
        for root in source_roots(source, roots.get(source)):
            digest.update(str(root.resolve(strict=False)).encode("utf-8", errors="replace"))
            if source == "opencode":
                found = [root] if root.is_file() else source_files(root, ".db")
                found = [p for p in found if (root.is_file() and p == root) or
                         (p.name.startswith("opencode") and p.name != "opencode-auth.db")]
                paths.extend(found + [Path(str(path) + "-wal") for path in found])
            else:
                suffix = ".json" if source == "gemini" else ".jsonl"
                found = source_files(root, suffix)
                paths.extend(p for p in found if source != "gemini" or p.name.startswith("session-"))
        for path in sorted(set(paths)):
            try:
                stat = path.stat()
            except OSError:
                continue
            digest.update(str(path).encode("utf-8", errors="replace"))
            digest.update(f":{stat.st_size}:{stat.st_mtime_ns}".encode())
    return digest.digest()


def _scan_claude_file(path):
    seen = {}
    for row in json_lines(path):
        if row.get("type") != "assistant":
            continue
        msg = row.get("message") or {}
        if not isinstance(msg, dict):
            continue
        usage = msg.get("usage") or {}
        if not isinstance(usage, dict):
            continue
        key = msg.get("id") or row.get("requestId") or row.get("uuid")
        item = event("Claude", msg.get("model"), row.get("timestamp"), row.get("sessionId") or path.stem, usage, "Claude Code")
        if item and key:
            item["_message_id"] = str(key)
            if key not in seen or item["total"] >= seen[key]["total"]:
                seen[key] = item
    return list(seen.values())


def scan_claude(root, file_cache=None):
    seen = {}
    for path in source_files(root, ".jsonl"):
        batch = file_cache.read("claude-v3", path, _scan_claude_file) if file_cache else _scan_claude_file(path)
        for item in batch:
            key = (item["session"], item["_message_id"])
            if key not in seen or item["total"] >= seen[key]["total"]:
                seen[key] = item
    return [{key: value for key, value in item.items() if key != "_message_id"} for item in seen.values()]


def _scan_codex_file(path):
    results, latest_limit = [], None
    previous = None
    session, model = path.stem, "Unknown model"
    for row in json_lines(path):
        payload = row.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        if row.get("type") == "session_meta":
            session = (payload.get("id") or session)
        if row.get("type") == "turn_context":
            model = payload.get("model") or model
        if payload.get("type") != "token_count":
            continue
        limits = payload.get("rate_limits") or {}
        if not isinstance(limits, dict):
            limits = {}
        if limits and (not latest_limit or str(row.get("timestamp", "")) > latest_limit[0]):
            latest_limit = (str(row.get("timestamp", "")), limits)
        info = payload.get("info") or {}
        if not isinstance(info, dict):
            continue
        total = info.get("total_token_usage") or {}
        if not isinstance(total, dict) or not total:
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
    return results, latest_limit


def scan_codex(root, file_cache=None):
    results, latest_limit = [], None
    for path in source_files(root, ".jsonl"):
        batch, limit = (file_cache.read("codex-v4", path, _scan_codex_file)
                        if file_cache else _scan_codex_file(path))
        results.extend(batch)
        if limit and (not latest_limit or limit[0] > latest_limit[0]):
            latest_limit = limit
    return results, ({**latest_limit[1], "recorded_at": latest_limit[0]} if latest_limit else None)


def _scan_gemini_file(path):
    results = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return results
    if not isinstance(data, dict) or not isinstance(data.get("messages"), list):
        return results
    for message in data.get("messages", []):
        if not isinstance(message, dict) or message.get("type") != "gemini":
            continue
        tokens = message.get("tokens") or {}
        if not isinstance(tokens, dict):
            continue
        item = event("Gemini", message.get("model"), message.get("timestamp"), data.get("sessionId") or path.stem,
                     tokens, "Gemini CLI")
        if item:
            results.append(item)
    return results


def scan_gemini(root, file_cache=None):
    results = []
    for path in source_files(root, ".json"):
        if path.name.startswith("session-"):
            results.extend(file_cache.read("gemini-v2", path, _scan_gemini_file) if file_cache else _scan_gemini_file(path))
    return results


def scan_opencode(root):
    """Read OpenCode V1/V2 assistant usage from a read-only SQLite connection."""
    results = []
    explicit = os.environ.get("OPENCODE_DB_PATH")
    paths = [root] if root.is_file() else source_files(root, ".db")
    for path in paths:
        if (not explicit and not root.is_file() and not path.name.startswith("opencode")) or path.name == "opencode-auth.db":
            continue
        try:
            with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
                tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                candidates = [t for t in ("message", "session_message") if t in tables]
                if not candidates:
                    continue
                table = max(candidates, key=lambda t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
                columns = {r[1] for r in db.execute(f"PRAGMA table_info({table})")}
                if not {"id", "session_id", "data"}.issubset(columns):
                    continue
                session_info = {}
                for session_table in ("session", "session_v2"):
                    if session_table not in tables:
                        continue
                    session_columns = {r[1] for r in db.execute(f"PRAGMA table_info({session_table})")}
                    if "id" not in session_columns:
                        continue
                    selected = [col if col in session_columns else "NULL" for col in ("directory", "parent_id")]
                    for sid, directory, parent in db.execute(
                        f"SELECT id, {', '.join(selected)} FROM {session_table}"
                    ):
                        session_info[sid] = {"directory": directory, "child": parent is not None}
                compactions = {}
                if table == "message" and "part" in tables:
                    part_columns = {r[1] for r in db.execute("PRAGMA table_info(part)")}
                    if {"session_id", "time_created", "data"}.issubset(part_columns):
                        for sid, at, raw in db.execute("SELECT session_id, time_created, data FROM part"):
                            try:
                                payload = json.loads(raw)
                                if isinstance(payload, dict) and payload.get("type") == "compaction":
                                    compactions.setdefault(sid, []).append(number(at))
                            except (TypeError, ValueError):
                                continue
                elif table == "session_message" and "type" in columns and "time_created" in columns:
                    for sid, at, raw in db.execute(
                        "SELECT session_id, time_created, data FROM session_message WHERE type = 'compaction'"
                    ):
                        try:
                            payload = json.loads(raw)
                            if isinstance(payload, dict) and payload.get("status") == "completed":
                                compactions.setdefault(sid, []).append(number(at))
                        except (TypeError, ValueError):
                            continue
                where = "WHERE type = 'assistant'" if "type" in columns else ""
                batch = []
                for ident, session, raw in db.execute(f"SELECT id, session_id, data FROM {table} {where}"):
                    try:
                        data = json.loads(raw)
                    except (TypeError, ValueError):
                        continue
                    if not isinstance(data, dict):
                        continue
                    if table == "message" and data.get("role") != "assistant":
                        continue
                    info = session_info.get(session, {})
                    if ".opencode" in (info.get("directory") or ""):
                        continue
                    tokens = data.get("tokens") or {}
                    if not isinstance(tokens, dict):
                        continue
                    cache = tokens.get("cache") or {}
                    if not isinstance(cache, dict):
                        cache = {}
                    model = data.get("model") or {}
                    if not isinstance(model, dict):
                        model = {}
                    timing = data.get("time") or {}
                    if not isinstance(timing, dict):
                        continue
                    when = number(timing.get("completed")) or number(timing.get("created"))
                    if not when:
                        continue
                    item = event(str(data.get("providerID") or model.get("providerID") or "OpenCode"),
                                 data.get("modelID") or model.get("id"), when / 1000,
                                 session, {"input": tokens.get("input"), "output": tokens.get("output"),
                                           "cache_read_input_tokens": cache.get("read"),
                                           "cache_write_input_tokens": cache.get("write")}, "OpenCode")
                    if item:
                        item["reasoning"] = number(tokens.get("reasoning"))
                        item["total"] += item["reasoning"]
                        start, end = number(timing.get("created")), number(timing.get("completed"))
                        if end > start > 0 and not info.get("child"):
                            item["runtime_start"] = start
                            item["runtime_end"] = end
                            item["runtime"] = end - start
                        batch.append(item)
                previous_by_session = {}
                for item in sorted(batch, key=lambda e: e["timestamp"]):
                    sid = item["session"]
                    at = int(datetime.fromisoformat(item["timestamp"]).timestamp() * 1000)
                    previous = previous_by_session.get(sid)
                    if previous is not None:
                        item["compaction_before"] = any(previous < c < at for c in compactions.get(sid, ()))
                    previous_by_session[sid] = at
                results.extend(batch)
        except (sqlite3.Error, OSError):
            continue
    return results


def scan(enabled=None, roots=None, cache_path=None):
    enabled = list(SOURCES) if enabled is None else enabled
    roots = roots or {}
    events, connections, seen_events = [], [], set()
    limit = None
    try:
        file_cache = FileCache(cache_path) if cache_path else None
    except (OSError, sqlite3.DatabaseError):
        file_cache = None
    try:
        for source, title, scanner in (("claude", "Claude Code", scan_claude),
                                       ("codex", "Codex CLI", scan_codex),
                                       ("gemini", "Gemini CLI", scan_gemini),
                                       ("opencode", "OpenCode", scan_opencode)):
            paths = source_roots(source, roots.get(source))
            active = source in enabled
            count = 0
            for root in paths:
                if active and root.exists():
                    if source == "codex":
                        batch, found_limit = scanner(root, file_cache)
                        if found_limit and (not limit or found_limit["recorded_at"] > limit["recorded_at"]):
                            limit = found_limit
                    elif source == "opencode":
                        batch = scanner(root)
                    else:
                        batch = scanner(root, file_cache)
                    for item in batch:
                        identity = (item["source"], item["provider"], item["session"], item["timestamp"],
                                    item["model"], item["input"], item["output"], item["cache_read"], item["cache_write"],
                                    item.get("reasoning", 0))
                        if identity not in seen_events:
                            seen_events.add(identity)
                            events.append(item)
                            count += 1
            connections.append({"id": source, "name": title, "path": "; ".join(map(str, paths)),
                                "paths": [str(path) for path in paths], "enabled": active,
                                "detected": any(path.exists() for path in paths), "events": count})
    finally:
        if file_cache:
            file_cache.close()
    return events, connections, limit
