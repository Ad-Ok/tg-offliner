import os
import shutil
import sys
import tempfile
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest import mock

# Ensure required environment variables exist before importing project modules
os.environ.setdefault("API_ID", "123456")
os.environ.setdefault("API_HASH", "testhash")
os.environ.setdefault("PHONE", "+10000000000")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import telegram_export


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