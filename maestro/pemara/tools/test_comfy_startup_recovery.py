import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import comfy_lifecycle as lifecycle


class StartupRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name)
        (self.state / 'starting.json').write_text(json.dumps({'pid': 42, 'created': 1000}))
        self.proc = Mock(pid=42)
        self.proc.create_time.return_value = 1000
        self.proc.children.return_value = []
        self.addCleanup(patch.stopall)
        patch.object(lifecycle, 'STATE', self.state).start()
        patch.object(lifecycle, 'exact_process', return_value=self.proc).start()
        patch.object(lifecycle.time, 'time', return_value=2000).start()
        self.listener = patch.object(lifecycle, 'listener', return_value=None).start()
        self.register = patch.object(lifecycle, 'register').start()
        patch.object(lifecycle.psutil, 'wait_procs', return_value=([self.proc], [])).start()

    def test_aged_owned_startup_can_be_recovered(self):
        result = lifecycle.stop_failed_start(42)
        self.assertTrue(result['recovered_failed_startup'])
        self.proc.kill.assert_called_once()
        self.assertFalse((self.state / 'starting.json').exists())
        self.assertTrue(Path(result['evidence']).exists())

    def test_recent_startup_is_preserved(self):
        with patch.object(lifecycle.time, 'time', return_value=1100):
            with self.assertRaises(RuntimeError):
                lifecycle.stop_failed_start(42)
        self.proc.kill.assert_not_called()

    def test_pid_reuse_is_preserved(self):
        self.proc.create_time.return_value = 1001
        with self.assertRaises(RuntimeError):
            lifecycle.stop_failed_start(42)
        self.proc.kill.assert_not_called()

    def test_previously_live_runtime_is_preserved(self):
        (self.state / 'runtime.json').write_text(json.dumps({'pid': 42, 'created': 1000}))
        with self.assertRaises(RuntimeError):
            lifecycle.stop_failed_start(42)
        self.proc.kill.assert_not_called()

    def test_listener_race_is_preserved(self):
        self.listener.return_value = 42
        with self.assertRaises(RuntimeError):
            lifecycle.stop_failed_start(42)
        self.proc.kill.assert_not_called()


if __name__ == '__main__':
    unittest.main()
