import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from creative_os.ir import CreativeError
from creative_os.store import Store


class StoreTests(unittest.TestCase):
    def test_revision_and_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            s = Store(Path(d) / "state.sqlite")
            first = s.put("shots", {"prompt": "one"}, entity_id="SH1")
            s.put("shots", {"prompt": "two"}, entity_id="SH1", expected=first["revision"], create=False)
            with self.assertRaises(CreativeError):
                s.put("shots", {"prompt": "stale"}, entity_id="SH1", expected=1, create=False)
            self.assertEqual(s.get("shots", "SH1")["prompt"], "two")
            self.assertEqual(len(s.history("shots", "SH1")), 2)

    def test_concurrent_create_has_one_winner(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "state.sqlite"
            def create(_):
                try: Store(path).put("jobs", {}, entity_id="same"); return True
                except CreativeError: return False
            with ThreadPoolExecutor(max_workers=4) as pool:
                self.assertEqual(sum(pool.map(create, range(8))), 1)
