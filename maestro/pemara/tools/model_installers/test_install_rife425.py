import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import install_rife425 as installer


class RestoreTests(unittest.TestCase):
    def test_corrupt_archive_never_creates_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / 'bad.zip'
            with zipfile.ZipFile(archive, 'w') as package:
                package.writestr('flownet.pkl', b'wrong-model')
                package.writestr('../../outside.py', b'unsafe')
            with self.assertRaises(ValueError):
                installer.install(archive, root / 'target')
            self.assertFalse((root / 'target').exists())
            self.assertFalse((root / 'outside.py').exists())

    def test_verified_weight_is_idempotent_and_existing_other_model_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            weight = b'fixture-weight'
            archive = root / 'model.zip'
            with zipfile.ZipFile(archive, 'w') as package:
                package.writestr('rife425/flownet.pkl', weight)
                package.writestr('../../outside.py', b'not-extracted')
            with patch.object(installer, 'MODEL_SHA256', hashlib.sha256(weight).hexdigest()), patch.object(installer, 'MODEL_BYTES', len(weight)):
                target = root / 'target'
                self.assertEqual(installer.install(archive, target)['status'], 'PASS')
                installed = target / 'third_party/Practical-RIFE/train_log/flownet.pkl'
                timestamp = installed.stat().st_mtime_ns
                installer.install(archive, target)
                self.assertEqual(timestamp, installed.stat().st_mtime_ns)
                self.assertFalse((root / 'outside.py').exists())
                installed.write_bytes(b'other-existing-model')
                with self.assertRaises(ValueError):
                    installer.install(archive, target)
                self.assertEqual(installed.read_bytes(), b'other-existing-model')

    def test_duplicate_weight_names_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / 'duplicate.zip'
            with zipfile.ZipFile(archive, 'w') as package:
                package.writestr('a/flownet.pkl', b'one')
                package.writestr('b/flownet.pkl', b'two')
            with self.assertRaises(ValueError):
                installer.install(archive, root / 'target')
            self.assertFalse((root / 'target').exists())


if __name__ == '__main__':
    unittest.main()
