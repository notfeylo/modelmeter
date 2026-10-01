from __future__ import annotations

import argparse
import json
import sqlite3
import threading
import time
import webbrowser
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .collector import scan, timestamp, number
from .usage import usage_payload, cache_miss_sessions, cache_miss_detail

DATA = Path.home() / ".tallybeam"
DB = DATA / "tallybeam.sqlite3"
CONFIG = DATA / "config.json"
lock = threading.Lock()
cache = {"at": 0, "events": [], "connections": [], "limits": None}


def config():
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
        if isinstance(data.get("enabled"), list):
            return data
    except (OSError, ValueError):
        pass
    return {"enabled": ["claude", "codex", "gemini", "opencode"]}


def database():
    DATA.mkdir(exist_ok=True)
    db = sqlite3.connect(DB)
    db.execute("CREATE TABLE IF NOT EXISTS imported (id TEXT PRIMARY KEY, provider TEXT NOT NULL, model TEXT NOT NULL, timestamp TEXT NOT NULL, session TEXT NOT NULL, input INTEGER NOT NULL, output INTEGER NOT NULL, cache_read INTEGER NOT NULL, cache_write INTEGER NOT NULL)")
    return db


def imported():
    with closing(database()) as db:
        rows = db.execute("SELECT provider,model,timestamp,session,input,output,cache_read,cache_write FROM imported").fetchall()
    return [dict(provider=r[0], model=r[1], timestamp=r[2], session=r[3], input=r[4], output=r[5],
                 cache_read=r[6], cache_write=r[7], total=sum(r[4:8]), source="CSV import") for r in rows]


def refresh(force=False):
    with lock:
        if force or time.monotonic() - cache["at"] > 20:
            events, connections, limits = scan(config()["enabled"])
            cache.update(at=time.monotonic(), events=events + imported(), connections=connections, limits=limits)
        return dict(cache)


def overview(days=30, provider="all"):
    state = refresh()
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    events = [e for e in state["events"] if datetime.fromisoformat(e["timestamp"]) >= since and
              (provider == "all" or e["provider"].lower() == provider.lower())]
    daily, hourly, providers, models = defaultdict(lambda: {"tokens": 0, "messages": 0}), defaultdict(int), Counter(), Counter()
    for e in events:
        day = e["timestamp"][:10]
        daily[day]["tokens"] += e["total"]
        daily[day]["messages"] += 1
        hourly[e["timestamp"][:13]] += e["total"]
        providers[e["provider"]] += e["total"]
        models[e["model"]] += e["total"]
    points = []
    for offset in range(days - 1, -1, -1):
        day = (now - timedelta(days=offset)).date().isoformat()
        points.append({"date": day, **daily[day]})
    total = sum(e["total"] for e in events)
    return {"generated_at": now.isoformat(), "days": days, "provider": provider,
            "total": total, "today": daily[now.date().isoformat()]["tokens"], "messages": len(events),
            "daily_average": round(total / days), "peak": max(points, key=lambda x: x["tokens"]),
            "breakdown": {k: sum(e[k] for e in events) for k in ("input", "output", "cache_read", "cache_write")},
            "daily": points, "hourly": [{"hour": k, "tokens": v} for k, v in sorted(hourly.items())],
            "providers": providers, "models": models.most_common(8),
            "connections": state["connections"] + [{"id": "grok", "name": "Grok / xAI", "path": "CSV import", "enabled": True, "detected": any(e["provider"] == "Grok" for e in state["events"]), "events": sum(e["provider"] == "Grok" for e in state["events"])}],
            "codex_limits": state["limits"],
            "sessions": sessions(events)[:30]}


