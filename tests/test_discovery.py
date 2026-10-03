import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from tallybeam.discovery import _json_from_loopback, discover_models, discover_obsidian_vaults, link_vaults_to_agent_sessions


class DiscoveryTests(unittest.TestCase):
    def test_known_model_stores_only_and_no_usage_inferred(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            tag = home / ".ollama" / "models" / "manifests" / "registry.ollama.ai" / "library" / "qwen2.5" / "7b"
            tag.parent.mkdir(parents=True)
            tag.write_text("{}", encoding="utf-8")
            snapshot = home / ".cache" / "huggingface" / "hub" / "models--org--small" / "snapshots" / "abc"
            snapshot.mkdir(parents=True)
            (home / "unrelated.gguf").write_text("model", encoding="utf-8")
            models = discover_models(home, {}, loopback=lambda _url: None)
            self.assertEqual([(m["provider"], m["model"]) for m in models],
                             [("Hugging Face", "org/small"), ("Ollama", "qwen2.5:7b")])
            self.assertTrue(all("tokens" not in row for row in models))

    def test_loopback_model_list_deduplicates_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            query = lambda url: ({"models": [{"name": "llama3:latest"}]} if "11434" in url else
                                 {"data": [{"id": "qwen-small", "state": "loaded"}]})
            models = discover_models(home, {}, loopback=query)
            self.assertEqual({(m["provider"], m["model"]) for m in models},
                             {("Ollama", "llama3:latest"), ("LM Studio", "qwen-small")})

    def test_obsidian_registry_does_not_read_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            appdata = home / "AppData"
            config = appdata / "obsidian" / "obsidian.json"
            config.parent.mkdir(parents=True)
            vault = home / "brain"
            (vault / ".obsidian").mkdir(parents=True)
            (vault / "private.md").write_text("private text", encoding="utf-8")
            config.write_text(json.dumps({"vaults": {"one": {"path": str(vault)}}}), encoding="utf-8")
            result = discover_obsidian_vaults(home, {"APPDATA": str(appdata)})
            self.assertEqual(result[0]["name"], "brain")
            self.assertNotIn("private text", str(result))

    def test_vault_link_requires_recorded_agent_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault = root / "vault"
            vault.mkdir()
            logs = root / "logs"
            logs.mkdir()
            (logs / "session.jsonl").write_text(json.dumps({"cwd": str(vault / "project"), "type": "session_meta"}) + "\n", encoding="utf-8")
            result = link_vaults_to_agent_sessions([{"path": str(vault), "name": "vault"}], {"Claude Code": [logs]})
            self.assertEqual(result[0]["agents"], ["Claude Code"])

    def test_model_discovery_does_not_follow_loopback_redirects(self):
        reached = []

        class Target(BaseHTTPRequestHandler):
            def do_GET(self):
                reached.append(True)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"models": []}')

            def log_message(self, *_args):
                pass

        target = HTTPServer(("127.0.0.1", 0), Target)

        class Redirect(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{target.server_port}/")
                self.end_headers()

            def log_message(self, *_args):
                pass

        redirect = HTTPServer(("127.0.0.1", 0), Redirect)
        threads = [threading.Thread(target=server.serve_forever, daemon=True) for server in (target, redirect)]
        for thread in threads:
            thread.start()
        try:
            self.assertIsNone(_json_from_loopback(f"http://127.0.0.1:{redirect.server_port}/"))
            self.assertEqual(reached, [])
        finally:
            for server in (redirect, target):
                server.shutdown()
                server.server_close()
            for thread in threads:
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
