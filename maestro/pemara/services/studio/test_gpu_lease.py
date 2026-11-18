import tempfile
import unittest
from pathlib import Path

from gpu_lease import GpuLeaseBusy, GpuLeaseRegistry


class GpuLeaseRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.registry = GpuLeaseRegistry(Path(self.temp.name) / "gpu_lease.json")

    def tearDown(self):
        self.temp.cleanup()

    def test_active_owner_blocks_another_job_without_terminating_it(self):
        first = self.registry.acquire(
            owner="studio",
            operation="video_take",
            job_id="job-1",
            project_id="project-a",
            take_id="01",
        )
        self.assertEqual(first["jobId"], "job-1")

        with self.assertRaises(GpuLeaseBusy) as blocked:
            self.registry.acquire(
                owner="studio",
                operation="video_sound",
                job_id="job-2",
                project_id="project-a",
                take_id="02",
            )
        self.assertEqual(blocked.exception.current["jobId"], "job-1")
        self.assertFalse(self.registry.release("job-2"))
        self.assertTrue(self.registry.status()["active"])

        self.assertTrue(self.registry.release("job-1"))
        self.assertFalse(self.registry.status()["active"])

    def test_same_job_can_heartbeat_and_reacquire_idempotently(self):
        self.registry.acquire(
            owner="studio",
            operation="video_take",
            job_id="job-1",
        )
        heartbeat = self.registry.heartbeat("job-1")
        again = self.registry.acquire(
            owner="studio",
            operation="video_take",
            job_id="job-1",
        )
        self.assertEqual(heartbeat["acquiredAt"], again["acquiredAt"])
        self.assertEqual(again["pid"], heartbeat["pid"])


if __name__ == "__main__":
    unittest.main()
