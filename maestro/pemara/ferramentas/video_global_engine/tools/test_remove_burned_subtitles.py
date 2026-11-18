import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

import remove_burned_subtitles as cleanup


class SubtitleCleanupTests(unittest.TestCase):
    def test_temporal_mask_keeps_persistent_text_and_rejects_moving_white_object(self):
        with tempfile.TemporaryDirectory() as temp_name:
            video = Path(temp_name) / "synthetic.avi"
            writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 12, (160, 90))
            self.assertTrue(writer.isOpened())
            for index in range(12):
                frame = np.full((90, 160, 3), (80, 110, 140), dtype=np.uint8)
                if 2 <= index <= 10:
                    cv2.putText(frame, "TEST", (45, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.rectangle(frame, (index * 8, 58), (index * 8 + 8, 66), (255, 255, 255), -1)
                writer.write(frame)
            writer.release()
            core, expanded, details = cleanup.temporal_subtitle_mask(
                video,
                band_top=50,
                band_bottom=85,
                left=0,
                right=160,
                occupancy=0.5,
                min_luma=185,
                max_saturation=80,
                dilate=5,
            )
            self.assertGreater(details["core_pixels"], 50)
            self.assertGreater(np.count_nonzero(expanded[60:82, 35:115]), 50)
            self.assertEqual(np.count_nonzero(core[55:68, 0:30]), 0)

    def test_frame_detection_requires_overlap_with_temporal_core(self):
        core = np.zeros((40, 80), dtype=np.uint8)
        core[25:30, 20:60] = 255
        with_text = np.zeros((40, 80, 3), dtype=np.uint8)
        with_text[25:30, 20:60] = 255
        without_text = np.zeros_like(with_text)
        self.assertTrue(cleanup.frame_has_subtitle(with_text, core, min_luma=188, max_saturation=72))
        self.assertFalse(cleanup.frame_has_subtitle(without_text, core, min_luma=188, max_saturation=72))

    def test_temporal_flow_removes_static_text_from_moving_scene(self):
        clean_frames = []
        contaminated = []
        text_mask = np.zeros((90, 160), dtype=np.uint8)
        cv2.putText(text_mask, "TEST", (45, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 255, 2)
        text_mask = cv2.dilate(text_mask, np.ones((5, 5), np.uint8), iterations=1)
        flags = []
        for index in range(12):
            x = np.arange(160, dtype=np.uint8)[None, :]
            frame = np.empty((90, 160, 3), dtype=np.uint8)
            frame[:, :, 0] = 50 + (x // 5)
            frame[:, :, 1] = 90 + (x // 8)
            frame[:, :, 2] = 120 + (x // 10)
            cv2.rectangle(frame, (15 + index * 5, 54), (40 + index * 5, 82), (40, 170, 210), -1)
            clean_frames.append(frame.copy())
            present = 2 <= index <= 9
            flags.append(present)
            if present:
                cv2.putText(frame, "TEST", (45, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            contaminated.append(frame)

        cleaned = cleanup.temporal_flow_clean_frames(
            contaminated,
            flags,
            text_mask,
            radius=3.0,
            flow_scale=0.5,
        )
        affected = text_mask > 0
        before_error = np.mean(
            [np.abs(contaminated[i][affected].astype(float) - clean_frames[i][affected]).mean() for i in range(2, 10)]
        )
        after_error = np.mean(
            [np.abs(cleaned[i][affected].astype(float) - clean_frames[i][affected]).mean() for i in range(2, 10)]
        )
        self.assertLess(after_error, before_error * 0.55)


if __name__ == "__main__":
    unittest.main()
