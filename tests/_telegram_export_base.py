"""Shared helpers for telegram_export unit tests."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("API_ID", "123456")
os.environ.setdefault("API_HASH", "testhash")
os.environ.setdefault("PHONE", "+10000000000")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import telegram_export  # noqa: E402
from message_processing import author as author_module  # noqa: E402
from message_processing import message_transform  # noqa: E402


class TelegramExportUnitTestCase(unittest.TestCase):
    """Provides temp downloads dir and common patches for telegram_export tests."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)

        downloads_patcher = mock.patch.object(telegram_export, "DOWNLOADS_DIR", self.temp_dir)
        downloads_patcher.start()
        self.addCleanup(downloads_patcher.stop)

        transform_downloads = mock.patch.object(message_transform, "DOWNLOADS_DIR", self.temp_dir)
        transform_downloads.start()
        self.addCleanup(transform_downloads.stop)

        self.process_author_patcher = mock.patch.object(
            author_module,
            "process_author",
            return_value={
                "author_name": "Bob",
                "author_avatar": None,
                "author_link": None,
                "repost_author_name": None,
                "repost_author_avatar": None,
                "repost_author_link": None,
            },
        )
        self.mock_process_author = self.process_author_patcher.start()
        self.addCleanup(self.process_author_patcher.stop)

        self.process_poll_patcher = mock.patch.object(
            message_transform,
            "process_poll",
            return_value="",
        )
        self.mock_process_poll = self.process_poll_patcher.start()
        self.addCleanup(self.process_poll_patcher.stop)

        self.parse_entities_patcher = mock.patch.object(
            message_transform,
            "parse_entities_to_html",
            side_effect=lambda text, entities: text,
        )
        self.mock_parse_entities = self.parse_entities_patcher.start()
        self.addCleanup(self.parse_entities_patcher.stop)

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


__all__ = ["telegram_export", "TelegramExportUnitTestCase"]