import os
import shutil
import sys
import tempfile
import unittest
from contextlib import ExitStack, nullcontext
from datetime import datetime
from types import ModuleType, SimpleNamespace
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

        downloads_patcher = mock.patch.object(telegram_export, "DOWNLOADS_DIR", self.temp_dir)
        self.addCleanup(downloads_patcher.stop)
        downloads_patcher.start()

        self.process_author_patcher = mock.patch.object(
            telegram_export,
            "process_author",
            return_value=("Bob", None, None),
        )
        self.mock_process_author = self.process_author_patcher.start()
        self.addCleanup(self.process_author_patcher.stop)

        self.process_poll_patcher = mock.patch.object(
            telegram_export,
            "process_poll",
            return_value="",
        )
        self.mock_process_poll = self.process_poll_patcher.start()
        self.addCleanup(self.process_poll_patcher.stop)

        self.parse_entities_patcher = mock.patch.object(
            telegram_export,
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

    def test_process_message_basic_text(self):
        folder_name = "test_channel"
        mock_client = mock.Mock()

        self.mock_process_author.return_value = ("Alice", "avatars/alice.jpg", "https://t.me/alice")
        post = self._build_basic_post()
        result = telegram_export.process_message_for_api(post, "channel123", mock_client, folder_name=folder_name)

        self.assertIsNotNone(result)
        self.assertEqual(result["message"], "Hello")
        self.assertEqual(result["author_name"], "Alice")
        self.assertEqual(result["media_url"], None)
        self.assertTrue(os.path.isdir(os.path.join(self.temp_dir, folder_name)))

    def test_process_message_photo_creates_thumbnail(self):
        folder_name = "test_channel"

        class FakePhoto:
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

        with mock.patch.object(telegram_export, "MessageMediaPhoto", FakePhoto):
            result = telegram_export.process_message_for_api(post, "channel123", mock_client, folder_name=folder_name)

        self.assertIsNotNone(result)
        self.assertIsNotNone(result["media_url"])
        self.assertIsNotNone(result["thumb_url"])

        thumb_full_path = os.path.join(self.temp_dir, result["thumb_url"])
        self.assertTrue(os.path.exists(thumb_full_path))

    def test_process_message_web_page(self):
        post = self._build_basic_post(
            media=SimpleNamespace(
                webpage=SimpleNamespace(url="https://example.com"),
            )
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

        post = self._build_basic_post(message="Text", media=media)

        mock_client = mock.Mock()

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

        action = MessageActionChatEditTitle("New Title")
        post = self._build_basic_post(action=action, message="")

        mock_client = mock.Mock()

        result = telegram_export.process_message_for_api(post, "channel123", mock_client)

        self.assertEqual(result["message"], "✏️ Название изменено на: New Title")

    def test_process_message_reactions(self):
        reaction = SimpleNamespace(reaction="👍", count=5)
        reactions = SimpleNamespace(results=[reaction])
        post = self._build_basic_post(reactions=reactions)

        mock_client = mock.Mock()

        result = telegram_export.process_message_for_api(post, "channel123", mock_client)

        self.assertEqual(result["reactions"]["total_count"], 5)
        self.assertEqual(result["reactions"]["recent_reactions"], [{"reaction": "👍", "count": 5}])

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

    def test_generate_gallery_layouts_creates_layout(self):
        image_dir = os.path.join(self.temp_dir, "channel123", "thumbs")
        os.makedirs(image_dir, exist_ok=True)
        rel1 = os.path.join("channel123", "thumbs", "img1.jpg")
        rel2 = os.path.join("channel123", "thumbs", "img2.jpg")
        open(os.path.join(self.temp_dir, rel1), "wb").close()
        open(os.path.join(self.temp_dir, rel2), "wb").close()

        fake_posts = [
            SimpleNamespace(grouped_id=111, media_type="MessageMediaPhoto", thumb_url=rel1, telegram_id=2),
            SimpleNamespace(grouped_id=111, media_type="MessageMediaPhoto", thumb_url=rel2, telegram_id=1),
        ]

        created_layouts = []
        session_mock = mock.Mock()

        class FakePostModel:
            query = mock.Mock()

        FakePostModel.query.filter_by.return_value.all.return_value = fake_posts

        class FakeLayout:
            query = mock.Mock()

            def __init__(self, grouped_id, channel_id, json_data):
                created_layouts.append(
                    {
                        "grouped_id": grouped_id,
                        "channel_id": channel_id,
                        "json_data": json_data,
                    }
                )

        FakeLayout.query.filter_by.return_value.first.return_value = None

        fake_models = ModuleType("models")
        fake_models.Post = FakePostModel
        fake_models.Layout = FakeLayout
        fake_models.db = SimpleNamespace(session=session_mock)

        class FakeApp:
            def app_context(self):
                return nullcontext()

        fake_app_module = ModuleType("app")
        fake_app_module.app = FakeApp()

        layout_data = {"cells": [{"image_index": 0}, {"image_index": 1}]}

        with mock.patch.dict(sys.modules, {"app": fake_app_module, "models": fake_models}):
            with mock.patch("utils.gallery_layout.generate_gallery_layout", return_value=layout_data):
                telegram_export.generate_gallery_layouts_for_channel("channel123")

        self.assertEqual(len(created_layouts), 1)
        self.assertEqual(created_layouts[0]["json_data"], layout_data)
        session_mock.add.assert_called_once()
        session_mock.commit.assert_called_once()

    def test_generate_gallery_layouts_skips_existing_layout(self):
        image_dir = os.path.join(self.temp_dir, "channel123", "thumbs")
        os.makedirs(image_dir, exist_ok=True)
        rel1 = os.path.join("channel123", "thumbs", "img1.jpg")
        rel2 = os.path.join("channel123", "thumbs", "img2.jpg")
        open(os.path.join(self.temp_dir, rel1), "wb").close()
        open(os.path.join(self.temp_dir, rel2), "wb").close()

        fake_posts = [
            SimpleNamespace(grouped_id=111, media_type="MessageMediaPhoto", thumb_url=rel1, telegram_id=1),
            SimpleNamespace(grouped_id=111, media_type="MessageMediaPhoto", thumb_url=rel2, telegram_id=2),
        ]

        session_mock = mock.Mock()

        class FakePostModel:
            query = mock.Mock()

        FakePostModel.query.filter_by.return_value.all.return_value = fake_posts

        existing_layout = SimpleNamespace(json_data={"cells": [{"image_index": 0}, {"image_index": 1}]})

        class FakeLayout:
            query = mock.Mock()

            def __init__(self, *args, **kwargs):
                raise AssertionError("Layout should not be created when valid layout exists")

        FakeLayout.query.filter_by.return_value.first.return_value = existing_layout

        fake_models = ModuleType("models")
        fake_models.Post = FakePostModel
        fake_models.Layout = FakeLayout
        fake_models.db = SimpleNamespace(session=session_mock)

        class FakeApp:
            def app_context(self):
                return nullcontext()

        fake_app_module = ModuleType("app")
        fake_app_module.app = FakeApp()

        with mock.patch.dict(sys.modules, {"app": fake_app_module, "models": fake_models}):
            with mock.patch("utils.gallery_layout.generate_gallery_layout") as layout_mock:
                telegram_export.generate_gallery_layouts_for_channel("channel123")

        layout_mock.assert_not_called()
        session_mock.add.assert_not_called()
        session_mock.commit.assert_not_called()

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
            client.iter_messages.side_effect = [
                [forward_message],
                [comment_message],
            ]

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
        info = {
            "name": "Discussion",
            "discussion_group_id": 1,
        }

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(telegram_export, "get_channel_info", return_value=info))
            post_mock = stack.enter_context(mock.patch("telegram_export.requests.post", return_value=SimpleNamespace(status_code=200)))

            telegram_export.save_discussion_group_info(client, discussion_entity)

        self.assertTrue(post_mock.called)
        updated_payload = post_mock.call_args.kwargs["json"]
        self.assertEqual(updated_payload["id"], str(discussion_entity.id))
        self.assertIsNone(updated_payload["discussion_group_id"])
        self.assertTrue(updated_payload["name"].startswith("💬"))

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

    def test_main_success(self):
        with ExitStack() as stack:
            stack.enter_context(mock.patch("telegram_export.time.time", side_effect=[0.0, 2.5]))
            import_mock = stack.enter_context(mock.patch.object(telegram_export, "import_channel_direct", return_value={"success": True, "processed": 3, "comments": 1}))
            print_mock = stack.enter_context(mock.patch("builtins.print"))

            telegram_export.main("channel123")

        import_mock.assert_called_once_with("channel123")
        print_mock.assert_any_call("✅ Импорт завершён за 2.50 секунд.")
        print_mock.assert_any_call("   Постов обработано: 3")
        print_mock.assert_any_call("   Комментариев импортировано: 1")

    def test_main_failure(self):
        with ExitStack() as stack:
            stack.enter_context(mock.patch("telegram_export.time.time", side_effect=[0.0, 0.0]))
            stack.enter_context(mock.patch.object(telegram_export, "import_channel_direct", return_value={"success": False, "error": "boom"}))
            print_mock = stack.enter_context(mock.patch("builtins.print"))

            telegram_export.main("channel123")

        print_mock.assert_any_call("❌ Ошибка при импорте: boom")


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
