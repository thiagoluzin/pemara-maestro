import unittest
from unittest import mock

import hyperframes_runtime as runtime


class HyperFramesRuntimeTest(unittest.TestCase):
    def test_status_exposes_local_only_and_authenticated_rules(self) -> None:
        with mock.patch.object(runtime, "preview_online", return_value=True):
            data = runtime.status()
        self.assertTrue(data["online"])
        self.assertEqual(data["bind"], "127.0.0.1")
        self.assertEqual(data["port"], 8032)
        self.assertTrue(data["rules"]["autoStartWithMaestro"])
        self.assertTrue(data["rules"]["authenticatedGateway"])
        self.assertFalse(data["rules"]["browserGpu"])

    def test_ensure_preview_does_not_duplicate_online_server(self) -> None:
        with (
            mock.patch.object(runtime, "preview_online", return_value=True),
            mock.patch.object(runtime.subprocess, "run") as run,
        ):
            data = runtime.ensure_preview()
        self.assertTrue(data["online"])
        run.assert_not_called()

    def test_queued_render_is_not_started_twice(self) -> None:
        queued = {"id": "existing", "status": "queued", "progress": 0}
        with (
            mock.patch.object(runtime, "_load_job", return_value=queued),
            mock.patch.object(runtime.threading, "Thread") as thread,
        ):
            result = runtime.start_render()
        self.assertEqual(result, queued)
        thread.assert_not_called()


if __name__ == "__main__":
    unittest.main()
