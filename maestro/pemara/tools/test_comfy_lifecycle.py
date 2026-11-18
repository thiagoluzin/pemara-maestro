import contextlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

import comfy_lifecycle as lifecycle
from comfy_cli import utils
from comfy_mcp import errors


class LifecycleTests(unittest.TestCase):
    def test_hidden_owner_delegates_to_fixed_broker_without_local_kill(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(lifecycle, 'STATE', Path(tmp)), \
                patch.object(lifecycle, 'listener', side_effect=lifecycle.psutil.AccessDenied()), \
                patch.object(lifecycle, 'delegated_stop', return_value={'stopped': True}) as broker, \
                patch.object(lifecycle, 'stop_exact') as local_stop:
            self.assertTrue(lifecycle.operate('stop')['stopped'])
            broker.assert_called_once(); local_stop.assert_not_called()

    def test_bound_only_socket_requires_recorded_runtime_identity(self):
        import json
        bound = Mock(status=lifecycle.psutil.CONN_NONE, pid=43,
                     laddr=Mock(ip='127.0.0.1', port=8188))
        parent = Mock(pid=42)
        parent.create_time.return_value = 123.0
        parent.children.return_value = [Mock(pid=43)]
        with tempfile.TemporaryDirectory() as tmp, patch.object(lifecycle, 'STATE', Path(tmp)), \
                patch.object(lifecycle.psutil, 'net_connections', return_value=[bound]), \
                patch.object(lifecycle.psutil, 'Process', return_value=parent), \
                patch.object(lifecycle, 'exact_process') as exact:
            with self.assertRaises(RuntimeError):
                lifecycle.listener()
            (Path(tmp) / 'starting.json').write_text(json.dumps({'pid': 42, 'created': 123.0}))
            self.assertEqual(lifecycle.listener(), 43)
            exact.assert_called_once_with(43)
            parent.create_time.return_value = 124.0
            with self.assertRaises(RuntimeError):
                lifecycle.listener()

    def test_listener_ignores_other_bound_interface(self):
        foreign = Mock(status=lifecycle.psutil.CONN_LISTEN, pid=4528,
                       laddr=Mock(ip='100.103.10.110', port=8188))
        local = Mock(status=lifecycle.psutil.CONN_LISTEN, pid=42,
                     laddr=Mock(ip='127.0.0.1', port=8188))
        with patch.object(lifecycle.psutil, 'net_connections', return_value=[foreign]):
            self.assertIsNone(lifecycle.listener())
        with patch.object(lifecycle.psutil, 'net_connections', return_value=[foreign, local]):
            self.assertEqual(lifecycle.listener(), 42)

    def test_listener_preserves_wildcard_conflicts(self):
        for address in ('0.0.0.0', '::', '::ffff:127.0.0.1'):
            bound = Mock(status=lifecycle.psutil.CONN_LISTEN, pid=42,
                         laddr=Mock(ip=address, port=8188))
            with self.subTest(address=address), patch.object(
                    lifecycle.psutil, 'net_connections', return_value=[bound]):
                self.assertEqual(lifecycle.listener(), 42)

    def test_busy_queue_refuses(self):
        for queue in ({'queue_running': [1], 'queue_pending': []},
                      {'queue_running': [], 'queue_pending': [1]}, {}):
            with self.subTest(queue=queue), patch.object(lifecycle, 'get_json', return_value=queue):
                with self.assertRaises(RuntimeError):
                    lifecycle.idle()

    def test_unknown_runtime_refuses(self):
        data = {'system': {'argv': ['C:/other/main.py'], 'comfyui_version': '0.34.2',
                           'pytorch_version': '2.14.0+cu130'}, 'devices': [{'type': 'cuda'}]}
        with self.assertRaises(RuntimeError):
            lifecycle.validate_stats(data)

    def test_automatic_start_obeys_hold_without_probe(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(lifecycle, 'STATE', Path(tmp)), \
                patch.object(lifecycle, 'listener') as probe:
            (Path(tmp) / 'maintenance.hold').touch()
            result = lifecycle.operate('start', automatic=True)
            self.assertTrue(result['maintenance'])
            probe.assert_not_called()

    def test_busy_stop_does_not_set_hold_or_kill(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(lifecycle, 'STATE', Path(tmp)), \
                patch.object(lifecycle, 'listener', return_value=1), \
                patch.object(lifecycle, 'get_json'), patch.object(lifecycle, 'validate_stats'), \
                patch.object(lifecycle, 'idle', side_effect=RuntimeError('busy')), \
                patch.object(lifecycle, 'stop_exact') as stop:
            with self.assertRaises(RuntimeError):
                lifecycle.operate('stop')
            stop.assert_not_called()
            self.assertFalse((Path(tmp) / 'maintenance.hold').exists())

    def test_same_runtime_start_does_not_spawn(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(lifecycle, 'STATE', Path(tmp)), \
                patch.object(lifecycle, 'FLAG', Path(tmp) / 'flag'), \
                patch.object(lifecycle, 'listener', return_value=42), \
                patch.object(lifecycle, 'get_json'), patch.object(lifecycle, 'validate_stats'), \
                patch.object(lifecycle, 'record', return_value={'pid': 42}), \
                patch.object(lifecycle.subprocess, 'Popen') as spawn:
            self.assertTrue(lifecycle.operate('start')['already_running'])
            spawn.assert_not_called()

    def test_global_lock_refuses_second_operation(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(lifecycle, 'STATE', Path(tmp)):
            with lifecycle.lock():
                with self.assertRaises(RuntimeError):
                    with lifecycle.lock():
                        self.fail('Second lock must not succeed')

    def test_leaf_process_is_killed_and_waited(self):
        proc = Mock()
        proc.children.return_value = []
        with patch.object(utils.psutil, 'Process', return_value=proc), \
                patch.object(utils.psutil, 'wait_procs', return_value=([proc], [])) as wait:
            self.assertTrue(utils.kill_all(42))
            proc.kill.assert_called_once()
            wait.assert_called_once_with([proc], timeout=10)

    def test_survivor_is_not_reported_stopped(self):
        proc = Mock()
        proc.children.return_value = []
        with patch.object(utils.psutil, 'Process', return_value=proc), \
                patch.object(utils.psutil, 'wait_procs', return_value=([], [proc])):
            self.assertFalse(utils.kill_all(42))

    def test_listener_loss_does_not_erase_living_process(self):
        with patch.object(lifecycle, 'listener', return_value=None), \
                patch.object(lifecycle, 'tracked_alive', return_value=42), \
                patch.object(lifecycle, 'register') as register:
            with self.assertRaises(RuntimeError):
                lifecycle.stop_exact()
            register.assert_not_called()

    def test_orphan_prevents_duplicate_start(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(lifecycle, 'STATE', Path(tmp)), \
                patch.object(lifecycle, 'FLAG', Path(tmp) / 'flag'), \
                patch.object(lifecycle, 'listener', return_value=None), \
                patch.object(lifecycle, 'tracked_alive', return_value=42), \
                patch.object(lifecycle.subprocess, 'Popen') as spawn:
            with self.assertRaises(RuntimeError):
                lifecycle.operate('start')
            spawn.assert_not_called()

    def test_error_alias_does_not_swallow_timeout_or_permission(self):
        for code, timed_out, expected in [('no_background_server', False, True),
                                          ('no_recorded_server', False, True),
                                          ('no_background_server', True, False),
                                          ('stop_failed', False, False)]:
            exc = Mock(code=code, timed_out=timed_out)
            with self.subTest(code=code, timed_out=timed_out):
                self.assertEqual(errors._is_no_recorded_server(exc), expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
