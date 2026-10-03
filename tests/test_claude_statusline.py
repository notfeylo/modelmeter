import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tallybeam.claude_statusline import capture, read_snapshot


class ClaudeStatuslineTests(unittest.TestCase):
    def test_capture_saves_only_reported_limit_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "limits.json"
            reset = int((datetime.now(timezone.utc) + timedelta(hours=2)).timestamp())
            payload = {"model": {"id": "claude-test"}, "transcript_path": "private/path",
                       "rate_limits": {"five_hour": {"used_percentage": 27.5, "resets_at": reset}}}
            self.assertTrue(capture(payload, path))
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["windows"]["five_hour"]["used_percent"], 27.5)
            self.assertNotIn("private/path", path.read_text(encoding="utf-8"))
            self.assertEqual(read_snapshot(path)["model"], "claude-test")

    def test_missing_or_expired_limit_does_not_overwrite_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "limits.json"
            self.assertFalse(capture({"rate_limits": {}}, path))
            self.assertFalse(path.exists())
            self.assertFalse(capture({"rate_limits": {"five_hour": {"used_percentage": 4, "resets_at": 1}}}, path))


if __name__ == "__main__":
    unittest.main()
