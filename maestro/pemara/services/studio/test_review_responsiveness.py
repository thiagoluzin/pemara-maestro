import asyncio
import threading
import unittest
from unittest import mock

import main


class ReviewResponsivenessTests(unittest.IsolatedAsyncioTestCase):
    async def test_slow_reviews_and_preparation_do_not_block_another_decision(self):
        cases = [
            ('video_take_anchor_review', '_review_anchor_candidate', {'decision': 'APPROVED'}),
            ('video_take_audio_candidate_review', '_review_take_audio_candidate', {'decision': 'APPROVED'}),
            ('video_take_job_start', '_start_video_take_job', {}),
            ('video_take_upscale_start', '_start_take_upscale_job', {}),
            ('video_anchor_executor_start', '_start_video_anchor_executor', {'takeIds': ['01']}),
        ]
        for route, operation, payload in cases:
            with self.subTest(route=route):
                entered, release = threading.Event(), threading.Event()

                def slow(*args, **kwargs):
                    entered.set()
                    release.wait(2)
                    return {'ok': True}

                with mock.patch.object(main, '_is_internal_request', return_value=True), \
                     mock.patch.object(main, '_video_projects_json_body', new=mock.AsyncMock(return_value=payload)), \
                     mock.patch.object(main, operation, side_effect=slow), \
                     mock.patch.object(main, '_patch_video_take', return_value={'status': 'APPROVED'}) as patch_take:
                    args = (object(), 'project') if route == 'video_anchor_executor_start' else (object(), 'project', '01')
                    task = asyncio.create_task(getattr(main, route)(*args))
                    try:
                        for _ in range(100):
                            if entered.is_set():
                                break
                            await asyncio.sleep(.01)
                        self.assertTrue(entered.is_set())
                        self.assertFalse(task.done(), 'Slow operation blocked the event loop')
                        # Body is independently parsed for the quick review.
                        main._video_projects_json_body.return_value = {'status': 'APPROVED'}
                        result = await asyncio.wait_for(main.video_take_patch(object(), 'other', '02'), .5)
                        self.assertEqual(result['status'], 'APPROVED')
                        self.assertTrue(patch_take.call_args.kwargs['defer_exports'])
                    finally:
                        release.set()
                        await task


if __name__ == '__main__':
    unittest.main()
