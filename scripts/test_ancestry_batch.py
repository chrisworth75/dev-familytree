"""Unit tests for ancestry_batch.SessionStore and pure helpers.

Run with:
    cd ~/dev-familytree/scripts
    ../.venv/bin/python -m unittest test_ancestry_batch -v
"""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ancestry_batch import (
    SessionStore,
    SessionError,
    build_event,
    normalize_side,
)


class SessionStoreTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _new_store(self):
        return SessionStore.new(sessions_root=self.root)

    def test_new_session_creates_dir_and_checkpoint(self):
        store = self._new_store()
        self.assertTrue(store.session_dir.is_dir())
        self.assertTrue(store.checkpoint_path.is_file())
        self.assertEqual(store.status, "in_progress")
        self.assertEqual(store.last_page_completed, 0)
        self.assertIsNone(store.test_guid)
        self.assertEqual(store.event_count(), 0)
        self.assertRegex(store.session_id, r"^\d{4}-\d{2}-\d{2}-[0-9a-f]{6}$")

    def test_session_id_uses_supplied_clock(self):
        when = datetime(2026, 5, 15, 9, 30, 0, tzinfo=timezone.utc).astimezone()
        store = SessionStore.new(sessions_root=self.root, now=when)
        self.assertTrue(store.session_id.startswith("2026-05-15-"))

    def test_set_test_guid_persists(self):
        store = self._new_store()
        store.set_test_guid("E756DE6C-0C8D-443B-8793-ADDB6F35FD6A")
        reloaded = SessionStore.load(store.session_dir)
        self.assertEqual(reloaded.test_guid, "E756DE6C-0C8D-443B-8793-ADDB6F35FD6A")

    def test_append_event_writes_one_line_per_call_with_durable_flush(self):
        store = self._new_store()
        e1 = build_event({"guid": "AAA", "name": "Alice", "sharedCm": 100.0}, store.session_id)
        e2 = build_event({"guid": "BBB", "name": "Bob", "sharedCm": 50.0}, store.session_id)
        store.append_event(e1)
        # File visible and content readable BEFORE store.close() - durability check.
        self.assertEqual(store.event_count(), 1)
        store.append_event(e2)
        self.assertEqual(store.event_count(), 2)
        lines = store.events_path.read_text().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0])["match"]["ancestry_id"], "AAA")
        self.assertEqual(json.loads(lines[1])["match"]["ancestry_id"], "BBB")
        store.close()

    def test_complete_page_updates_state_atomically(self):
        store = self._new_store()
        store.complete_page(1, ["AAA", "BBB"])
        store.complete_page(2, ["CCC"])
        # No .tmp leftover.
        self.assertFalse((store.session_dir / "checkpoint.json.tmp").exists())
        reloaded = SessionStore.load(store.session_dir)
        self.assertEqual(reloaded.last_page_completed, 2)
        self.assertEqual(reloaded.state["seen_guids"], ["AAA", "BBB", "CCC"])
        self.assertTrue(reloaded.has_seen("BBB"))
        self.assertFalse(reloaded.has_seen("ZZZ"))

    def test_complete_page_is_idempotent_on_duplicate_guids(self):
        store = self._new_store()
        store.complete_page(1, ["AAA"])
        store.complete_page(2, ["AAA", "BBB"])  # AAA already seen
        self.assertEqual(store.state["seen_guids"], ["AAA", "BBB"])

    def test_mark_complete_and_abandoned(self):
        store = self._new_store()
        store.mark_complete()
        self.assertEqual(SessionStore.load(store.session_dir).status, "complete")

        other = self._new_store()
        other.mark_abandoned()
        self.assertEqual(SessionStore.load(other.session_dir).status, "abandoned")

    def test_load_missing_checkpoint_raises(self):
        empty_dir = self.root / "ghost"
        empty_dir.mkdir()
        with self.assertRaises(SessionError):
            SessionStore.load(empty_dir)

    def test_find_in_progress_returns_only_in_progress(self):
        a = self._new_store()
        b = self._new_store()
        c = self._new_store()
        b.mark_complete()
        c.mark_abandoned()
        results = SessionStore.find_in_progress(sessions_root=self.root)
        self.assertEqual(results, [a.session_dir])

    def test_find_in_progress_handles_missing_root(self):
        self.assertEqual(SessionStore.find_in_progress(sessions_root=self.root / "nope"), [])

    def test_record_failed_page_persists_and_is_idempotent(self):
        store = self._new_store()
        store.record_failed_page(42)
        store.record_failed_page(7)
        store.record_failed_page(42)  # duplicate - should be ignored
        reloaded = SessionStore.load(store.session_dir)
        self.assertEqual(reloaded.failed_pages, [42, 7])

    def test_resolve_failed_page_removes_and_merges_guids(self):
        store = self._new_store()
        store.record_failed_page(5)
        store.record_failed_page(8)
        store.resolve_failed_page(5, ["XXX", "YYY"])
        reloaded = SessionStore.load(store.session_dir)
        self.assertEqual(reloaded.failed_pages, [8])
        self.assertTrue(reloaded.has_seen("XXX"))
        self.assertTrue(reloaded.has_seen("YYY"))

    def test_resolve_failed_page_is_noop_for_unknown_page(self):
        store = self._new_store()
        store.resolve_failed_page(999, [])  # not in failed_pages - shouldn't raise
        self.assertEqual(store.failed_pages, [])

    def test_complete_or_keep_open_marks_complete_when_no_failures(self):
        store = self._new_store()
        result = store.complete_or_keep_open()
        self.assertTrue(result)
        self.assertEqual(SessionStore.load(store.session_dir).status, "complete")

    def test_complete_or_keep_open_leaves_open_when_failures_pending(self):
        store = self._new_store()
        store.record_failed_page(5)
        result = store.complete_or_keep_open()
        self.assertFalse(result)
        reloaded = SessionStore.load(store.session_dir)
        self.assertEqual(reloaded.status, "in_progress")
        self.assertEqual(reloaded.failed_pages, [5])

    def test_load_checkpoint_without_failed_pages_field(self):
        """Backwards-compat: older checkpoints have no failed_pages key."""
        store = self._new_store()
        # Simulate a legacy checkpoint without the new field.
        legacy = dict(store.state)
        legacy.pop("failed_pages")
        store.checkpoint_path.write_text(json.dumps(legacy))
        reloaded = SessionStore.load(store.session_dir)
        self.assertEqual(reloaded.failed_pages, [])
        # Should still be able to record one.
        reloaded.record_failed_page(1)
        self.assertEqual(reloaded.failed_pages, [1])

    def test_event_count_cached_across_append_and_load(self):
        store = self._new_store()
        self.assertEqual(store.event_count(), 0)
        for guid in ["AAA", "BBB", "CCC"]:
            store.append_event(build_event({"guid": guid, "name": guid}, store.session_id))
        self.assertEqual(store.event_count(), 3)
        store.close()

        reloaded = SessionStore.load(store.session_dir)
        self.assertEqual(reloaded.event_count(), 3)
        reloaded.append_event(build_event({"guid": "DDD", "name": "D"}, reloaded.session_id))
        self.assertEqual(reloaded.event_count(), 4)
        reloaded.close()

    def test_load_seeds_seen_guids_from_events_jsonl(self):
        """Mid-page crash recovery: events flushed to disk before complete_page
        runs must still be deduped on resume, even though they never made it
        into the checkpoint's seen_guids list."""
        store = self._new_store()
        for guid in ["AAA", "BBB", "CCC"]:
            store.append_event(build_event({"guid": guid, "name": guid}, store.session_id))
        # No complete_page() call — simulates the process dying mid-page.
        store.close()
        # Sanity: state on disk still has empty seen_guids.
        on_disk = json.loads(store.checkpoint_path.read_text())
        self.assertEqual(on_disk["seen_guids"], [])

        reloaded = SessionStore.load(store.session_dir)
        self.assertTrue(reloaded.has_seen("AAA"))
        self.assertTrue(reloaded.has_seen("BBB"))
        self.assertTrue(reloaded.has_seen("CCC"))
        self.assertFalse(reloaded.has_seen("ZZZ"))

        # Next complete_page should sync the recovered GUIDs into the on-disk list.
        reloaded.complete_page(1, [])
        re_re = SessionStore.load(store.session_dir)
        self.assertEqual(sorted(re_re.state["seen_guids"]), ["AAA", "BBB", "CCC"])

    def test_round_trip_full_state(self):
        """End-to-end: create -> append events -> complete pages -> reload."""
        store = self._new_store()
        store.set_test_guid("GUID-1")
        for i, guid in enumerate(["AAA", "BBB", "CCC"], start=1):
            event = build_event({"guid": guid, "name": f"M{i}", "sharedCm": 10.0 * i}, store.session_id)
            store.append_event(event)
        store.complete_page(1, ["AAA", "BBB", "CCC"])
        store.close()

        reloaded = SessionStore.load(store.session_dir)
        self.assertEqual(reloaded.session_id, store.session_id)
        self.assertEqual(reloaded.test_guid, "GUID-1")
        self.assertEqual(reloaded.last_page_completed, 1)
        self.assertEqual(reloaded.event_count(), 3)
        for guid in ("AAA", "BBB", "CCC"):
            self.assertTrue(reloaded.has_seen(guid))


