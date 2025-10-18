from __future__ import annotations

from contextlib import ExitStack
from unittest import mock

from tests._telegram_export_base import TelegramExportUnitTestCase, telegram_export


class TelegramExportMainTests(TelegramExportUnitTestCase):
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