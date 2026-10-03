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
        data = json.loads(path.read_text(encoding="utf-8"))
        recorded = datetime.fromisoformat(data["recorded_at"])
        if (datetime.now(timezone.utc) - recorded).total_seconds() > 600:
            return None
        return data if isinstance(data.get("windows"), dict) else None
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
