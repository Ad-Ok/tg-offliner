from __future__ import annotations

import os
from contextlib import ExitStack
from types import SimpleNamespace
from unittest import mock

from tests._telegram_export_base import TelegramExportUnitTestCase, telegram_export


class ProcessMessageTests(TelegramExportUnitTestCase):
    def test_process_message_basic_text(self):
        folder_name = "test_channel"
        mock_client = mock.Mock()

        self.mock_process_author.return_value = ("Alice", "avatars/alice.jpg", "https://t.me/alice")
        post = self._build_basic_post()
        result = telegram_export.process_message_for_api(post, "channel123", mock_client, folder_name=folder_name)

        self.assertIsNotNone(result)
        self.assertEqual(result["message"], "Hello")
        self.assertEqual(result["author_name"], "Alice")
        self.assertIsNone(result["media_url"])
        self.assertTrue(os.path.isdir(os.path.join(self.temp_dir, folder_name)))

    def test_process_message_photo_creates_thumbnail(self):
        folder_name = "test_channel"

        class FakePhoto:
            """Marker class to mimic MessageMediaPhoto."""

        post = self._build_basic_post(id=456, media=FakePhoto())
        mock_client = mock.Mock()

        def fake_download(media, file):
            with open(f"{file}.jpg", "wb") as handle:
                handle.write(b"fake")
            return f"{file}.jpg"

        mock_client.download_media.side_effect = fake_download

        with mock.patch.object(telegram_export, "MessageMediaPhoto", FakePhoto):
            result = telegram_export.process_message_for_api(post, "channel123", mock_client, folder_name=folder_name)

        self.assertIsNotNone(result)
        self.assertIsNotNone(result["media_url"])
        self.assertIsNotNone(result["thumb_url"])
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, result["thumb_url"])))

    def test_process_message_web_page(self):
        post = self._build_basic_post(
            media=SimpleNamespace(webpage=SimpleNamespace(url="https://example.com"))
        )
        mock_client = mock.Mock()

        with mock.patch.object(telegram_export, "MessageMediaWebPage", SimpleNamespace):
            result = telegram_export.process_message_for_api(post, "channel123", mock_client)

        self.assertEqual(result["media_url"], "https://example.com")
        self.assertIsNone(result["thumb_url"])

    def test_process_message_sticker_adds_emoji(self):
        class FakeStickerAttr:
            def __init__(self, alt):
                self.alt = alt

        sticker_attr = FakeStickerAttr("🔥")

        class FakeDocument:
            def __init__(self):
                self.mime_type = "application/x-tgsticker"
                self.attributes = [sticker_attr]

        class FakeMediaDocument:
            def __init__(self):
                self.document = FakeDocument()

        media = FakeMediaDocument()
        mock_client = mock.Mock()
        post = self._build_basic_post(message="Text", media=media)

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(telegram_export, "MessageMediaDocument", FakeMediaDocument))
            stack.enter_context(mock.patch.object(telegram_export, "Document", FakeDocument))
            stack.enter_context(mock.patch.object(telegram_export, "DocumentAttributeSticker", FakeStickerAttr))
            stack.enter_context(mock.patch.object(telegram_export, "MessageMediaPhoto", SimpleNamespace))
            result = telegram_export.process_message_for_api(post, "channel123", mock_client)

        self.assertEqual(result["message"], "Text 🔥")
        self.assertIsNone(result["media_url"])

    def test_process_message_system_action(self):
        class MessageActionChatEditTitle:
            def __init__(self, title):
                self.title = title

        post = self._build_basic_post(action=MessageActionChatEditTitle("New Title"), message="")
        mock_client = mock.Mock()

        result = telegram_export.process_message_for_api(post, "channel123", mock_client)

        self.assertEqual(result["message"], "✏️ Название изменено на: New Title")

    def test_process_message_reactions(self):
        reaction = SimpleNamespace(reaction="👍", count=5)
        post = self._build_basic_post(reactions=SimpleNamespace(results=[reaction]))
        mock_client = mock.Mock()

        result = telegram_export.process_message_for_api(post, "channel123", mock_client)

        self.assertEqual(result["reactions"]["total_count"], 5)
        self.assertEqual(result["reactions"]["recent_reactions"], [{"reaction": "👍", "count": 5}])