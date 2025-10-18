"""Transform Telegram messages into API payloads."""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from typing import Optional, TypedDict, List

from message_processing.polls import process_poll
from message_processing import author as author_module
from utils.text_format import parse_entities_to_html
from telethon.tl.types import (
	Document,
	DocumentAttributeSticker,
	MessageMediaDocument,
	MessageMediaPhoto,
	MessageMediaWebPage,
)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")


class ReactionEntry(TypedDict):
	reaction: str
	count: int


class ReactionsInfo(TypedDict):
	total_count: int
	recent_reactions: List[ReactionEntry]


class ProcessedMessage(TypedDict, total=False):
	telegram_id: int
	channel_id: str
	date: Optional[str]
	message: str
	media_url: Optional[str]
	thumb_url: Optional[str]
	media_type: Optional[str]
	mime_type: Optional[str]
	author_name: Optional[str]
	author_avatar: Optional[str]
	author_link: Optional[str]
	repost_author_name: Optional[str]
	repost_author_avatar: Optional[str]
	repost_author_link: Optional[str]
	reactions: Optional[ReactionsInfo]
	grouped_id: Optional[int]
	reply_to: Optional[int]


@dataclass
class MediaInfo:
	"""Intermediate container for media paths and metadata."""

	media_url: Optional[str] = None
	thumb_url: Optional[str] = None
	media_type: Optional[str] = None
	mime_type: Optional[str] = None
	sticker_emoji: Optional[str] = None


def get_channel_folder(channel_name: str) -> str:
	"""Ensure channel folder structure exists and return absolute path."""

	if channel_name.isdigit():
		folder_name = f"channel_{channel_name}"
	else:
		folder_name = channel_name

	channel_folder = os.path.join(DOWNLOADS_DIR, folder_name)
	os.makedirs(channel_folder, exist_ok=True)

	media_folder = os.path.join(channel_folder, "media")
	os.makedirs(media_folder, exist_ok=True)

	return channel_folder


def extract_sticker_emoji(media) -> Optional[str]:
	"""Return sticker emoji for TGS stickers if present."""

	if not isinstance(media, MessageMediaDocument):
		return None

	document = getattr(media, "document", None)
	if not isinstance(document, Document):
		return None

	if getattr(document, "mime_type", None) != "application/x-tgsticker":
		return None

	for attr in getattr(document, "attributes", []):
		if isinstance(attr, DocumentAttributeSticker) and getattr(attr, "alt", None):
			return attr.alt

	return None


def download_media_with_thumbnail(post, client, channel_folder: str) -> MediaInfo:
	"""Download media files and generate thumbnails when applicable."""

	info = MediaInfo()

	if not getattr(post, "media", None) or getattr(post, "poll", None):
		return info

	info.media_type = type(post.media).__name__
	info.sticker_emoji = extract_sticker_emoji(post.media)

	if info.sticker_emoji:
		# Sticker-only payload, no media download required.
		info.media_type = None
		return info

	if isinstance(post.media, MessageMediaWebPage):
		webpage = getattr(post.media, "webpage", None)
		info.media_url = getattr(webpage, "url", None)
		if info.media_url:
			logging.info("MessageMediaWebPage detected: %s", info.media_url)
		return info

	# Download media using Telethon client.
	target_path = os.path.join(channel_folder, "media", f"{post.id}_media")
	media_path = client.download_media(post.media, file=target_path)
	if media_path:
		info.media_url = os.path.relpath(media_path, DOWNLOADS_DIR)

	if isinstance(post.media, MessageMediaDocument) and isinstance(getattr(post.media, "document", None), Document):
		info.mime_type = getattr(post.media.document, "mime_type", None)

	if info.media_url and isinstance(post.media, MessageMediaPhoto):
		full_media_path = os.path.join(DOWNLOADS_DIR, info.media_url)
		thumbs_dir = os.path.join(channel_folder, "thumbs")
		os.makedirs(thumbs_dir, exist_ok=True)
		thumb_path = os.path.join(thumbs_dir, os.path.basename(full_media_path))

		try:
			from PIL import Image

			with Image.open(full_media_path) as img:
				img.thumbnail((300, 300), Image.Resampling.LANCZOS)
				img.save(thumb_path, quality=85, optimize=True)
				logging.info("Created thumbnail %s with size %s", thumb_path, img.size)
		except Exception as exc:  # pragma: no cover - fallback path
			shutil.copy2(full_media_path, thumb_path)
			logging.warning("Failed to create thumbnail, copied original: %s", exc)

		info.thumb_url = os.path.relpath(thumb_path, DOWNLOADS_DIR)

	return info


