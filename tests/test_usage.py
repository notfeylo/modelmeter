import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tallybeam.collector import scan_opencode
from tallybeam.usage import usage_payload, cache_miss_sessions, cache_miss_detail


class UsageTests(unittest.TestCase):
    def test_opencode_v1_usage(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "opencode.db"
            db = sqlite3.connect(path)
            db.execute("CREATE TABLE message (id TEXT, session_id TEXT, time_created INTEGER, data TEXT)")
            now = int(datetime.now(timezone.utc).timestamp() * 1000)
            data = {"role": "assistant", "modelID": "model-v1", "providerID": "provider-v1",
                    "time": {"created": now}, "tokens": {"input": 10, "output": 5, "cache": {"read": 2}}}
            db.execute("INSERT INTO message VALUES (?,?,?,?)", ("m1", "s1", now, json.dumps(data)))
            db.commit()
            db.close()
            rows = scan_opencode(Path(directory))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["total"], 17)
            self.assertEqual(rows[0]["provider"], "provider-v1")

    def test_opencode_v2_usage_without_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "opencode.db"
            db = sqlite3.connect(path)
            db.execute("CREATE TABLE session_message (id TEXT, session_id TEXT, type TEXT, time_created INTEGER, data TEXT)")
            now = int(datetime.now(timezone.utc).timestamp() * 1000)
            for i, (read, inp) in enumerate(((50, 100), (125, 20))):
                data = {"model": {"id": "model-a", "providerID": "provider-a"},
                        "time": {"created": now + i * 1000},
                        "tokens": {"input": inp, "output": 10, "reasoning": 5, "cache": {"read": read, "write": 0}},
                        "content": [{"type": "text", "text": "secret prompt content"}]}
                db.execute("INSERT INTO session_message VALUES (?,?,?,?,?)", (f"m{i}", "session-one", "assistant", now + i * 1000, json.dumps(data)))
            db.commit()
            db.close()
            events = scan_opencode(Path(directory))
            self.assertEqual(len(events), 2)
            self.assertNotIn("content", events[0])
            self.assertEqual(events[0]["reasoning"], 5)
            dashboard = usage_payload(events, "7")
            self.assertEqual(dashboard["summary"]["total"], 325)
            self.assertEqual(dashboard["summary"]["cache_expected"], 165)
            self.assertEqual(dashboard["summary"]["cache_miss"], 40)
            self.assertEqual(len(dashboard["days"]), 7)
            sessions = cache_miss_sessions(events, "7")
            detail = cache_miss_detail(events, sessions["sessions"][0]["sessionId"])
            self.assertEqual(detail["messages"][1]["miss"], 40)
            self.assertNotIn("content", json.dumps(detail))

    def test_empty_range_keeps_zero_days(self):
        event = {"provider": "Claude", "model": "old", "session": "s", "timestamp":
                 (datetime.now(timezone.utc) - timedelta(days=100)).isoformat(),
                 "input": 1, "output": 2, "cache_read": 0, "cache_write": 0, "total": 3}
        result = usage_payload([event], "7")
        self.assertEqual(result["summary"]["total"], 0)
        self.assertEqual(len(result["days"]), 7)


if __name__ == "__main__":
    unittest.main()
