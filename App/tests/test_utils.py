import unittest

from App.utils.profile_images import DEFAULT_PROFILE_IMAGE_URL, resolve_profile_image


class ProfileImageUtilsTests(unittest.TestCase):
    def test_resolve_profile_image_returns_fallback_when_missing(self):
        self.assertEqual(resolve_profile_image(None), DEFAULT_PROFILE_IMAGE_URL)
        self.assertEqual(resolve_profile_image({}), DEFAULT_PROFILE_IMAGE_URL)

    def test_resolve_profile_image_prefers_remote_url(self):
        url = "https://example.com/photo.jpg"
        profile_data = {"profile_picture_url": url}
        self.assertEqual(resolve_profile_image(profile_data), url)

    def test_resolve_profile_image_ignores_non_http_values(self):
        profile_data = {"image_filename": "uploads/profile_images/test.png"}
        self.assertEqual(resolve_profile_image(profile_data), DEFAULT_PROFILE_IMAGE_URL)
