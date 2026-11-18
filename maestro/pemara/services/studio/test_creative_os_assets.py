import tempfile
import unittest
from pathlib import Path
from creative_os.store import Store
from creative_os.assets import Assets
from creative_os.ir import CreativeError


class AssetTests(unittest.TestCase):
    def test_scoping_change_and_escape(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/"film").mkdir(); (root/"film"/"frame.png").write_bytes(b"a")
            a=Assets(Store(root/"db.sqlite"), root)
            record=a.register("film","frame.png","first_frame")
            self.assertEqual(a.resolve(record["id"],"film")[0].read_bytes(),b"a")
            with self.assertRaises(CreativeError): a.resolve(record["id"],"other")
            with self.assertRaises(CreativeError): a.register("film","../db.sqlite","first_frame")
            (root/"film"/"frame.png").write_bytes(b"b")
            with self.assertRaisesRegex(CreativeError,"mudou"): a.resolve(record["id"],"film")
