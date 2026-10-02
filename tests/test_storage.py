import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from tallybeam import app


class StorageTests(unittest.TestCase):
    def test_only_absolute_non_root_extra_paths_are_loaded(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = app.configured_paths({"paths": {"codex": [directory, ".", str(Path(directory).anchor), 3]}})
            self.assertEqual(paths["codex"], [directory])

    def test_imported_usage_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(app, "DATA", root), patch.object(app, "DB", root / "usage.sqlite3"):
                with closing(app.database()) as db:
                    db.execute("INSERT INTO imported VALUES (?,?,?,?,?,?,?,?,?)", (
                        "request-1", "Grok", "grok-test", "2026-10-01T12:00:00+00:00", "session-1", 100, 25, 10, 0))
                    db.commit()
                events = app.imported()
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0]["provider"], "Grok")
                self.assertEqual(events[0]["total"], 135)


if __name__ == "__main__":
    unittest.main()
