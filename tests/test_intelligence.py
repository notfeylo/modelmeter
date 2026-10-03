import unittest
from datetime import datetime, timedelta, timezone

from tallybeam.intelligence import grounded_answer, neural_usage_forecast, recorded_facts, retrieve_facts


class IntelligenceTests(unittest.TestCase):
    def test_retrieval_uses_recorded_counters_only(self):
        event = {"provider": "Codex", "source": "Codex CLI", "model": "gpt-test",
                 "timestamp": datetime.now(timezone.utc).isoformat(), "total": 17,
                 "content": "secret prompt text"}
        facts = recorded_facts([event])
        self.assertTrue(any("17" in fact["text"] for fact in facts))
        self.assertTrue(any("gpt-test" in fact["text"] for fact in retrieve_facts("gpt-test", facts)))
        self.assertNotIn("secret prompt text", str(facts))
        answer = grounded_answer("Which model?", facts)
        self.assertEqual(answer["method"], "recorded facts")
        self.assertTrue(answer["evidence"])

    def test_neural_estimate_suppressed_without_history(self):
        now = datetime.now(timezone.utc)
        events = [{"timestamp": (now - timedelta(days=day)).isoformat(), "total": 10} for day in range(5)]
        self.assertIsNone(neural_usage_forecast(events)["forecast"])

    def test_neural_forecast_is_advisory_or_withheld(self):
        today = datetime.now().astimezone().date()
        events = [{"timestamp": datetime.combine(today - timedelta(days=day), datetime.min.time(), timezone.utc).isoformat(),
                   "total": (day % 7 + 1) * 100} for day in range(1, 85)]
        result = neural_usage_forecast(events)
        if result["forecast"] is not None:
            self.assertGreaterEqual(result["forecast"], 0)
            self.assertLess(result["holdout_mae"], result["baseline_mae"])
        else:
            self.assertIn(result["status"], ("validation below baseline", "insufficient history"))


if __name__ == "__main__":
    unittest.main()