def render_system_message(post) -> Optional[str]:
	"""Produce textual representation for Telegram service messages."""

	action = getattr(post, "action", None)
	if not action:
		return None

	action_type = type(action).__name__

	if action_type == "MessageActionChannelCreate":
		return f"🎉 Канал создан: {getattr(action, 'title', '')}"
	if action_type == "MessageActionChatEditPhoto":
		return "🖼️ Фото канала изменено"
	if action_type == "MessageActionChatEditTitle":
		return f"✏️ Название изменено на: {getattr(action, 'title', '')}"
	if action_type == "MessageActionChatDeletePhoto":
		return "🗑️ Фото канала удалено"
	if action_type == "MessageActionChatAddUser":
		return "👥 Пользователь добавлен в группу"
	if action_type == "MessageActionChatDeleteUser":
		return "👤❌ Пользователь покинул группу"
	if action_type == "MessageActionChatJoinedByLink":
		return "🔗 Пользователь присоединился по ссылке"
	if action_type == "MessageActionPinMessage":
		return "📌 Сообщение закреплено"
	if action_type == "MessageActionHistoryClear":
		return "🧹 История сообщений очищена"

	is_phone_call = "PhoneCall" in action_type or any(
		hasattr(action, attr) for attr in ("duration", "reason", "video")
	)

	if is_phone_call:
		call_action = action
		direction = "📤 Исходящий" if getattr(post, "from_id", None) else "📥 Входящий"
		video_type = "🎥 Видеозвонок" if getattr(call_action, "video", False) else "📞 Голосовой звонок"

		reason = getattr(call_action, "reason", None)
		status = "❓ Неизвестно"
		if reason:
			reason_type = type(reason).__name__
			if "Missed" in reason_type:
				status = "🔴 Пропущен"
			elif "Busy" in reason_type:
				status = "📵 Занято"
			elif "Hangup" in reason_type:
				status = "✅ Завершен"
			elif "Disconnect" in reason_type:
				status = "🔌 Разорвано"
			else:
				status = f"❓ {reason_type}"

		duration = getattr(call_action, "duration", None)
		if duration:
			minutes = duration // 60
			seconds = duration % 60
			duration_str = f"⏰ {minutes}м {seconds}с ({duration}с)"
		else:
			duration_str = "⏰ Не состоялся"

		return f"{direction} {video_type} - {status} {duration_str}"

	logging.info("Unknown system message type: %s", action_type)
	return f"ℹ️ Системное сообщение: {action_type}"


def build_reactions(post) -> Optional[ReactionsInfo]:
	"""Convert Telethon reactions info to API schema."""

	reactions = getattr(post, "reactions", None)
	if not reactions or not getattr(reactions, "results", None):
		return None

	entries: List[ReactionEntry] = []
	total = 0
	for reaction in reactions.results:
		count = getattr(reaction, "count", 0)
		entries.append({"reaction": str(getattr(reaction, "reaction", "")), "count": count})
		total += count

	return {"total_count": total, "recent_reactions": entries}


def build_message_text(post, sticker_emoji: Optional[str]) -> str:
	"""Compose final message text including polls, system messages and emojis."""

	system_text = render_system_message(post)
	if system_text:
		return system_text

	message_text = getattr(post, "message", "") or ""

	poll_html = process_poll(post)
	if poll_html:
		message_text = f"{message_text}<br><br>{poll_html}" if message_text else poll_html

	if sticker_emoji:
		message_text = f"{message_text} {sticker_emoji}" if message_text else sticker_emoji

	if message_text and getattr(post, "entities", None):
		try:
			formatted = parse_entities_to_html(message_text, post.entities)
			if formatted:
				message_text = formatted
		except Exception as exc:  # pragma: no cover - formatting errors are non-critical
			logging.warning("Failed to apply formatting to message %s: %s", getattr(post, "id", "?"), exc)

	return message_text


def process_message_for_api(post, channel_id: str, client, folder_name: Optional[str] = None) -> Optional[ProcessedMessage]:
	"""Convert Telethon message to payload suitable for REST API."""

	try:
		channel_key = folder_name if folder_name else channel_id
		channel_folder = get_channel_folder(channel_key)

		media_info = download_media_with_thumbnail(post, client, channel_folder)
		author_info = author_module.process_author(post, client, channel_folder)
		message_text = build_message_text(post, media_info.sticker_emoji)
		reactions = build_reactions(post)

		reply_to = None
		reply_obj = getattr(post, "reply_to", None)
		if reply_obj and hasattr(reply_obj, "reply_to_msg_id"):
			reply_to = reply_obj.reply_to_msg_id

		processed: ProcessedMessage = {
			"telegram_id": getattr(post, "id", None),
			"channel_id": channel_id,
			"date": post.date.isoformat() if getattr(post, "date", None) else None,
			"message": message_text,
			"media_url": media_info.media_url,
			"thumb_url": media_info.thumb_url,
			"media_type": media_info.media_type,
			"mime_type": media_info.mime_type,
			"author_name": author_info.get("author_name"),
			"author_avatar": author_info.get("author_avatar"),
			"author_link": author_info.get("author_link"),
			"repost_author_name": author_info.get("repost_author_name"),
			"repost_author_avatar": author_info.get("repost_author_avatar"),
			"repost_author_link": author_info.get("repost_author_link"),
			"reactions": reactions,
			"grouped_id": getattr(post, "grouped_id", None),
			"reply_to": reply_to,
		}

		return processed
	except Exception as exc:  # pragma: no cover - logging for production diagnostics
		logging.error("Ошибка обработки сообщения %s: %s", getattr(post, "id", "?"), exc)
		return None


__all__ = [
	"DOWNLOADS_DIR",
	"MediaInfo",
	"ProcessedMessage",
	"ReactionEntry",
	"ReactionsInfo",
	"build_message_text",
	"build_reactions",
	"download_media_with_thumbnail",
	"extract_sticker_emoji",
	"get_channel_folder",
	"process_message_for_api",
	"render_system_message",
]
