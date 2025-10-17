import os
import shutil
import sys
import tempfile
import unittest
from contextlib import ExitStack
from datetime import datetime
from types import SimpleNamespace
from unittest import mock

# Ensure required environment variables exist before importing project modules
os.environ.setdefault("API_ID", "123456")
os.environ.setdefault("API_HASH", "testhash")
os.environ.setdefault("PHONE", "+10000000000")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import telegram_export


class TelegramExportTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)

        patcher = mock.patch.object(telegram_export, "DOWNLOADS_DIR", self.temp_dir)
        self.addCleanup(patcher.stop)
        patcher.start()

    def _build_basic_post(self, **overrides):
        base = {
            "id": 123,
            "message": "Hello",
            "media": None,
            "poll": None,
            "sender": SimpleNamespace(),
            "peer_id": None,
            "from_id": None,
            "fwd_from": None,
            "reactions": None,
            "entities": [],
            "grouped_id": None,
            "reply_to": None,
            "action": None,
            "date": datetime(2024, 1, 1),
        }
        base.update(overrides)
        return SimpleNamespace(**base)

    def test_process_message_basic_text(self):
        folder_name = "test_channel"
        mock_client = mock.Mock()

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(telegram_export, "process_author", return_value=("Alice", "avatars/alice.jpg", "https://t.me/alice")))
            stack.enter_context(mock.patch.object(telegram_export, "process_poll", return_value=""))
            stack.enter_context(mock.patch.object(telegram_export, "parse_entities_to_html", side_effect=lambda text, entities: text))
            post = self._build_basic_post()
            result = telegram_export.process_message_for_api(post, "channel123", mock_client, folder_name=folder_name)

        self.assertIsNotNone(result)
        self.assertEqual(result["message"], "Hello")
        self.assertEqual(result["author_name"], "Alice")
        self.assertEqual(result["media_url"], None)
        self.assertTrue(os.path.isdir(os.path.join(self.temp_dir, folder_name)))

    def test_process_message_photo_creates_thumbnail(self):
        folder_name = "test_channel"

        class FakePhoto:  # noqa: D401 - simple test double
            """Marker class to mimic MessageMediaPhoto."""

        post = self._build_basic_post(
            id=456,
            media=FakePhoto(),
        )

        mock_client = mock.Mock()

        def fake_download(media, file):
            with open(f"{file}.jpg", "wb") as handle:
                handle.write(b"fake")
            return f"{file}.jpg"

        mock_client.download_media.side_effect = fake_download

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(telegram_export, "MessageMediaPhoto", FakePhoto))
            stack.enter_context(mock.patch.object(telegram_export, "process_author", return_value=("Bob", None, None)))
            stack.enter_context(mock.patch.object(telegram_export, "process_poll", return_value=""))
            stack.enter_context(mock.patch.object(telegram_export, "parse_entities_to_html", side_effect=lambda text, entities: text))
            result = telegram_export.process_message_for_api(post, "channel123", mock_client, folder_name=folder_name)

        self.assertIsNotNone(result)
        self.assertIsNotNone(result["media_url"])
        self.assertIsNotNone(result["thumb_url"])

        thumb_full_path = os.path.join(self.temp_dir, result["thumb_url"])
        self.assertTrue(os.path.exists(thumb_full_path))

    def test_should_stop_import_true(self):
        with mock.patch("telegram_export.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"status": "stopped"}
            self.assertTrue(telegram_export.should_stop_import("channel123"))

    def test_update_import_progress_post_called(self):
        with mock.patch("telegram_export.requests.post") as mock_post:
            telegram_export.update_import_progress("channel123", 10, 5, total_posts=100)
            mock_post.assert_called_once()

    def test_clear_downloads_removes_existing_folder(self):
        channel_folder = os.path.join(self.temp_dir, "existing")
        os.makedirs(channel_folder, exist_ok=True)
        with open(os.path.join(channel_folder, "file.txt"), "w", encoding="utf-8") as handle:
            handle.write("data")

        telegram_export.clear_downloads("existing")

        self.assertTrue(os.path.isdir(channel_folder))
        self.assertEqual(os.listdir(channel_folder), [])

    def test_get_channel_folder_numeric_id(self):
        channel_folder = telegram_export.get_channel_folder("12345")
        self.assertTrue(channel_folder.endswith(os.path.join(self.temp_dir, "channel_12345")))
        self.assertTrue(os.path.isdir(os.path.join(channel_folder, "media")))


@unittest.skipUnless(os.getenv("RUN_TELEGRAM_INTEGRATION") == "1", "Set RUN_TELEGRAM_INTEGRATION=1 to run integration tests")
class TelegramExportIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)

        patcher = mock.patch.object(telegram_export, "DOWNLOADS_DIR", self.temp_dir)
        self.addCleanup(patcher.stop)
        patcher.start()

        # Avoid touching DB-dependent logic during integration run
        gallery_patcher = mock.patch.object(telegram_export, "generate_gallery_layouts_for_channel", return_value=None)
        self.addCleanup(gallery_patcher.stop)
        gallery_patcher.start()

    def test_import_llamatest_channel(self):
        posted_payloads = []

        class DummyResponse:
            def __init__(self, status_code=200, text="OK"):
                self.status_code = status_code
                self.text = text

            def json(self):
                return {"status": "running"}

        with ExitStack() as stack:
            stack.enter_context(mock.patch("telegram_export.requests.post", side_effect=lambda *args, **kwargs: (posted_payloads.append((args, kwargs)) or DummyResponse())))
            stack.enter_context(mock.patch("telegram_export.requests.get", return_value=DummyResponse()))

            export_settings = {
                "include_system_messages": True,
                "include_reposts": True,
                "include_polls": True,
                "include_discussion_comments": False,
                "message_limit": 5,
            }

            result = telegram_export.import_channel_direct("llamatest", channel_id="integration-test", export_settings=export_settings)

        self.assertTrue(result["success"], msg=f"Integration import failed: {result}")
        self.assertGreater(result["processed"], 0)
        self.assertTrue(any("/api/channels" in call[0][0] for call in posted_payloads))
        self.assertTrue(any("/api/posts" in call[0][0] for call in posted_payloads))

        channel_dir = os.path.join(self.temp_dir, "llamatest")
        self.assertTrue(os.path.isdir(channel_dir), msg="Expected downloads folder for llamatest")

if __name__ == "__main__":
    unittest.main()
