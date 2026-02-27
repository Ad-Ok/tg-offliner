"""
Tests for async import, resume and retry functionality.

Covers:
- _process_message_with_retry(): retry logic, FloodWaitError handling
- _get_existing_telegram_ids(): DB query for existing post IDs
- import_channel_direct(resume=True): skip existing posts, preserve media
- import_all_discussion_comments(existing_ids=...): skip existing comments
- API endpoint /add_channel: 202 Accepted, 409 conflict, resume auto-detection
- import_state thread-safety

Run: python -m pytest tests/test_async_import.py -v
  or: python -m unittest tests.test_async_import -v
"""

from __future__ import annotations

import json
import os
import sys
import threading
from contextlib import ExitStack
from types import SimpleNamespace
from unittest import TestCase, mock

os.environ.setdefault("API_ID", "123456")
os.environ.setdefault("API_HASH", "testhash")
os.environ.setdefault("PHONE", "+10000000000")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import telegram_export  # noqa: E402
from database import create_app, init_db  # noqa: E402
from models import db, Post, Channel  # noqa: E402
from tests._telegram_export_base import TelegramExportUnitTestCase  # noqa: E402


# ---------------------------------------------------------------------------
# _process_message_with_retry tests
# ---------------------------------------------------------------------------

class TestProcessMessageWithRetry(TelegramExportUnitTestCase):
    """Tests for _process_message_with_retry()."""

    def test_success_on_first_attempt(self):
        post = SimpleNamespace(id=1)
        with mock.patch.object(
            telegram_export, "process_message_for_api", return_value={"telegram_id": 1}
        ):
            result = telegram_export._process_message_with_retry(post, "ch1", mock.Mock(), "folder")
        self.assertEqual(result, {"telegram_id": 1})

    def test_retries_on_generic_exception(self):
        post = SimpleNamespace(id=42)
        call_count = 0

        def flaky_process(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("transient error")
            return {"telegram_id": 42}

        with mock.patch.object(telegram_export, "process_message_for_api", side_effect=flaky_process):
            with mock.patch("telegram_export.time.sleep"):
                result = telegram_export._process_message_with_retry(post, "ch1", mock.Mock(), "f", max_retries=3)

        self.assertEqual(result, {"telegram_id": 42})
        self.assertEqual(call_count, 3)

    def test_returns_none_after_max_retries(self):
        post = SimpleNamespace(id=99)
        with mock.patch.object(
            telegram_export, "process_message_for_api", side_effect=RuntimeError("permanent")
        ):
            with mock.patch("telegram_export.time.sleep"):
                result = telegram_export._process_message_with_retry(post, "ch1", mock.Mock(), "f", max_retries=2)
        self.assertIsNone(result)

    def test_flood_wait_error_retries_with_correct_delay(self):
        """FloodWaitError should wait exactly e.seconds+1 and retry."""
        from telethon.errors import FloodWaitError

        post = SimpleNamespace(id=10)
        flood_error = FloodWaitError(request=None, capture=5)
        flood_error.seconds = 5

        call_count = 0

        def process_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise flood_error
            return {"telegram_id": 10}

        with mock.patch.object(telegram_export, "process_message_for_api", side_effect=process_side_effect):
            with mock.patch("telegram_export.time.sleep") as sleep_mock:
                result = telegram_export._process_message_with_retry(post, "ch1", mock.Mock(), "f", max_retries=3)

        self.assertEqual(result, {"telegram_id": 10})
        self.assertEqual(call_count, 2)
        sleep_mock.assert_any_call(6)

    def test_exponential_backoff_on_generic_errors(self):
        """Generic errors use exponential backoff: RETRY_BASE_DELAY * 2^(attempt-1)."""
        post = SimpleNamespace(id=7)
        with mock.patch.object(
            telegram_export, "process_message_for_api", side_effect=RuntimeError("fail")
        ):
            with mock.patch("telegram_export.time.sleep") as sleep_mock:
                result = telegram_export._process_message_with_retry(post, "ch1", mock.Mock(), "f", max_retries=3)
        self.assertIsNone(result)
        delays = [call.args[0] for call in sleep_mock.call_args_list]
        self.assertEqual(delays, [2, 4])


# ---------------------------------------------------------------------------
# _get_existing_telegram_ids tests
# ---------------------------------------------------------------------------

class TestGetExistingTelegramIds(TestCase):
    """Tests for _get_existing_telegram_ids() — uses real in-memory DB."""

    def setUp(self):
        self.test_app = create_app(database_uri='sqlite:///:memory:')
        self.test_app.config['TESTING'] = True
        with self.test_app.app_context():
            init_db(self.test_app)
            db.create_all()
            for tid in [10, 20, 30]:
                db.session.add(Post(telegram_id=tid, channel_id='testch', date='2025-01-01'))
            db.session.add(Post(telegram_id=100, channel_id='other', date='2025-01-01'))
            db.session.commit()

    def test_returns_correct_ids(self):
        fake_app_mod = type(sys)("app")
        fake_app_mod.app = self.test_app
        with mock.patch.dict(sys.modules, {"app": fake_app_mod}):
            ids = telegram_export._get_existing_telegram_ids('testch')
        self.assertEqual(ids, {10, 20, 30})

    def test_returns_empty_for_unknown_channel(self):
        fake_app_mod = type(sys)("app")
        fake_app_mod.app = self.test_app
        with mock.patch.dict(sys.modules, {"app": fake_app_mod}):
            ids = telegram_export._get_existing_telegram_ids('nonexistent')
        self.assertEqual(ids, set())


# ---------------------------------------------------------------------------
# import_channel_direct resume tests
# ---------------------------------------------------------------------------

class TestImportChannelDirectResume(TelegramExportUnitTestCase):
    """Tests for import_channel_direct() with resume=True."""

    def _run_import(self, posts, existing_ids, **kwargs):
        """Helper: runs import_channel_direct with resume=True and common mocks."""
        mock_client = mock.Mock()
        entity = SimpleNamespace(username="testch", id=42, count=len(posts))

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(telegram_export, "connect_to_telegram", return_value=mock_client))
            stack.enter_context(mock.patch("utils.entity_validation.get_entity_by_username_or_id", return_value=(entity, None)))
            stack.enter_context(mock.patch("utils.entity_validation.validate_entity_for_download", return_value={"valid": True, "error": None}))
            stack.enter_context(mock.patch.object(telegram_export, "get_channel_info", return_value={"discussion_group_id": None}))
            stack.enter_context(mock.patch.object(telegram_export, "_save_channel", return_value=True))
            stack.enter_context(mock.patch.object(telegram_export, "should_stop_import", return_value=False))
            stack.enter_context(mock.patch.object(telegram_export, "update_import_progress"))
            stack.enter_context(mock.patch.object(telegram_export, "generate_gallery_layouts_for_channel"))
            stack.enter_context(mock.patch.object(telegram_export, "_flush_batch"))
            get_ids_mock = stack.enter_context(
                mock.patch.object(telegram_export, "_get_existing_telegram_ids", return_value=existing_ids)
            )
            clear_mock = stack.enter_context(mock.patch.object(telegram_export, "clear_downloads"))
            process_mock = stack.enter_context(
                mock.patch.object(telegram_export, "_process_message_with_retry",
                                  side_effect=lambda p, *a, **kw: {"telegram_id": p.id})
            )

            mock_client.iter_messages.return_value = posts
            result = telegram_export.import_channel_direct("testch", channel_id="testch", resume=True)

        return result, clear_mock, get_ids_mock, process_mock

    def test_resume_skips_existing_posts(self):
        """Resume should skip posts already in DB."""
        posts = [
            SimpleNamespace(id=1, action=None, fwd_from=None, poll=None),
            SimpleNamespace(id=2, action=None, fwd_from=None, poll=None),
            SimpleNamespace(id=3, action=None, fwd_from=None, poll=None),
        ]
        existing_ids = {1, 3}

        result, clear_mock, get_ids_mock, process_mock = self._run_import(posts, existing_ids)

        self.assertTrue(result["success"])
        self.assertEqual(result["skipped"], 2)
        clear_mock.assert_not_called()
        get_ids_mock.assert_called_once_with("testch")
        # _process_message_with_retry should only be called for post 2
        self.assertEqual(process_mock.call_count, 1)
        self.assertEqual(process_mock.call_args_list[0][0][0].id, 2)

    def test_resume_creates_subdirs_without_clearing(self):
        """Resume should create media/thumbs/avatars dirs but not call clear_downloads."""
        posts = []
        result, clear_mock, _, _ = self._run_import(posts, set())
        clear_mock.assert_not_called()
        channel_folder = os.path.join(self.temp_dir, "testch")
        self.assertTrue(os.path.isdir(os.path.join(channel_folder, "media")))
        self.assertTrue(os.path.isdir(os.path.join(channel_folder, "thumbs")))
        self.assertTrue(os.path.isdir(os.path.join(channel_folder, "avatars")))

    def test_resume_returns_skipped_count(self):
        """Result should contain 'skipped' key."""
        posts = [SimpleNamespace(id=1, action=None, fwd_from=None, poll=None)]
        result, _, _, _ = self._run_import(posts, {1})
        self.assertIn("skipped", result)
        self.assertEqual(result["skipped"], 1)

    def test_non_resume_calls_clear_downloads(self):
        """Non-resume import should call clear_downloads."""
        mock_client = mock.Mock()
        entity = SimpleNamespace(username="testch", id=42, count=0)

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(telegram_export, "connect_to_telegram", return_value=mock_client))
            stack.enter_context(mock.patch("utils.entity_validation.get_entity_by_username_or_id", return_value=(entity, None)))
            stack.enter_context(mock.patch("utils.entity_validation.validate_entity_for_download", return_value={"valid": True, "error": None}))
            stack.enter_context(mock.patch.object(telegram_export, "get_channel_info", return_value={"discussion_group_id": None}))
            stack.enter_context(mock.patch.object(telegram_export, "_save_channel", return_value=True))
            stack.enter_context(mock.patch.object(telegram_export, "should_stop_import", return_value=False))
            stack.enter_context(mock.patch.object(telegram_export, "update_import_progress"))
            stack.enter_context(mock.patch.object(telegram_export, "generate_gallery_layouts_for_channel"))
            stack.enter_context(mock.patch.object(telegram_export, "_flush_batch"))
            clear_mock = stack.enter_context(mock.patch.object(telegram_export, "clear_downloads"))

            mock_client.iter_messages.return_value = []
            result = telegram_export.import_channel_direct("testch", channel_id="testch", resume=False)

        clear_mock.assert_called_once()

    def test_resume_with_discussion_comments(self):
        """Resume should load existing comment IDs and pass them to import_all_discussion_comments."""
        mock_client = mock.Mock()
        entity = SimpleNamespace(username="testch", id=42, count=0)

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(telegram_export, "connect_to_telegram", return_value=mock_client))
            stack.enter_context(mock.patch("utils.entity_validation.get_entity_by_username_or_id", return_value=(entity, None)))
            stack.enter_context(mock.patch("utils.entity_validation.validate_entity_for_download", return_value={"valid": True, "error": None}))
            stack.enter_context(mock.patch.object(telegram_export, "get_channel_info", return_value={"discussion_group_id": 777}))
            stack.enter_context(mock.patch.object(telegram_export, "_save_channel", return_value=True))
            stack.enter_context(mock.patch.object(telegram_export, "should_stop_import", return_value=False))
            stack.enter_context(mock.patch.object(telegram_export, "update_import_progress"))
            stack.enter_context(mock.patch.object(telegram_export, "generate_gallery_layouts_for_channel"))
            stack.enter_context(mock.patch.object(telegram_export, "_flush_batch"))
            stack.enter_context(
                mock.patch.object(telegram_export, "_get_existing_telegram_ids", side_effect=[{1, 2}, {100, 200}])
            )
            disc_mock = stack.enter_context(
                mock.patch.object(telegram_export, "import_all_discussion_comments", return_value=5)
            )

            mock_client.iter_messages.return_value = []
            result = telegram_export.import_channel_direct("testch", channel_id="testch", resume=True)

        self.assertTrue(result["success"])
        disc_mock.assert_called_once()
        call_kwargs = disc_mock.call_args
        self.assertEqual(call_kwargs[1]["existing_ids"], {100, 200})


