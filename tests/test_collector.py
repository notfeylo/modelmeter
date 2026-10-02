import json
import tempfile
import unittest
from pathlib import Path

from tallybeam.collector import FileCache, scan_claude, scan_codex, scan_gemini, source_roots


class CollectorTests(unittest.TestCase):
    def test_claude_streaming_revisions_count_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = []
            for output in (2, 5):
                rows.append({"type": "assistant", "timestamp": "2026-10-01T12:00:00Z", "sessionId": "session",
                             "message": {"id": "same-message", "model": "claude-test", "usage": {
                                 "input_tokens": 10, "output_tokens": output,
                                 "cache_read_input_tokens": 4, "cache_creation_input_tokens": 1}}})
            (root / "a.jsonl").write_text("\n".join(map(json.dumps, rows)), encoding="utf-8")
            events = scan_claude(root)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["total"], 20)

    def test_codex_cumulative_usage_becomes_deltas(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = []
            for inp, cached, out in ((100, 20, 10), (150, 40, 20)):
                rows.append({"timestamp": "2026-10-01T12:00:00Z", "type": "event_msg", "payload": {
                    "type": "token_count", "info": {"total_token_usage": {
                        "input_tokens": inp, "cached_input_tokens": cached, "output_tokens": out}}}})
            (root / "b.jsonl").write_text("\n".join(map(json.dumps, rows)), encoding="utf-8")
            events, _ = scan_codex(root)
            self.assertEqual([e["total"] for e in events], [110, 60])
            self.assertEqual(events[1]["input"], 30)
            self.assertEqual(events[1]["cache_read"], 20)

    def test_gemini_total_includes_thought_tokens(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = {"sessionId": "gemini-test", "messages": [{"type": "gemini", "timestamp": "2026-10-01T12:00:00Z",
                     "model": "gemini-test", "tokens": {"input": 100, "output": 10, "cached": 20, "thoughts": 5, "total": 115}}]}
            (root / "session-test.json").write_text(json.dumps(data), encoding="utf-8")
            event = scan_gemini(root)[0]
            self.assertEqual(event["total"], 115)
            self.assertEqual(event["cache_read"], 20)

    def test_cached_source_updates_when_file_changes_and_deduplicates_copies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "session.jsonl"
            row = {"type": "assistant", "timestamp": "2026-10-01T12:00:00Z", "sessionId": "s",
                   "message": {"id": "one", "model": "m", "content": "private prompt text", "usage": {"input_tokens": 1}}}
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            cache_path = root / "cache" / "events.sqlite3"
            cache = FileCache(cache_path)
            self.assertEqual(scan_claude(root, cache)[0]["total"], 1)
            cache.close()
            self.assertNotIn(b"private prompt text", cache_path.read_bytes())
            (root / "copy.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
            row["message"]["id"] = "two"
            with path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row) + "\n")
            cache = FileCache(cache_path)
            self.assertEqual(len(scan_claude(root, cache)), 2)
            cache.close()

    def test_codex_home_override_is_checked(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict("os.environ", {"CODEX_HOME": directory}):
                self.assertIn(Path(directory) / "sessions", source_roots("codex"))
                self.assertIn(Path(directory) / "archived_sessions", source_roots("codex"))

    def test_opencode_extra_path_remains_with_override(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            primary = root / "primary.db"
            alternate = root / "alternate.db"
            with patch.dict("os.environ", {"OPENCODE_DB_PATH": str(primary)}):
                self.assertEqual(source_roots("opencode", [alternate]), [primary, alternate])


if __name__ == "__main__":
    unittest.main()