class HelpersTest(unittest.TestCase):
    def test_normalize_side_known_values(self):
        self.assertEqual(normalize_side("Both sides"), "both")
        self.assertEqual(normalize_side("Paternal side"), "paternal")
        self.assertEqual(normalize_side("Maternal side"), "maternal")
        self.assertEqual(normalize_side("PATERNAL SIDE"), "paternal")
        self.assertEqual(normalize_side("Paternal side (warning)"), "paternal")

    def test_normalize_side_unknown_or_missing(self):
        self.assertEqual(normalize_side(None), "unknown")
        self.assertEqual(normalize_side(""), "unknown")
        self.assertEqual(normalize_side("Cousin"), "unknown")

    def test_build_event_schema_shape(self):
        raw = {
            "guid": "AAA",
            "name": "Alice",
            "sharedCm": 42.5,
            "relationship": "2nd cousin",
            "matchSide": "Paternal side",
            "hasTree": True,
            "treeSize": 1234,
            "linkedTreeId": "999",
            "hasCommonAncestor": True,
        }
        event = build_event(raw, "session-id-1")
        self.assertEqual(event["event_type"], "MatchObserved")
        self.assertEqual(event["schema_version"], 1)
        self.assertEqual(event["source"], "ancestry.co.uk")
        self.assertEqual(event["session_id"], "session-id-1")
        self.assertEqual(len(event["event_id"]), 36)  # uuid4 string form
        self.assertIn("T", event["discovered_at"])  # ISO8601
        self.assertEqual(
            event["match"],
            {
                "ancestry_id": "AAA",
                "name": "Alice",
                "shared_cm": 42.5,
                "predicted_relationship": "2nd cousin",
                "match_side": "paternal",
                "has_tree": True,
                "tree_size": 1234,
                "linked_tree_id": "999",
                "has_common_ancestor": True,
            },
        )

    def test_build_event_handles_missing_optional_fields(self):
        event = build_event({"guid": "BBB", "name": "Bob"}, "s1")
        self.assertEqual(event["match"]["ancestry_id"], "BBB")
        self.assertIsNone(event["match"]["shared_cm"])
        self.assertIsNone(event["match"]["predicted_relationship"])
        self.assertEqual(event["match"]["match_side"], "unknown")
        self.assertFalse(event["match"]["has_tree"])
        self.assertFalse(event["match"]["has_common_ancestor"])


if __name__ == "__main__":
    unittest.main()
