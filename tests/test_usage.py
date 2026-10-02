import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tallybeam.collector import scan_opencode
from tallybeam.usage import usage_payload, cache_miss_sessions, cache_miss_detail


class UsageTests(unittest.TestCase):
    def test_opencode_mixed_schema_compaction_and_child_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "opencode-local.db"
            db = sqlite3.connect(path)
            db.execute("CREATE TABLE message (id TEXT, session_id TEXT, time_created INTEGER, data TEXT)")
            db.execute("CREATE TABLE session (id TEXT, title TEXT, directory TEXT, parent_id TEXT)")
            db.execute("CREATE TABLE session_v2 (id TEXT, title TEXT, directory TEXT, parent_id TEXT)")
            db.execute("CREATE TABLE session_message (id TEXT, session_id TEXT, type TEXT, time_created INTEGER, data TEXT)")
            db.execute("INSERT INTO session VALUES ('old', 'Old', '/work', NULL)")
            db.execute("INSERT INTO session_v2 VALUES ('new', 'secret prompt text', '/work', NULL)")
            db.execute("INSERT INTO session_v2 VALUES ('child', 'Child', '/work', 'new')")
            now = int(datetime.now(timezone.utc).timestamp() * 1000) - 10000
            db.execute("INSERT INTO message VALUES (?,?,?,?)", ("residue", "old", now, json.dumps({"role": "assistant", "tokens": {"input": 999}})))
            def assistant(created, completed):
                return json.dumps({"time": {"created": created, "completed": completed},
                                   "model": {"id": "m", "providerID": "p"},
                                   "tokens": {"input": 10, "output": 5, "cache": {"read": 5}}})
            rows = [("a", "new", "assistant", now, assistant(now, now + 1000)),
                    ("compact", "new", "compaction", now + 1500, json.dumps({"status": "completed"})),
                    ("b", "new", "assistant", now + 2000, assistant(now + 2000, now + 3000)),
                    ("c", "child", "assistant", now + 4000, assistant(now + 4000, now + 5000))]
            db.executemany("INSERT INTO session_message VALUES (?,?,?,?,?)", rows)
            db.commit()
            db.close()
            events = scan_opencode(Path(directory))
            self.assertEqual(len(events), 3)
            self.assertNotIn("title", events[0])
            self.assertNotIn("secret prompt text", json.dumps(cache_miss_sessions(events, "7")))
            self.assertTrue(events[1]["compaction_before"])
            self.assertEqual(events[0]["runtime"], 1000)
            self.assertNotIn("runtime", events[2])
            self.assertEqual(usage_payload(events, "7")["summary"]["cache_expected"], 0)

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
            self.assertEqual(len(dashboard["days"]), 168)
            self.assertEqual(len(dashboard["heatmap"]["data"]), 84)
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
        self.assertEqual(len(result["days"]), 168)

    def test_model_filter_recalculates_every_total(self):
        now = datetime.now(timezone.utc).isoformat()
        rows = [dict(provider="Claude", model=model, session=model, source="Claude Code", timestamp=now,
                     input=amount, output=1, cache_read=0, cache_write=0, total=amount + 1)
                for model, amount in (("sonnet", 10), ("opus", 20))]
        result = usage_payload(rows, "7", "sonnet")
        self.assertEqual(result["summary"]["total"], 11)
        self.assertEqual(sum(day["total"] for day in result["days"]), 11)
        self.assertEqual(result["models"][0]["name"], "sonnet")
        self.assertEqual(len(result["models"]), 1)
        self.assertEqual(result["meta"]["availableModels"], ["opus", "sonnet"])

    def test_runtime_merge_and_compaction_pairing(self):
        now = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        def row(offset, model, read, compacted=False):
            return {"provider": "OpenCode", "model": model, "session": "s", "source": "OpenCode",
                    "timestamp": (now + timedelta(minutes=offset)).isoformat(), "input": 10, "output": 5,
                    "cache_read": read, "cache_write": 0, "total": 15 + read,
                    "compaction_before": compacted}
        first = row(0, "a", 5)
        second = row(1, "a", 5, True)
        third = row(2, "a", 4)
        first.update(runtime=2000, runtime_start=1000, runtime_end=3000)
        second.update(runtime=2000, runtime_start=2000, runtime_end=4000)
        dashboard = usage_payload([first, second, third], "7")
        self.assertEqual(dashboard["summary"]["runtime"], 4000)
        self.assertEqual(dashboard["summary"]["runtime_dedup"], 3000)
        self.assertEqual(dashboard["summary"]["cache_expected"], 20)
        self.assertEqual(dashboard["summary"]["cache_miss"], 16)
        changed = row(1, "b", 1)
        unpaired = row(2, "a", 0)
        self.assertEqual(usage_payload([first, changed, unpaired], "7")["summary"]["cache_expected"], 0)


if __name__ == "__main__":
    unittest.main()
