"""Evidence-grounded usage explanations and a small validated neural forecast.

Neither retrieval nor learned outputs are ever added to recorded token totals.
"""
from __future__ import annotations

import json
import math
import random
import re
import urllib.request
from collections import Counter
from datetime import datetime, timedelta

from .usage import provider_name
from .discovery import loopback_opener


def _recent(events, days=90):
    cutoff = datetime.now().astimezone().date() - timedelta(days=days - 1)
    for event in events:
        try:
            day = datetime.fromisoformat(event["timestamp"]).astimezone().date()
        except (KeyError, ValueError, TypeError):
            continue
        if day >= cutoff:
            yield day, event


def recorded_facts(events, days=90):
    """Retrieve aggregate counter evidence, never transcript or Obsidian text."""
    by_provider, by_model, by_day = Counter(), Counter(), Counter()
    for day, event in _recent(events, days):
        total = int(event.get("total") or 0)
        if total <= 0:
            continue
        provider = provider_name(event)
        by_provider[provider] += total
        by_model[(provider, str(event.get("model") or "Unknown model"))] += total
        by_day[day.isoformat()] += total
    facts = []
    if by_day:
        facts.append({"id": f"total:{days}d", "text": f"Across all sources, {sum(by_day.values()):,} tokens were recorded in the last {days} days", "tokens": sum(by_day.values())})
    for provider, total in by_provider.most_common():
        facts.append({"id": f"provider:{provider}", "text": f"{provider} recorded {total:,} tokens in the last {days} days", "tokens": total})
    for (provider, model), total in by_model.most_common(40):
        facts.append({"id": f"model:{provider}/{model}", "text": f"{provider} model {model} recorded {total:,} tokens in the last {days} days", "tokens": total})
    for day, total in sorted(by_day.items(), reverse=True)[:days]:
        facts.append({"id": f"day:{day}", "text": f"On {day}, {total:,} tokens were recorded", "tokens": total})
    return facts


def retrieve_facts(question, facts, limit=6):
    """Sparse lexical retrieval over aggregate evidence with stable ranking."""
    terms = set(re.findall(r"[a-z0-9][a-z0-9.-]+", question.casefold()))
    question_lower = question.casefold()
    requested_day = None
    if "today" in terms:
        requested_day = datetime.now().astimezone().date().isoformat()
    elif "yesterday" in terms:
        requested_day = (datetime.now().astimezone().date() - timedelta(days=1)).isoformat()
    scored = []
    for fact in facts:
        haystack = fact["id"].casefold() + " " + fact["text"].casefold()
        overlap = sum(1 for term in terms if term in haystack)
        if overlap or not terms or (requested_day and fact["id"] == f"day:{requested_day}"):
            intent = (3 if requested_day and fact["id"] == f"day:{requested_day}" else 0)
            if "model" in terms and fact["id"].startswith("model:"):
                intent += 2
            if "provider" in terms and fact["id"].startswith("provider:"):
                intent += 2
            if "total" in terms and fact["id"].startswith("total:"):
                intent += 2
            scored.append((intent, overlap, fact["tokens"], fact))
    if not scored:
        scored = [(0, 0, fact["tokens"], fact) for fact in facts]
    scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    return [item[3] for item in scored[:limit]]


def grounded_answer(question, facts):
    matches = retrieve_facts(question, facts)
    if not matches:
        return {"answer": "No recorded token usage is available for that period.", "evidence": [], "method": "recorded facts"}
    return {"answer": ". ".join(item["text"] for item in matches[:3]) + ".", "evidence": matches,
            "method": "recorded facts"}