def sessions(events):
    groups = {}
    for e in events:
        key = (e["provider"], e["session"])
        if key not in groups:
            groups[key] = {"provider": e["provider"], "session": e["session"], "model": e["model"],
                           "started": e["timestamp"], "last": e["timestamp"], "messages": 0, "total": 0,
                           "input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "source": e["source"]}
        row = groups[key]
        row["started"] = min(row["started"], e["timestamp"])
        row["last"] = max(row["last"], e["timestamp"])
        row["messages"] += 1
        for field in ("total", "input", "output", "cache_read", "cache_write"):
            row[field] += e[field]
    return sorted(groups.values(), key=lambda x: x["last"], reverse=True)


class Handler(BaseHTTPRequestHandler):
    server_version = "Tallybeam/0.1"

    def log_message(self, format, *args):
        pass

    def respond(self, data, status=200):
        body = json.dumps(data, default=list).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        uri = urlparse(self.path)
        if uri.path == "/api/usage":
            value = parse_qs(uri.query).get("range", ["30"])[0]
            return self.respond(usage_payload(refresh()["events"], value))
        if uri.path == "/api/limits":
            return self.respond({"codex": refresh()["limits"]})
        if uri.path == "/api/cache-miss/sessions":
            params = parse_qs(uri.query)
            value = params.get("range", ["30"])[0]
            if value not in ("7", "30", "90", "180", "365", "all"):
                value = "30"
            day = params.get("date", [None])[0]
            return self.respond(cache_miss_sessions(refresh()["events"], value, day))
        if uri.path.startswith("/api/cache-miss/session/"):
            identity = uri.path.rsplit("/", 1)[-1]
            detail = cache_miss_detail(refresh()["events"], identity)
            return self.respond(detail if detail else {"error": "Session not found"}, 200 if detail else 404)
        if uri.path == "/api/overview":
            params = parse_qs(uri.query)
            try:
                days = int(params.get("days", ["30"])[0])
            except ValueError:
                days = 30
            days = max(1, min(days, 365))
            provider = params.get("provider", ["all"])[0]
            if provider.lower() not in ("all", "claude", "codex", "gemini", "grok", "opencode"):
                provider = "all"
            return self.respond(overview(days, provider))
        if uri.path == "/api/health":
            return self.respond({"ok": True, "version": "0.1.0"})
        if uri.path == "/api/session":
            params = parse_qs(uri.query)
            provider = params.get("provider", [""])[0]
            session_id = params.get("id", [""])[0]
            if not provider or not session_id or len(session_id) > 200:
                return self.respond({"error": "Provider and session required"}, 400)
            events = sorted((e for e in refresh()["events"] if e["provider"] == provider and e["session"] == session_id), key=lambda e: e["timestamp"])
            return self.respond({"provider": provider, "session": session_id, "events": events[:5000]})
        name = "index.html" if uri.path == "/" else uri.path.lstrip("/")
        if not (name == "index.html" or name == "logo.svg" or (name.startswith("assets/") and "/" not in name[7:])):
            return self.respond({"error": "Not found"}, 404)
        resource = files("tallybeam") / "static" / name
        if not resource.is_file():
            return self.respond({"error": "Not found"}, 404)
        body = resource.read_bytes()
        mime = {"html": "text/html", "js": "application/javascript", "css": "text/css", "svg": "image/svg+xml", "woff2": "font/woff2"}.get(name.split(".")[-1], "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; font-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        origin = self.headers.get("Origin")
        host = self.headers.get("Host")
        if origin and origin != "http://" + host:
            return self.respond({"error": "Invalid origin"}, 403)
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.respond({"error": "JSON required"}, 415)
        size = number(self.headers.get("Content-Length"))
        if size > 2_000_000:
            return self.respond({"error": "Request too large"}, 413)
        try:
            data = json.loads(self.rfile.read(size))
        except ValueError:
            return self.respond({"error": "Invalid JSON"}, 400)
        if self.path == "/api/refresh":
            refresh(True)
            return self.respond({"ok": True})
        if self.path == "/api/connections":
            enabled = data.get("enabled") if isinstance(data, dict) else None
            if not isinstance(enabled, list) or any(x not in ("claude", "codex", "gemini", "opencode") for x in enabled):
                return self.respond({"error": "Invalid connections"}, 400)
            DATA.mkdir(exist_ok=True)
            CONFIG.write_text(json.dumps({"enabled": enabled}), encoding="utf-8")
            refresh(True)
            return self.respond({"ok": True})
        if self.path == "/api/import":
            if not isinstance(data, list) or len(data) > 5000:
                return self.respond({"error": "Send at most 5,000 rows"}, 400)
            rows = []
            for i, row in enumerate(data):
                if not isinstance(row, dict):
                    return self.respond({"error": f"Invalid row {i+1}"}, 400)
                when = timestamp(row.get("timestamp"))
                provider = str(row.get("provider", ""))[:40].strip()
                if provider not in ("Claude", "Codex", "Gemini", "Grok", "OpenCode", "Other") or not when:
                    return self.respond({"error": f"Invalid provider or timestamp in row {i+1}"}, 400)
                values = [number(row.get(k)) for k in ("input", "output", "cache_read", "cache_write")]
                ident = str(row.get("id") or f"{provider}:{row.get('session')}:{when}:{i}")[:200]
                rows.append((ident, provider, str(row.get("model") or "Unknown")[:100], when,
                             str(row.get("session") or "Imported")[:100], *values))
            with closing(database()) as db:
                db.executemany("INSERT OR REPLACE INTO imported VALUES (?,?,?,?,?,?,?,?,?)", rows)
                db.commit()
            refresh(True)
            return self.respond({"imported": len(rows)})
        return self.respond({"error": "Not found"}, 404)


def main():
    parser = argparse.ArgumentParser(description="Local AI usage dashboard")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Tallybeam listening at http://127.0.0.1:{args.port}", flush=True)
    if not args.no_browser:
        webbrowser.open(f"http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
