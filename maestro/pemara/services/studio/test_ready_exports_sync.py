import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import video_projects
from ready_exports_sync import PENDING_NAME, ReadyExportsSync


class ReadyExportsSyncTests(unittest.TestCase):
    def test_review_persists_without_waiting_for_slow_export_and_next_review_wins(self):
        entered, release, second = threading.Event(), threading.Event(), threading.Event()
        snapshots = []

        def slow_export(project, *, queue_path):
            snapshots.append(json.loads(queue_path.read_text())['takes'][0]['maestro_status'])
            if len(snapshots) == 1:
                entered.set()
                release.wait(3)
            else:
                second.set()

        worker = ReadyExportsSync(slow_export)
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                video_projects.create_project(root, name='Review Speed')
                project = root / 'review_speed'
                queue_path = project / 'take_queue.json'
                queue = json.loads(queue_path.read_text())
                preview = project / 'takes' / 'test.mp4'
                preview.write_bytes(b'original-preserved')
                queue['takes'] = [{'id': '01', 'maestro_status': 'READY', 'video': {'output_preview': str(preview)}}]
                queue_path.write_text(json.dumps(queue))
                with mock.patch.object(video_projects, 'request_ready_exports_sync', worker.request):
                    first = video_projects.patch_take(root, 'review_speed', '01', {'status': 'APPROVED'}, defer_exports=True)
                    self.assertEqual(first['status'], 'APPROVED')
                    self.assertTrue(entered.wait(2))
                    self.assertTrue((project / PENDING_NAME).exists())
                    start = time.monotonic()
                    latest = video_projects.patch_take(root, 'review_speed', '01', {
                        'status': 'REJECTED', 'directorRequest': {'category': 'OTHER', 'reason': 'Fix motion'},
                    }, defer_exports=True)
                    self.assertLess(time.monotonic() - start, 1)
                    self.assertEqual(latest['status'], 'REJECTED')
                    self.assertEqual(json.loads(queue_path.read_text())['takes'][0]['maestro_status'], 'REJECTED')
                    self.assertEqual(preview.read_bytes(), b'original-preserved')
                    release.set()
                    self.assertTrue(second.wait(2))
                    worker.close()
                    self.assertEqual(snapshots, ['APPROVED', 'REJECTED'])
                    self.assertFalse((project / PENDING_NAME).exists())
        finally:
            release.set()
            worker.close()

    def test_failed_export_remains_durable_and_resumes_after_restart(self):
        failed = threading.Event()

        def fail(*args, **kwargs):
            failed.set()
            raise OSError('disk temporarily unavailable')

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / 'project'
            project.mkdir()
            queue = project / 'take_queue.json'
            queue.write_text('{}')
            first = ReadyExportsSync(fail)
            with self.assertLogs(level='ERROR'):
                first.request(project, queue_path=queue)
                self.assertTrue(failed.wait(2))
                first.close()
            self.assertTrue((project / PENDING_NAME).exists())
            recovered = threading.Event()
            second = ReadyExportsSync(lambda *args, **kwargs: recovered.set())
            try:
                second.resume(root)
                self.assertTrue(recovered.wait(2))
                second.close()
                self.assertFalse((project / PENDING_NAME).exists())
            finally:
                second.close()

    def test_rejects_queue_outside_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            worker = ReadyExportsSync()
            with self.assertRaises(ValueError):
                worker.request(root / 'project', queue_path=root / 'other.json')


if __name__ == '__main__':
    unittest.main()
