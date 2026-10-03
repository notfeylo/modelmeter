"""Optional Claude Code status-line bridge: save only reported limit windows."""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOT = Path.home() / ".tallybeam" / "claude-limits.json"


def capture(payload, destination=SNAPSHOT):
    if not isinstance(payload, dict):
        return False
    limits = payload.get("rate_limits")
    if not isinstance(limits, dict):
        return False
    windows = {}
    for name in ("five_hour", "seven_day"):
        source = limits.get(name)
        if not isinstance(source, dict):
            continue
        used, reset = source.get("used_percentage"), source.get("resets_at")
        if isinstance(used, (int, float)) and isinstance(reset, (int, float)) and math.isfinite(used) and math.isfinite(reset):
            if 0 <= used <= 100 and reset > datetime.now(timezone.utc).timestamp():
                windows[name] = {"used_percent": used, "resets_at": int(reset)}
    if not windows:
        return False
    model = payload.get("model")
    identifier = model.get("id") if isinstance(model, dict) else None
    result = {"model": str(identifier or "Claude")[:120], "recorded_at": datetime.now(timezone.utc).isoformat(),
              "windows": windows, "source": "Claude Code statusLine"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f"{destination.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(result), encoding="utf-8")
    os.replace(temporary, destination)
    return True


def read_snapshot(path=SNAPSHOT):
    try:
        if path.stat().st_size > 64_000:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("windows"), dict):
            return None
        recorded = datetime.fromisoformat(data["recorded_at"])
        age = (datetime.now(timezone.utc) - recorded).total_seconds()
        if not -60 <= age <= 600:
            return None
        windows = data["windows"]
        for window in windows.values():
            if not isinstance(window, dict):
                return None
            percent = window.get("used_percent")
            reset = window.get("resets_at")
            if (not isinstance(percent, (int, float)) or isinstance(percent, bool) or
                    not math.isfinite(percent) or not 0 <= percent <= 100 or
                    not isinstance(reset, (int, float)) or isinstance(reset, bool) or
                    not math.isfinite(reset)):
                return None
        if not isinstance(data.get("model"), str) or len(data["model"]) > 120:
            return None
        return data
    except (OSError, ValueError, KeyError, TypeError):
        return None


def main():
    try:
        payload = json.load(sys.stdin)
        capture(payload)
        model = payload.get("model") if isinstance(payload, dict) else None
        name = model.get("display_name") if isinstance(model, dict) else None
        print(f"[{str(name or 'Claude')[:60]}]")
    except (OSError, ValueError, TypeError):
        print("[Claude]")


if __name__ == "__main__":
    main()
