"""Real codec round-trip checks, without a camera. Requires opencv-python."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np
from mirror_capture import RawFrameWriter


@unittest.skipUnless(importlib.util.find_spec('cv2'), 'OpenCV is required for real AVI checks')
class VideoTests(unittest.TestCase):
    def test_two_videos_are_synchronized_and_preserve_raw_frames(self):
        import cv2
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / '영상_세션'
            folder.mkdir()
            writer = RawFrameWriter(folder / 'raw_frames', record_videos=True)
            original = np.full((48, 64, 3), (40, 60, 80), dtype=np.uint8)
            overlay = original.copy()
            overlay[8:32, 8:32] = (0, 255, 0)
            for i, t in enumerate([100., 100+1/30, 100+.1, 100+.2]):
                writer.submit(dict(frame_id=i+1, capture_monotonic_s=t),
                              dict(color_bgr=original.copy(), overlay_bgr=overlay.copy(),
                                   depth_native_z16=np.full((24, 32), 600, dtype=np.uint16)))
            summary = writer.close()
            self.assertTrue(summary['complete'], summary)
            self.assertTrue(summary['videos']['verified'])
            self.assertEqual(summary['written_frames'], 4)
            self.assertEqual(summary['videos']['frames'], 7)
            self.assertAlmostEqual(summary['videos']['duration_s'], 7/30)
            with (folder/'raw_frames/frames.csv').open(encoding='utf-8-sig', newline='') as fp:
                rows = list(csv.DictReader(fp))
            self.assertEqual([int(row['video_frame_index']) for row in rows], [0, 1, 3, 6])
            for name in ('original', 'mediapipe'):
                capture = cv2.VideoCapture(str(folder / f'{name}.avi'))
                try:
                    self.assertEqual(int(capture.get(cv2.CAP_PROP_FRAME_COUNT)), 7)
                    self.assertAlmostEqual(capture.get(cv2.CAP_PROP_FPS), 30)
                    for _ in range(7):
                        ok, frame = capture.read()
                        self.assertTrue(ok)
                        self.assertEqual(frame.shape, original.shape)
                        patch = frame[12:28, 12:28].mean(axis=(0, 1))
                        if name == 'mediapipe':
                            self.assertGreater(patch[1], 200)
                        else:
                            self.assertLess(patch[1], 100)
                finally:
                    capture.release()
            with np.load(folder/'raw_frames/frame_00000001.npz', allow_pickle=False) as frame:
                np.testing.assert_array_equal(frame['color_bgr'], original)
                self.assertNotIn('overlay_bgr', frame.files)
            self.assertFalse(list(folder.glob('*.partial.avi')))

    def test_resolution_change_is_reported_as_partial_recording(self):
        with tempfile.TemporaryDirectory() as temp:
            writer = RawFrameWriter(Path(temp)/'raw', record_videos=True)
            for i, shape in enumerate([(48, 64, 3), (50, 64, 3)]):
                image = np.zeros(shape, dtype=np.uint8)
                writer.submit(dict(frame_id=i+1, capture_monotonic_s=10.+i),
                              dict(color_bgr=image, overlay_bgr=image.copy()))
            summary = writer.close()
            self.assertFalse(summary['complete'])
            self.assertIn('해상도', summary['error'])


if __name__ == '__main__':
    unittest.main()
