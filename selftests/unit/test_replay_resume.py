"""Unit tests for variant-aware replay resume.

Covers:
  - TestSuite._runnable_name()
  - Replay._load_completed_test_names()
  - The filtering integration (runnable_name vs completed set)
"""
import json
import os
import tempfile
import unittest


class FakeRunnable:
    """Minimal stand-in for avocado.core.nrunner.runnable.Runnable."""

    def __init__(self, identifier, variant=None):
        self.identifier = identifier
        self.variant = variant


class TestRunnableName(unittest.TestCase):
    """Tests for TestSuite._runnable_name()."""

    def setUp(self):
        from avocado.core.suite import TestSuite
        self.fn = TestSuite._runnable_name

    def test_no_variant(self):
        r = FakeRunnable("examples/tests/passtest.py:PassTest.test", variant=None)
        self.assertEqual(
            self.fn(r),
            "examples/tests/passtest.py:PassTest.test",
        )

    def test_with_variant_id(self):
        r = FakeRunnable(
            "examples/tests/passtest.py:PassTest.test",
            variant={"variant_id": "fast-abc1", "variant": [], "paths": ["/"]},
        )
        self.assertEqual(
            self.fn(r),
            "examples/tests/passtest.py:PassTest.test;fast-abc1",
        )

    def test_variant_id_none(self):
        """variant dict present but variant_id is None → no suffix."""
        r = FakeRunnable(
            "examples/tests/passtest.py:PassTest.test",
            variant={"variant_id": None, "variant": [], "paths": ["/"]},
        )
        self.assertEqual(
            self.fn(r),
            "examples/tests/passtest.py:PassTest.test",
        )


class TestLoadCompletedTestNames(unittest.TestCase):
    """Tests for Replay._load_completed_test_names()."""

    def setUp(self):
        from avocado.plugins.replay import Replay
        self.load = Replay._load_completed_test_names

    def test_pass_and_skip_collected(self):
        with tempfile.TemporaryDirectory() as d:
            data = {
                "tests": [
                    {"name": "mytest.py:T.test;v1", "status": "PASS"},
                    {"name": "mytest.py:T.test;v2", "status": "FAIL"},
                    {"name": "mytest.py:T.test;v3", "status": "SKIP"},
                    {"name": "mytest.py:T.test;v4", "status": "ERROR"},
                ]
            }
            with open(os.path.join(d, "results.json"), "w", encoding="utf-8") as f:
                json.dump(data, f)
            completed = self.load(d)
        self.assertEqual(
            completed,
            {"mytest.py:T.test;v1", "mytest.py:T.test;v3"},
        )

    def test_missing_results_json(self):
        """Missing results.json returns empty set without raising."""
        self.assertEqual(self.load("/nonexistent/path/xyz"), set())

    def test_empty_tests_list(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "results.json"), "w", encoding="utf-8") as f:
                json.dump({"tests": []}, f)
            self.assertEqual(self.load(d), set())

    def test_corrupt_json_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "results.json"), "w", encoding="utf-8") as f:
                f.write("not valid json {{")
            self.assertEqual(self.load(d), set())


class TestResumeFiltering(unittest.TestCase):
    """Integration: _runnable_name matches what _load_completed_test_names returns."""

    def test_filters_out_completed_variants_only(self):
        from avocado.core.suite import TestSuite

        completed = {"mytest.py:T.test;v1", "mytest.py:T.test;v3"}
        runnables = [
            FakeRunnable("mytest.py:T.test", {"variant_id": "v1", "variant": [], "paths": ["/"]}),
            FakeRunnable("mytest.py:T.test", {"variant_id": "v2", "variant": [], "paths": ["/"]}),
            FakeRunnable("mytest.py:T.test", {"variant_id": "v3", "variant": [], "paths": ["/"]}),
            FakeRunnable("mytest.py:T.test", {"variant_id": "v4", "variant": [], "paths": ["/"]}),
        ]
        remaining = [r for r in runnables if TestSuite._runnable_name(r) not in completed]
        self.assertEqual(len(remaining), 2)
        self.assertEqual(TestSuite._runnable_name(remaining[0]), "mytest.py:T.test;v2")
        self.assertEqual(TestSuite._runnable_name(remaining[1]), "mytest.py:T.test;v4")

    def test_no_completed_keeps_all(self):
        from avocado.core.suite import TestSuite

        runnables = [
            FakeRunnable("mytest.py:T.test", {"variant_id": "v1", "variant": [], "paths": ["/"]}),
            FakeRunnable("mytest.py:T.test", {"variant_id": "v2", "variant": [], "paths": ["/"]}),
        ]
        # empty completed set → nothing filtered
        remaining = [r for r in runnables if TestSuite._runnable_name(r) not in set()]
        self.assertEqual(len(remaining), 2)


if __name__ == "__main__":
    unittest.main()
