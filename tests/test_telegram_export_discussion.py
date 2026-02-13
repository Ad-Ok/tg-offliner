from __future__ import annotations

from contextlib import ExitStack
from types import SimpleNamespace
from unittest import mock

from tests._telegram_export_base import TelegramExportUnitTestCase, telegram_export


class DiscussionImportTests(TelegramExportUnitTestCase):
    def test_import_discussion_comments_success(self):
        client = mock.Mock()
        discussion_entity = SimpleNamespace(id=777)
        comment_message = SimpleNamespace(
            id=10,
            sender=SimpleNamespace(),
            media=None,
            poll=None,
            reactions=None,
            entities=[],
            grouped_id=None,
            reply_to=SimpleNamespace(reply_to_msg_id=50),
        )

        with ExitStack() as stack:
            stack.enter_context(mock.patch("utils.entity_validation.get_entity_by_username_or_id", return_value=(discussion_entity, None)))
            stack.enter_context(mock.patch.object(telegram_export, "save_discussion_group_info"))
            stack.enter_context(mock.patch.object(telegram_export, "EXPORT_SETTINGS", {"comments_forward_search_limit": 5, "comments_search_limit": 5}))

            forward_message = SimpleNamespace(
                id=50,
                fwd_from=SimpleNamespace(saved_from_msg_id=123, from_id=SimpleNamespace()),
            )
            client.iter_messages.side_effect = [[forward_message], [comment_message]]

            stack.enter_context(mock.patch.object(telegram_export, "process_message_for_api", return_value={"telegram_id": 10}))
            post_mock = stack.enter_context(mock.patch("telegram_export.requests.post", return_value=SimpleNamespace(status_code=200)))

            result = telegram_export.import_discussion_comments(client, "channel123", 777, 123)

        self.assertEqual(result, 1)
        self.assertTrue(post_mock.called)

    def test_import_discussion_comments_no_forward_found(self):
        client = mock.Mock()
        discussion_entity = SimpleNamespace(id=777)

        with ExitStack() as stack:
            stack.enter_context(mock.patch("utils.entity_validation.get_entity_by_username_or_id", return_value=(discussion_entity, None)))
            stack.enter_context(mock.patch.object(telegram_export, "EXPORT_SETTINGS", {"comments_forward_search_limit": 5, "comments_search_limit": 5}))
            stack.enter_context(mock.patch.object(telegram_export, "save_discussion_group_info"))
            client.iter_messages.return_value = []

            result = telegram_export.import_discussion_comments(client, "channel123", 777, 123)

        self.assertEqual(result, 0)

    def test_import_discussion_comments_entity_missing(self):
        client = mock.Mock()

        with mock.patch("utils.entity_validation.get_entity_by_username_or_id", return_value=(None, "missing")):
            result = telegram_export.import_discussion_comments(client, "channel123", 777, 123)

        self.assertEqual(result, 0)

    def test_save_discussion_group_info_success(self):
        client = mock.Mock()
        discussion_entity = SimpleNamespace(id=777)
        info = {"name": "Discussion", "discussion_group_id": 1}

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(telegram_export, "get_channel_info", return_value=info))
            save_mock = stack.enter_context(mock.patch.object(telegram_export, "_save_channel", return_value=True))

            telegram_export.save_discussion_group_info(client, discussion_entity)

        self.assertTrue(save_mock.called)
        saved_info = save_mock.call_args[0][0]
        self.assertEqual(saved_info["id"], str(discussion_entity.id))
        self.assertIsNone(saved_info["discussion_group_id"])
        self.assertTrue(saved_info["name"].startswith("💬"))