def ask_local_model(question, facts, model):
    """Optional local RAG generation; only aggregate counters go to loopback Ollama."""
    result = grounded_answer(question, facts)
    if not model:
        return result
    prompt = ("Answer the user's question using only the numbered recorded facts below. "
              "If they do not answer it, say the data is unavailable. Never invent a quota, reset time, or token count. "
              "Keep the answer under 100 words.\n\n"
              + "\n".join(f"[{i+1}] {item['text']}" for i, item in enumerate(result["evidence"]))
              + f"\n\nQuestion: {question}")
    body = json.dumps({"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0}}).encode()
    request = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
    try:
        opener = loopback_opener()
        with opener.open(request, timeout=20) as response:
            data = json.loads(response.read(50_000))
        answer = str(data.get("response") or "").strip()[:3000]
        if answer:
            return {**result, "answer": answer, "method": "local Ollama RAG; verify against evidence"}
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    return result


def _features(values, index, scale):
    return [math.log1p(values[index - lag]) / math.log1p(scale) for lag in (1, 2, 3, 7)] + [
        math.sin(2 * math.pi * index / 7), math.cos(2 * math.pi * index / 7)]


def _fit_neural(samples, epochs=180):
    """Train a deterministic one-hidden-layer regressor on log-scaled daily usage."""
    rng = random.Random(7)
    width = 8
    first = [[rng.uniform(-0.15, 0.15) for _ in range(6)] for _ in range(width)]
    bias = [0.0] * width
    second = [rng.uniform(-0.15, 0.15) for _ in range(width)]
    output_bias = 0.0
    for _ in range(epochs):
        for features, target in samples:
            hidden = [math.tanh(sum(w * x for w, x in zip(weights, features)) + bias[j]) for j, weights in enumerate(first)]
            prediction = sum(w * h for w, h in zip(second, hidden)) + output_bias
            error = max(-2.0, min(2.0, prediction - target))
            old_second = second[:]
            for j in range(width):
                second[j] -= 0.015 * error * hidden[j]
                delta = error * old_second[j] * (1 - hidden[j] ** 2)
                bias[j] -= 0.015 * delta
                for k in range(6):
                    first[j][k] -= 0.015 * delta * features[k]
            output_bias -= 0.015 * error
    return first, bias, second, output_bias


def _predict(weights, features):
    first, bias, second, output_bias = weights
    hidden = [math.tanh(sum(w * x for w, x in zip(row, features)) + bias[j]) for j, row in enumerate(first)]
    return sum(w * h for w, h in zip(second, hidden)) + output_bias


def neural_usage_forecast(events):
    """Publish a next-day estimate only if holdout error beats a simple baseline."""
    today = datetime.now().astimezone().date()
    start = today - timedelta(days=89)
    by_day = Counter()
    for day, event in _recent(events, 90):
        if day < today:
            by_day[day] += max(0, int(event.get("total") or 0))
    values = [by_day[start + timedelta(days=i)] for i in range(89)]
    if len([value for value in values if value > 0]) < 21:
        return {"status": "insufficient history", "forecast": None}
    scale = max(1.0, max(values[:-7]))
    samples = [(_features(values, i, scale), math.log1p(values[i]) / math.log1p(scale)) for i in range(7, len(values))]
    train, holdout = samples[:-7], samples[-7:]
    weights = _fit_neural(train)
    neural_error = sum(abs(math.expm1(max(0.0, _predict(weights, x)) * math.log1p(scale)) - values[len(values) - 7 + i])
                       for i, (x, _) in enumerate(holdout)) / 7
    baseline_error = sum(abs(values[len(values) - 7 + i] - values[len(values) - 14 + i]) for i in range(7)) / 7
    if not math.isfinite(neural_error) or neural_error >= baseline_error or baseline_error == 0:
        return {"status": "validation below baseline", "forecast": None}
    all_scale = max(1.0, max(values))
    all_samples = [(_features(values, i, all_scale), math.log1p(values[i]) / math.log1p(all_scale)) for i in range(7, len(values))]
    weights = _fit_neural(all_samples)
    estimate = math.expm1(max(0.0, _predict(weights, _features(values + [0], len(values), all_scale))) * math.log1p(all_scale))
    if not math.isfinite(estimate):
        return {"status": "invalid estimate", "forecast": None}
    return {"status": "validated advisory estimate", "forecast": round(max(0, estimate)),
            "holdout_mae": round(neural_error), "baseline_mae": round(baseline_error),
            "target_day": today.isoformat(), "method": "one-hidden-layer neural regressor on recorded daily tokens"}
