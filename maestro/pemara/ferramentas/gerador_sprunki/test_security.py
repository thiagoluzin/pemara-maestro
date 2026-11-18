import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import app as sprunki


def png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), (20, 40, 60)).save(buffer, format="PNG")
    return buffer.getvalue()


class SprunkiSecurityTest(unittest.TestCase):
    def setUp(self):
        sprunki.app.config.update(TESTING=True)
        self.client = sprunki.app.test_client()

    def test_upload_ignores_hostile_filename_and_validates_image(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            sprunki, "OUTPUT_DIR", Path(temp_dir)
        ):
            response = self.client.post(
                "/api/studio/upload",
                data={"file": (io.BytesIO(png_bytes()), "../../payload.svg")},
                content_type="multipart/form-data",
            )
            self.assertEqual(response.status_code, 200)
            output_name = Path(response.get_json()["url"]).name
            self.assertRegex(output_name, r"^upload_[0-9a-f]{32}\.png$")
            self.assertEqual([path.name for path in Path(temp_dir).iterdir()], [output_name])

            rejected = self.client.post(
                "/api/studio/upload",
                data={"file": (io.BytesIO(b"<script>alert(1)</script>"), "image.png")},
                content_type="multipart/form-data",
            )
            self.assertEqual(rejected.status_code, 400)

    def test_reference_image_rejects_unsupported_data_url_before_generation(self):
        response = self.client.post(
            "/api/generate_oc",
            json={"image_ref": "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4="},
        )
        self.assertEqual(response.status_code, 400)

    def test_unbounded_text_and_rating_paths_are_rejected(self):
        too_long = self.client.post(
            "/api/generate_oc",
            json={"extra_desc": "x" * 1001},
        )
        self.assertEqual(too_long.status_code, 400)

        traversal = self.client.post(
            "/api/save_rating",
            json={"name": "../ratings.json", "rating": 5},
        )
        self.assertEqual(traversal.status_code, 400)

    def test_security_headers_and_no_wildcard_cors(self):
        response = self.client.get(
            "/api/status/not-a-uuid",
            headers={"Origin": "https://evil.example"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["Cross-Origin-Resource-Policy"], "same-origin")
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

        bad_host = self.client.get(
            "/api/status/not-a-uuid",
            headers={"Host": "evil.example"},
        )
        self.assertEqual(bad_host.status_code, 421)


if __name__ == "__main__":
    unittest.main()
