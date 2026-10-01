"""Dashboard aggregates over local usage metadata. No prompt content is exposed."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256

FIELDS = ("total", "active", "input", "output", "reasoning", "cache_read", "cache_write",
          "cache_miss", "cache_expected", "cache_hit_rate", "runtime", "runtime_dedup", "user_message_count")


def empty():
    return {field: 0 for field in FIELDS}


def event_metrics(event):
    row = empty()
    for key in ("total", "input", "output", "cache_read", "cache_write"):
        row[key] = event.get(key, 0)
    row["reasoning"] = event.get("reasoning", 0)
    row["active"] = row["input"] + row["output"] + row["reasoning"]
    row["runtime"] = event.get("runtime", 0)
    row["user_message_count"] = 1
    return row


def add(target, source):
    for key in FIELDS:
        if key != "cache_hit_rate":
            target[key] += source[key]


def selected(events, range_value):
    now = datetime.now(timezone.utc)
    days = None if range_value == "all" else int(range_value)
    since = (now - timedelta(days=days - 1)).date() if days else None
    return [e for e in events if since is None or datetime.fromisoformat(e["timestamp"]).astimezone().date() >= since]


def _annotated(events):
    grouped = defaultdict(list)
    for event in events:
        grouped[(event.get("source", event["provider"]), event["session"])].append(event)
    for _, group in grouped.items():
        previous = None
        for index, event in enumerate(sorted(group, key=lambda e: e["timestamp"])):
            same_model = previous and previous["provider"] == event["provider"] and previous["model"] == event["model"]
            real_session = event.get("session") not in (None, "", "Imported")
            expected = previous["total"] if real_session and same_model and previous["cache_read"] > 0 and not event.get("compaction_before") else None
            miss = max(0, expected - event["cache_read"]) if expected is not None else None
            key = (event.get("source", event["provider"]), event["session"], event["provider"], event["model"])
            yield key, index, event, expected, miss
            previous = event


def merged_runtime(intervals):
    total, end = 0, None
    for start, finish in sorted(intervals):
        if finish <= start:
            continue
        if end is None or start >= end:
            total += finish - start
            end = finish
        elif finish > end:
            total += finish - end
            end = finish
    return total


def _range_days(events, range_value):
    today = datetime.now().date()
    if range_value == "all" and events:
        first = min(datetime.fromisoformat(e["timestamp"]).astimezone().date() for e in events)
    else:
        first = today - timedelta(days=(int(range_value) if range_value != "all" else 30) - 1)
    return [(first + timedelta(days=i)).isoformat() for i in range((today - first).days + 1)]


def usage_payload(all_events, range_value="30"):
    if range_value not in ("7", "30", "90", "180", "365", "all"):
        range_value = "30"
    events = selected(all_events, range_value)
    day_names = _range_days(events, range_value)
    hourly_trend = range_value == "7"
    day_buckets = ([f"{name}T{hour:02d}" for name in day_names for hour in range(24)]
                   if hourly_trend else day_names)
    days = {name: empty() for name in day_buckets}
    summary = empty()
    models, providers, provider_models, trends, heat = {}, {}, {}, {}, {}
    intervals = defaultdict(list)
    hourly = len(day_names) <= 90
    for _, _, event, expected, miss in _annotated(events):
        local = datetime.fromisoformat(event["timestamp"]).astimezone()
        date = local.date().isoformat()
        if date not in day_names:
            continue
        day_bucket = f"{date}T{local.hour:02d}" if hourly_trend else date
        metrics = event_metrics(event)
        if expected is not None:
            metrics["cache_expected"] = expected
            metrics["cache_miss"] = miss
        add(summary, metrics)
        add(days[day_bucket], metrics)
        model, provider = event["model"], event["provider"]
        add(models.setdefault(model, empty()), metrics)
        add(providers.setdefault(provider, empty()), metrics)
        pm = (provider, model)
        add(provider_models.setdefault(pm, empty()), metrics)
        add(trends.setdefault(pm, {}).setdefault(date, empty()), metrics)
        bucket = f"{date}T{local.hour // 2 * 2:02d}" if hourly else date
        add(heat.setdefault(bucket, empty()), metrics)
        if event.get("runtime_start") is not None and event.get("runtime_end") is not None:
            interval = (event["runtime_start"], event["runtime_end"])
            for name in ("summary", f"day:{day_bucket}", f"model:{model}", f"provider:{provider}",
                         f"pm:{provider}\0{model}", f"trend:{provider}\0{model}\0{date}", f"heat:{bucket}"):
                intervals[name].append(interval)
    for date in day_names:
        if hourly:
            for hour in range(0, 24, 2):
                heat.setdefault(f"{date}T{hour:02d}", empty())
        else:
            heat.setdefault(date, empty())
    summary["runtime_dedup"] = merged_runtime(intervals["summary"])
    for key, value in days.items():
        value["runtime_dedup"] = merged_runtime(intervals[f"day:{key}"])
    for key, value in models.items():
        value["runtime_dedup"] = merged_runtime(intervals[f"model:{key}"])
    for key, value in providers.items():
        value["runtime_dedup"] = merged_runtime(intervals[f"provider:{key}"])
    for (provider, model), value in provider_models.items():
        value["runtime_dedup"] = merged_runtime(intervals[f"pm:{provider}\0{model}"])
    for (provider, model), values in trends.items():
        for date, value in values.items():
            value["runtime_dedup"] = merged_runtime(intervals[f"trend:{provider}\0{model}\0{date}"])
    for key, value in heat.items():
        value["runtime_dedup"] = merged_runtime(intervals[f"heat:{key}"])
    def named(key, value):
        return {"name": key, **value}
    def pm_named(key, value):
        return {"provider": key[0], "model": key[1], **value}
    local_days = [datetime.fromisoformat(e["timestamp"]).astimezone().date().isoformat() for e in all_events]
    now = datetime.now().astimezone()
    return {
        "meta": {"database": "local sources", "databasePath": "", "generatedAt": now.isoformat(),
                 "timezone": now.tzname() or "local", "firstDay": day_names[0], "lastDay": day_names[-1],
                 "availableFirstDay": min(local_days) if local_days else None,
                 "availableLastDay": max(local_days) if local_days else None, "range": range_value,
                 "assistantMessageCount": len(events), "scannedRows": len(all_events)},
        "summary": summary,
        "days": [{"date": day, **days[day]} for day in day_buckets],
        "models": [named(k, v) for k, v in sorted(models.items(), key=lambda x: x[1]["total"], reverse=True)],
        "providers": [named(k, v) for k, v in sorted(providers.items(), key=lambda x: x[1]["total"], reverse=True)],
        "providerModels": [pm_named(k, v) for k, v in provider_models.items()],
        "providerModelTrends": [{"provider": k[0], "model": k[1],
                                 "days": [{"date": d, **v.get(d, empty())} for d in day_names]}
                                for k, v in trends.items()],
        "heatmap": {"granularity": "hourly" if hourly else "daily", "intervalHours": 2 if hourly else 24,
                    "data": [{"date": k, **v} for k, v in sorted(heat.items())]},
    }


def session_key(key):
    return sha256("\0".join(key).encode()).hexdigest()[:24]


def cache_miss_sessions(all_events, range_value="30", date=None):
    events = selected(all_events, range_value)
    selected_ids = {id(event) for event in events}
    groups = defaultdict(list)
    for key, index, event, expected, miss in _annotated(all_events):
        if id(event) not in selected_ids:
            continue
        if date and datetime.fromisoformat(event["timestamp"]).astimezone().date().isoformat() != date:
            continue
        groups[key].append((index, event, expected, miss))
    rows = []
    for key, records in groups.items():
        total_expected = sum(r[2] or 0 for r in records)
        total_miss = sum(r[3] or 0 for r in records)
        if not total_expected:
            continue
        times = [int(datetime.fromisoformat(r[1]["timestamp"]).timestamp() * 1000) for r in records]
        rows.append({"sessionId": session_key(key), "title": records[0][1].get("title") or key[1], "provider": key[2], "model": key[3],
                     "cacheMiss": total_miss, "cacheExpected": total_expected,
                     "missRate": total_miss / total_expected * 100, "pairs": sum(r[2] is not None for r in records),
                     "firstTime": min(times), "lastTime": max(times), "noCache": False})
    rows.sort(key=lambda r: r["cacheMiss"], reverse=True)
    return {"range": range_value, "totalMiss": sum(r["cacheMiss"] for r in rows),
            "totalExpected": sum(r["cacheExpected"] for r in rows), "sessions": rows[:200]}


def cache_miss_detail(all_events, identity):
    records = [(key, index, event, expected, miss) for key, index, event, expected, miss in _annotated(all_events)
               if session_key(key) == identity]
    if not records:
        return None
    key = records[0][0]
    return {"sessionId": identity, "title": records[0][2].get("title") or key[1], "provider": key[2], "model": key[3], "noCache": False,
            "messages": [{"id": f"{identity}-{index}", "idx": index,
                          "ts": int(datetime.fromisoformat(e["timestamp"]).timestamp() * 1000),
                          "total": e["total"], "cacheRead": e["cache_read"], "cacheWrite": e["cache_write"],
                          "input": e["input"], "output": e["output"], "reasoning": e.get("reasoning", 0),
                          "prevTotal": expected, "miss": miss}
                         for _, index, e, expected, miss in records]}