# ---------------------------------------------------------------------------
# import_all_discussion_comments resume tests
# ---------------------------------------------------------------------------

class TestImportAllDiscussionCommentsResume(TelegramExportUnitTestCase):
    """Tests for import_all_discussion_comments() with existing_ids."""

    def test_skips_existing_comments(self):
        """Comments with IDs in existing_ids should be skipped."""
        client = mock.Mock()
        discussion_entity = SimpleNamespace(id=777)

        forward_msg = SimpleNamespace(
            id=1,
            fwd_from=SimpleNamespace(saved_from_msg_id=100),
        )
        comment_existing = SimpleNamespace(
            id=10,
            fwd_from=None,
            reply_to=SimpleNamespace(reply_to_msg_id=1, reply_to_top_id=1),
        )
        comment_new = SimpleNamespace(
            id=20,
            fwd_from=None,
            reply_to=SimpleNamespace(reply_to_msg_id=1, reply_to_top_id=1),
        )

        with ExitStack() as stack:
            stack.enter_context(mock.patch("utils.entity_validation.get_entity_by_username_or_id", return_value=(discussion_entity, None)))
            stack.enter_context(mock.patch.object(telegram_export, "save_discussion_group_info"))
            stack.enter_context(mock.patch.object(telegram_export, "_flush_batch"))

            client.iter_messages.return_value = [forward_msg, comment_existing, comment_new]

            process_mock = stack.enter_context(
                mock.patch.object(telegram_export, "_process_message_with_retry",
                                  return_value={"telegram_id": 20})
            )

            result = telegram_export.import_all_discussion_comments(
                client, "testch", 777, existing_ids={10}
            )

        self.assertEqual(result, 1)
        self.assertEqual(process_mock.call_count, 1)
        self.assertEqual(process_mock.call_args[0][0].id, 20)

    def test_no_existing_ids_processes_all(self):
        """Without existing_ids, all comments should be processed."""
        client = mock.Mock()
        discussion_entity = SimpleNamespace(id=777)

        forward_msg = SimpleNamespace(
            id=1,
            fwd_from=SimpleNamespace(saved_from_msg_id=100),
        )
        comment = SimpleNamespace(
            id=10,
            fwd_from=None,
            reply_to=SimpleNamespace(reply_to_msg_id=1, reply_to_top_id=1),
        )

        with ExitStack() as stack:
            stack.enter_context(mock.patch("utils.entity_validation.get_entity_by_username_or_id", return_value=(discussion_entity, None)))
            stack.enter_context(mock.patch.object(telegram_export, "save_discussion_group_info"))
            stack.enter_context(mock.patch.object(telegram_export, "_flush_batch"))

            client.iter_messages.return_value = [forward_msg, comment]
            stack.enter_context(
                mock.patch.object(telegram_export, "_process_message_with_retry",
                                  return_value={"telegram_id": 10})
            )

            result = telegram_export.import_all_discussion_comments(client, "testch", 777)

        self.assertEqual(result, 1)

    def test_existing_ids_default_is_empty(self):
        """Calling without existing_ids should default to empty set (no crash)."""
        client = mock.Mock()
        discussion_entity = SimpleNamespace(id=777)

        with ExitStack() as stack:
            stack.enter_context(mock.patch("utils.entity_validation.get_entity_by_username_or_id", return_value=(discussion_entity, None)))
            stack.enter_context(mock.patch.object(telegram_export, "save_discussion_group_info"))
            stack.enter_context(mock.patch.object(telegram_export, "_flush_batch"))
            client.iter_messages.return_value = []

            result = telegram_export.import_all_discussion_comments(client, "testch", 777)
        self.assertEqual(result, 0)


