import unittest
from io import BytesIO
from PIL import Image
from video_projects import _validate_anchor_png

class AnchorPixelRoundingTests(unittest.TestCase):
    def png(self,width,height):
        stream=BytesIO();Image.new('RGB',(width,height)).save(stream,format='PNG');return stream.getvalue()
    def test_original_imagegen_fractional_ratio_is_accepted(self):
        self.assertEqual(_validate_anchor_png(self.png(1672,941))['width'],1672)
        self.assertEqual(_validate_anchor_png(self.png(941,1672))['width'],941)
    def test_wrong_ratio_and_more_than_one_pixel_remain_rejected(self):
        for size in ((1536,1024),(1024,1024),(1672,943)):
            with self.subTest(size=size),self.assertRaisesRegex(ValueError,'proporcao'):
                _validate_anchor_png(self.png(*size))
