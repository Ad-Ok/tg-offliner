import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from message_processing import author as author_module
from message_processing import message_transform


class MessageTransformHelperTests(unittest.TestCase):
	def setUp(self) -> None:
		self.temp_dir = tempfile.mkdtemp()
		self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)

		downloads_patch = mock.patch.object(message_transform, "DOWNLOADS_DIR", self.temp_dir)
		downloads_patch.start()
		self.addCleanup(downloads_patch.stop)

	def test_extract_sticker_emoji_returns_value(self):
		class FakeAttr:
			def __init__(self, alt):
				self.alt = alt

		class FakeDocument:
			mime_type = "application/x-tgsticker"
			attributes = [FakeAttr("🔥")]

		class FakeMedia:
			document = FakeDocument()

		with mock.patch.object(message_transform, "MessageMediaDocument", FakeMedia), mock.patch.object(message_transform, "Document", FakeDocument), mock.patch.object(message_transform, "DocumentAttributeSticker", FakeAttr):
			emoji = message_transform.extract_sticker_emoji(FakeMedia())

		self.assertEqual(emoji, "🔥")

	def test_download_media_with_thumbnail_generates_preview(self):
		class FakePhoto:
			pass

		channel_folder = os.path.join(self.temp_dir, "channel_test")
		os.makedirs(os.path.join(channel_folder, "media"), exist_ok=True)

		post = SimpleNamespace(id=123, media=FakePhoto(), poll=None)

		mock_client = mock.Mock()

		def fake_download(media, file):
			target = f"{file}.jpg"
			with open(target, "wb") as handler:
				handler.write(b"fake")
			return target

		mock_client.download_media.side_effect = fake_download

		with mock.patch.object(message_transform, "MessageMediaPhoto", FakePhoto):
			info = message_transform.download_media_with_thumbnail(post, mock_client, channel_folder)

		self.assertIsNotNone(info.media_url)
		self.assertIsNotNone(info.thumb_url)

		thumb_path = os.path.join(self.temp_dir, info.thumb_url)
		self.assertTrue(os.path.exists(thumb_path))

	def test_download_media_with_thumbnail_skips_for_sticker(self):
		class FakeAttr:
			def __init__(self, alt):
				self.alt = alt

		class FakeDocument:
			mime_type = "application/x-tgsticker"
			attributes = [FakeAttr("✨")]

		class FakeMedia:
			document = FakeDocument()

		post = SimpleNamespace(id=10, media=FakeMedia(), poll=None)
		mock_client = mock.Mock()

		with mock.patch.object(message_transform, "MessageMediaDocument", FakeMedia), mock.patch.object(message_transform, "Document", FakeDocument), mock.patch.object(message_transform, "DocumentAttributeSticker", FakeAttr):
			info = message_transform.download_media_with_thumbnail(post, mock_client, self.temp_dir)

		mock_client.download_media.assert_not_called()
		self.assertEqual(info.sticker_emoji, "✨")
		self.assertIsNone(info.media_url)

	def test_render_system_message_handles_phone_call(self):
		class FakeReason:
			pass

		class FakeCallAction:
			video = True
			reason = FakeReason()
			duration = 125

		post = SimpleNamespace(action=FakeCallAction(), from_id=1)
		message = message_transform.render_system_message(post)

		self.assertIn("🎥", message)
		self.assertIn("125", message)

	def test_build_reactions_sums_counts(self):
		reaction = SimpleNamespace(reaction="👍", count=3)
		post = SimpleNamespace(reactions=SimpleNamespace(results=[reaction]))

		result = message_transform.build_reactions(post)

		self.assertEqual(result["total_count"], 3)
		self.assertEqual(result["recent_reactions"], [{"reaction": "👍", "count": 3}])

	def test_build_message_text_combines_poll_and_sticker(self):
		post = SimpleNamespace(
			message="Hello",
			poll=None,
			action=None,
			entities=["dummy"],
		)

		with mock.patch.object(message_transform, "process_poll", return_value="<poll>"), mock.patch.object(message_transform, "parse_entities_to_html", side_effect=lambda text, entities: text.upper()):
			text = message_transform.build_message_text(post, sticker_emoji="🔥")

		self.assertEqual(text, "HELLO<BR><BR><POLL> 🔥")


class ProcessAuthorTests(unittest.TestCase):
	def setUp(self) -> None:
		self.avatar_patch = mock.patch.object(author_module, "download_avatar", return_value="avatars/test.jpg")
		self.avatar_patch.start()
		self.addCleanup(self.avatar_patch.stop)

	def test_process_author_with_user_entity(self):
		sender = SimpleNamespace(first_name="Alice", last_name="Smith", username="alice", id=42, photo=True)
		post = SimpleNamespace(sender=sender, peer_id=None, reply_to=None, fwd_from=None)
		client = mock.Mock()

		result = author_module.process_author(post, client, "channel_folder")

		self.assertEqual(result["author_name"], "Alice Smith")
		self.assertEqual(result["author_link"], "https://t.me/alice")
		self.assertEqual(result["author_avatar"], "avatars/test.jpg")

	def test_process_author_anonymous_comment_uses_peer(self):
		peer = SimpleNamespace(title="Discussion", username="discussiongroup", id=999, photo=True)
		client = mock.Mock()
		client.get_entity.return_value = peer

		post = SimpleNamespace(sender=None, peer_id=peer, reply_to=SimpleNamespace(), fwd_from=None)

		result = author_module.process_author(post, client, "channel_folder")

		client.get_entity.assert_called_once_with(peer)
		self.assertEqual(result["author_name"], "Discussion")
		self.assertEqual(result["author_link"], "https://t.me/discussiongroup")

	def test_process_author_repost_from_name(self):
		fwd = SimpleNamespace(from_name="Original Channel")
		post = SimpleNamespace(sender=None, peer_id=None, reply_to=None, fwd_from=fwd)
		client = mock.Mock()

		result = author_module.process_author(post, client, "channel_folder")

		self.assertEqual(result["repost_author_name"], "Original Channel")
		self.assertIsNone(result["repost_author_link"])
