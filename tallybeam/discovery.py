"""Bounded, read-only discovery of locally installed models and Obsidian vaults."""
from __future__ import annotations

import json
import os
import urllib.request
from itertools import islice
from pathlib import Path

MAX_MODELS = 500


def _children(path):
    try:
        return list(islice(path.iterdir(), MAX_MODELS))
    except OSError:
        return []


def _modified(path):
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


def _json_from_loopback(url):
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url, timeout=0.35) as response:
            if response.status != 200 or int(response.headers.get("Content-Length", "0")) > 2_000_000:
                return None
            return json.loads(response.read(2_000_001))
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _add(models, seen, source, name, evidence, state="installed"):
    name = str(name or "").strip()
    key = (source, name.casefold())
    if not name or len(name) > 180 or key in seen or len(models) >= MAX_MODELS:
        return
    seen.add(key)
    models.append({"provider": source, "model": name, "state": state, "evidence": evidence})


def discover_models(home=None, environ=None, loopback=None):
    """Find actual local model manifests; never crawl drives or infer usage."""
    home = Path(home) if home is not None else Path.home()
    env = os.environ if environ is None else environ
    query = _json_from_loopback if loopback is None else loopback
    models, seen = [], set()

    ollama = query("http://127.0.0.1:11434/api/tags")
    if isinstance(ollama, dict):
        for row in ollama.get("models", [])[:MAX_MODELS]:
            if isinstance(row, dict):
                _add(models, seen, "Ollama", row.get("name") or row.get("model"), "Ollama local API")
    ollama_root = Path(env.get("OLLAMA_MODELS") or home / ".ollama" / "models")
    manifests = ollama_root / "manifests"
    if manifests.is_dir():
        for registry in _children(manifests):
            if not registry.is_dir():
                continue
            for namespace in _children(registry):
                if not namespace.is_dir():
                    continue
                for model_dir in _children(namespace):
                    if not model_dir.is_dir():
                        continue
                    for tag in _children(model_dir):
                        if tag.is_file():
                            prefix = "" if namespace.name == "library" else namespace.name + "/"
                            _add(models, seen, "Ollama", f"{prefix}{model_dir.name}:{tag.name}", "Ollama manifest")
                        if len(models) >= MAX_MODELS:
                            break

    studio = query("http://127.0.0.1:1234/api/v0/models")
    if isinstance(studio, dict):
        for row in studio.get("data", [])[:MAX_MODELS]:
            if isinstance(row, dict):
                _add(models, seen, "LM Studio", row.get("id"), "LM Studio local API", row.get("state") or "installed")
    studio_root = home / ".lmstudio" / "models"
    if studio_root.is_dir():
        for publisher in _children(studio_root):
            if not publisher.is_dir():
                continue
            for repository in _children(publisher):
                if not repository.is_dir():
                    continue
                for item in _children(repository):
                    if item.is_file() and item.suffix.lower() in (".gguf", ".safetensors"):
                        _add(models, seen, "LM Studio", f"{publisher.name}/{repository.name}/{item.stem}", "LM Studio model folder")
                    if len(models) >= MAX_MODELS:
                        break

    hf_root = Path(env.get("HF_HUB_CACHE") or (Path(env["HF_HOME"]) / "hub" if env.get("HF_HOME") else home / ".cache" / "huggingface" / "hub"))
    if hf_root.is_dir():
        for item in _children(hf_root):
            if item.is_dir() and item.name.startswith("models--") and (item / "snapshots").is_dir():
                if _children(item / "snapshots"):
                    _add(models, seen, "Hugging Face", item.name.removeprefix("models--").replace("--", "/"), "Hugging Face cache")
            if len(models) >= MAX_MODELS:
                break

    return sorted(models, key=lambda row: (row["provider"], row["model"].casefold()))


def discover_obsidian_vaults(home=None, environ=None):
    """Read the vault registry only; note contents are neither indexed nor token evidence."""
    home = Path(home) if home is not None else Path.home()
    env = os.environ if environ is None else environ
    config = Path(env.get("APPDATA") or home / ".config") / "obsidian" / "obsidian.json"
    try:
        registered = json.loads(config.read_text(encoding="utf-8")).get("vaults", {})
    except (OSError, ValueError, AttributeError):
        return []
    result = []
    for row in list(registered.values())[:100]:
        if not isinstance(row, dict) or not row.get("path"):
            continue
        path = Path(row["path"])
        if path.is_dir() and (path / ".obsidian").is_dir():
            result.append({"name": path.name, "path": str(path), "status": "Vault detected; no token counters"})
    return result


def link_vaults_to_agent_sessions(vaults, roots=None):
    """Match recorded working directories, without reading vault notes or changing usage."""
    if not vaults:
        return vaults
    from .collector import source_roots

    roots = roots or {"Claude Code": source_roots("claude"), "Codex CLI": source_roots("codex")}
    linked = {vault["path"]: set() for vault in vaults}
    for agent, folders in roots.items():
        for folder in folders:
            if not Path(folder).is_dir():
                continue
            files = sorted(islice(Path(folder).rglob("*.jsonl"), 500), key=_modified, reverse=True)[:60]
            for path in files:
                try:
                    with path.open("r", encoding="utf-8", errors="replace") as stream:
                        for line in islice(stream, 12):
                            row = json.loads(line)
                            if not isinstance(row, dict):
                                continue
                            payload = row.get("payload")
                            cwd = row.get("cwd") or (payload.get("cwd") if isinstance(payload, dict) else None)
                            if not isinstance(cwd, str) or not Path(cwd).is_absolute():
                                continue
                            working = Path(cwd).resolve(strict=False)
                            for vault_path in linked:
                                vault_root = Path(vault_path).resolve(strict=False)
                                if working == vault_root or vault_root in working.parents:
                                    linked[vault_path].add(agent)
                            if all(linked.values()):
                                break
                except (OSError, ValueError, TypeError):
                    continue
    for vault in vaults:
        vault["agents"] = sorted(linked[vault["path"]])
        vault["status"] = ("Agent session observed in vault" if vault["agents"] else
                           "Vault detected; no link in recent sampled sessions")
    return vaults