# ---------------------------------------------------------------------------
# API endpoint /add_channel tests (async import, 202, 409, resume)
# ---------------------------------------------------------------------------

class TestAddChannelEndpoint(TestCase):
    """Tests for POST /api/add_channel — async import with resume."""

    def setUp(self):
        from api.channels import channels_bp

        self.flask_app = create_app(database_uri='sqlite:///:memory:')
        self.flask_app.config['TESTING'] = True
        self.flask_app.register_blueprint(channels_bp, url_prefix='/api')

        with self.flask_app.app_context():
            init_db(self.flask_app)
            db.create_all()

        self.client = self.flask_app.test_client()

    def _mock_telegram(self, entity=None, error=None):
        """Returns ExitStack with Telegram mocks."""
        if entity is None:
            entity = SimpleNamespace(username="testch", id=42)
        stack = ExitStack()
        stack.enter_context(mock.patch("api.channels.connect_to_telegram", return_value=mock.Mock()))
        stack.enter_context(mock.patch(
            "utils.entity_validation.get_entity_by_username_or_id",
            return_value=(entity if error is None else None, error)
        ))
        return stack

    def test_returns_202_accepted(self):
        """New import should return 202 Accepted immediately."""
        entity = SimpleNamespace(username="newch", id=99)

        with ExitStack() as stack:
            stack.enter_context(self._mock_telegram(entity))
            stack.enter_context(mock.patch("utils.import_state.get_status", return_value=None))
            app_mock = mock.MagicMock()
            app_mock.set_download_status = mock.Mock()
            stack.enter_context(mock.patch.dict(sys.modules, {"app": app_mock}))
            stack.enter_context(mock.patch("threading.Thread"))

            with self.flask_app.app_context():
                response = self.client.post(
                    '/api/add_channel',
                    data=json.dumps({"channel_username": "newch"}),
                    content_type='application/json'
                )

        self.assertEqual(response.status_code, 202)
        data = json.loads(response.data)
        self.assertEqual(data["channel_id"], "newch")

    def test_returns_409_when_already_downloading(self):
        """Should return 409 if channel is already downloading."""
        entity = SimpleNamespace(username="busych", id=50)

        with ExitStack() as stack:
            stack.enter_context(self._mock_telegram(entity))
            stack.enter_context(mock.patch(
                "utils.import_state.get_status",
                return_value={"status": "downloading", "details": {}}
            ))

            with self.flask_app.app_context():
                response = self.client.post(
                    '/api/add_channel',
                    data=json.dumps({"channel_username": "busych"}),
                    content_type='application/json'
                )

        self.assertEqual(response.status_code, 409)

    def test_auto_detects_resume_for_existing_channel(self):
        """If channel already exists in DB, should set resume=True in response."""
        entity = SimpleNamespace(username="existch", id=77)

        with self.flask_app.app_context():
            ch = Channel(id="existch", name="Existing", changes={})
            db.session.add(ch)
            db.session.commit()

        with ExitStack() as stack:
            stack.enter_context(self._mock_telegram(entity))
            stack.enter_context(mock.patch("utils.import_state.get_status", return_value=None))
            app_mock = mock.MagicMock()
            app_mock.set_download_status = mock.Mock()
            stack.enter_context(mock.patch.dict(sys.modules, {"app": app_mock}))
            stack.enter_context(mock.patch("threading.Thread"))

            with self.flask_app.app_context():
                response = self.client.post(
                    '/api/add_channel',
                    data=json.dumps({"channel_username": "existch"}),
                    content_type='application/json'
                )

        self.assertEqual(response.status_code, 202)
        data = json.loads(response.data)
        self.assertTrue(data["resume"])

    def test_new_channel_resume_false(self):
        """If channel does not exist in DB, resume should be False."""
        entity = SimpleNamespace(username="freshch", id=88)

        with ExitStack() as stack:
            stack.enter_context(self._mock_telegram(entity))
            stack.enter_context(mock.patch("utils.import_state.get_status", return_value=None))
            app_mock = mock.MagicMock()
            app_mock.set_download_status = mock.Mock()
            stack.enter_context(mock.patch.dict(sys.modules, {"app": app_mock}))
            stack.enter_context(mock.patch("threading.Thread"))

            with self.flask_app.app_context():
                response = self.client.post(
                    '/api/add_channel',
                    data=json.dumps({"channel_username": "freshch"}),
                    content_type='application/json'
                )

        self.assertEqual(response.status_code, 202)
        data = json.loads(response.data)
        self.assertFalse(data["resume"])

    def test_missing_channel_username_returns_400(self):
        """Missing channel_username should return 400."""
        with self.flask_app.app_context():
            response = self.client.post(
                '/api/add_channel',
                data=json.dumps({}),
                content_type='application/json'
            )
        self.assertEqual(response.status_code, 400)

    def test_entity_not_found_returns_400(self):
        """If Telegram entity not found, should return 400."""
        with ExitStack() as stack:
            stack.enter_context(self._mock_telegram(error="Channel not found"))

            with self.flask_app.app_context():
                response = self.client.post(
                    '/api/add_channel',
                    data=json.dumps({"channel_username": "missing"}),
                    content_type='application/json'
                )

        self.assertEqual(response.status_code, 400)

    def test_sets_download_status_on_start(self):
        """Should call set_download_status with 'downloading' on import start."""
        entity = SimpleNamespace(username="statch", id=66)

        with ExitStack() as stack:
            stack.enter_context(self._mock_telegram(entity))
            stack.enter_context(mock.patch("utils.import_state.get_status", return_value=None))
            app_mock = mock.MagicMock()
            set_status_mock = mock.Mock()
            app_mock.set_download_status = set_status_mock
            stack.enter_context(mock.patch.dict(sys.modules, {"app": app_mock}))
            stack.enter_context(mock.patch("threading.Thread"))

            with self.flask_app.app_context():
                self.client.post(
                    '/api/add_channel',
                    data=json.dumps({"channel_username": "statch"}),
                    content_type='application/json'
                )

        set_status_mock.assert_called_once()
        args = set_status_mock.call_args
        self.assertEqual(args[0][0], "statch")
        self.assertEqual(args[0][1], "downloading")


# ---------------------------------------------------------------------------
# import_state thread-safety sanity test
# ---------------------------------------------------------------------------

class TestImportStateConcurrency(TestCase):
    """Basic concurrency sanity test for import_state."""

    def test_concurrent_set_and_get(self):
        from utils.import_state import set_status, get_all_statuses

        errors = []

        def writer(ch_id):
            try:
                for i in range(50):
                    set_status(ch_id, 'downloading', {'i': i})
                set_status(ch_id, 'completed', {'done': True})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(f"async_test_ch_{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        self.assertEqual(errors, [])
        statuses = get_all_statuses()
        for i in range(5):
            self.assertEqual(statuses[f"async_test_ch_{i}"]["status"], "completed")
