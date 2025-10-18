import logging
import os
from typing import Optional, Tuple, TypedDict

from config import DOWNLOADS_DIR


class AuthorInfo(TypedDict, total=False):
    author_name: Optional[str]
    author_avatar: Optional[str]
    author_link: Optional[str]
    repost_author_name: Optional[str]
    repost_author_avatar: Optional[str]
    repost_author_link: Optional[str]


def download_avatar(entity, client, channel_folder):
    """Скачивает аватар пользователя или канала в папку канала."""

    if entity and getattr(entity, "photo", None):
        try:
            avatars_folder = os.path.join(channel_folder, "avatars")
            os.makedirs(avatars_folder, exist_ok=True)

            avatar_filename = f"avatar_{entity.id}.jpg"
            avatar_full_path = os.path.join(avatars_folder, avatar_filename)

            avatar_path = client.download_profile_photo(entity, file=avatar_full_path)
            if avatar_path:
                relative_path = os.path.relpath(avatar_path, DOWNLOADS_DIR)
                return relative_path
        except Exception as exc:  # pragma: no cover - network access fallback
            logging.warning("Ошибка при скачивании аватара: %s", exc)
    return None


def _extract_entity_details(entity, client, channel_folder) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not entity:
        return None, None, None

    name: Optional[str] = None
    link: Optional[str] = None

    if hasattr(entity, "first_name") or hasattr(entity, "last_name"):
        name = f"{getattr(entity, 'first_name', '') or ''} {getattr(entity, 'last_name', '') or ''}".strip() or "Без имени"
        if getattr(entity, "username", None):
            link = f"https://t.me/{entity.username}"
        elif getattr(entity, "id", None):
            link = f"https://t.me/user?id={entity.id}"
    elif hasattr(entity, "title"):
        name = getattr(entity, "title", None)
        if getattr(entity, "username", None):
            link = f"https://t.me/{entity.username}"
        elif getattr(entity, "id", None):
            link = f"https://t.me/c/{entity.id}"

    avatar = download_avatar(entity, client, channel_folder)
    return name, avatar, link


def _fallback_for_anonymous_comment(post, client, channel_folder) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    try:
        peer_entity = client.get_entity(getattr(post, "peer_id", None))
        return _extract_entity_details(peer_entity, client, channel_folder)
    except Exception as exc:  # pragma: no cover - defensive logging
        logging.warning("Не удалось получить информацию о peer для анонимного комментария: %s", exc)
    return None, None, None


def _resolve_repost_author(post, client, channel_folder) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    fwd = getattr(post, "fwd_from", None)
    if not fwd:
        return None, None, None

    if getattr(fwd, "from_id", None):
        try:
            entity = client.get_entity(fwd.from_id)
            return _extract_entity_details(entity, client, channel_folder)
        except Exception as exc:  # pragma: no cover - defensive logging
            logging.warning("Ошибка при обработке автора репоста: %s", exc)
    elif getattr(fwd, "from_name", None):
        return fwd.from_name, None, None
    elif getattr(fwd, "saved_from_peer", None):
        try:
            entity = client.get_entity(fwd.saved_from_peer)
            details = _extract_entity_details(entity, client, channel_folder)
            if details[0]:
                return details
            title = getattr(entity, "title", None) or getattr(entity, "username", "Unknown Channel")
            return title, details[1], details[2]
        except Exception as exc:  # pragma: no cover - defensive logging
            logging.warning("Ошибка при обработке канала репоста: %s", exc)

    return None, None, None


def process_author(post, client, channel_folder) -> AuthorInfo:
    """Собирает информацию об авторе сообщения и источнике репоста."""

    sender = getattr(post, "sender", None)
    author_name, author_avatar, author_link = _extract_entity_details(sender, client, channel_folder)

    if not author_name and getattr(post, "peer_id", None) and getattr(post, "reply_to", None):
        author_name, author_avatar, author_link = _fallback_for_anonymous_comment(post, client, channel_folder)

    repost_name, repost_avatar, repost_link = _resolve_repost_author(post, client, channel_folder)

    return AuthorInfo(
        author_name=author_name,
        author_avatar=author_avatar,
        author_link=author_link,
        repost_author_name=repost_name,
        repost_author_avatar=repost_avatar,
        repost_author_link=repost_link,
    )


__all__ = [
    "AuthorInfo",
    "download_avatar",
    "process_author",
]