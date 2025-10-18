from __future__ import annotations

from contextlib import ExitStack
from types import SimpleNamespace
from unittest import mock

from tests._telegram_export_base import TelegramExportUnitTestCase, telegram_export


class ImportChannelDirectTests(TelegramExportUnitTestCase):
    def test_import_channel_direct_success(self):
        mock_client = mock.Mock()
        entity = SimpleNamespace(username="llamatest", id=42, count=2)
        posts = [
            SimpleNamespace(id=1, action=None, fwd_from=None, poll=None),
            SimpleNamespace(id=2, action=None, fwd_from=None, poll=None),
        ]

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(telegram_export, "connect_to_telegram", return_value=mock_client))
            stack.enter_context(mock.patch("utils.entity_validation.get_entity_by_username_or_id", return_value=(entity, None)))
            stack.enter_context(mock.patch("utils.entity_validation.validate_entity_for_download", return_value={"valid": True, "error": None}))
            stack.enter_context(mock.patch.object(telegram_export, "clear_downloads"))
            stack.enter_context(mock.patch.object(telegram_export, "get_channel_info", return_value={"discussion_group_id": 777}))
            stack.enter_context(mock.patch.object(telegram_export, "process_message_for_api", side_effect=[{"telegram_id": 1}, {"telegram_id": 2}]))
            stack.enter_context(mock.patch.object(telegram_export, "import_discussion_comments", return_value=1))
            stack.enter_context(mock.patch.object(telegram_export, "should_stop_import", return_value=False))
            stack.enter_context(mock.patch.object(telegram_export, "update_import_progress"))
            stack.enter_context(mock.patch.object(telegram_export, "generate_gallery_layouts_for_channel"))
            stack.enter_context(mock.patch("telegram_export.requests.post", return_value=SimpleNamespace(status_code=200)))
            stack.enter_context(mock.patch("telegram_export.time.sleep"))

            mock_client.iter_messages.return_value = posts

            result = telegram_export.import_channel_direct("llamatest", channel_id="test-channel")

        self.assertTrue(result["success"])
        self.assertEqual(result["processed"], 2)
        self.assertEqual(result["comments"], 2)

    def test_import_channel_direct_stops_on_request(self):
        mock_client = mock.Mock()
        entity = SimpleNamespace(username="llamatest", id=42, count=1)
        posts = [SimpleNamespace(id=1, action=None, fwd_from=None, poll=None)]

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(telegram_export, "connect_to_telegram", return_value=mock_client))
            stack.enter_context(mock.patch("utils.entity_validation.get_entity_by_username_or_id", return_value=(entity, None)))
            stack.enter_context(mock.patch("utils.entity_validation.validate_entity_for_download", return_value={"valid": True, "error": None}))
            stack.enter_context(mock.patch.object(telegram_export, "clear_downloads"))
            stack.enter_context(mock.patch.object(telegram_export, "get_channel_info", return_value={"discussion_group_id": None}))
            stack.enter_context(mock.patch.object(telegram_export, "should_stop_import", return_value=True))
            stack.enter_context(mock.patch.object(telegram_export, "generate_gallery_layouts_for_channel"))
            stack.enter_context(mock.patch("telegram_export.requests.post", return_value=SimpleNamespace(status_code=200)))
            stack.enter_context(mock.patch("telegram_export.time.sleep"))
            update_mock = stack.enter_context(mock.patch.object(telegram_export, "update_import_progress"))

            mock_client.iter_messages.return_value = posts

            result = telegram_export.import_channel_direct("llamatest", channel_id="stop-test")

        self.assertTrue(result["success"])
        self.assertTrue(result["stopped"])
        self.assertEqual(result["processed"], 0)
        update_mock.assert_not_called()

    def test_import_channel_direct_validation_failure(self):
        mock_client = mock.Mock()
        entity = SimpleNamespace(username="llamatest", id=42)

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(telegram_export, "connect_to_telegram", return_value=mock_client))
            stack.enter_context(mock.patch("utils.entity_validation.get_entity_by_username_or_id", return_value=(entity, None)))
            stack.enter_context(mock.patch("utils.entity_validation.validate_entity_for_download", return_value={"valid": False, "error": "Not allowed"}))

            result = telegram_export.import_channel_direct("llamatest")

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Not allowed")

    def test_import_channel_direct_entity_not_found(self):
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(telegram_export, "connect_to_telegram", return_value=mock.Mock()))
            stack.enter_context(mock.patch("utils.entity_validation.get_entity_by_username_or_id", return_value=(None, "Not found")))

            result = telegram_export.import_channel_direct("missing")

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Not found")