from .author import process_author
from .system_messages import process_system_message
from .polls import process_poll
from .reactions import process_reactions
from .media import process_media
from telethon.tl.types import PeerChannel
from html_generator import generate_message_html
from datetime import datetime
from utils.date_utils import format_message_date
from utils.text_format import parse_entities_to_html

def process_message(message, client):
    """Обрабатывает одно сообщение и возвращает данные для HTML."""
    sender_name, sender_avatar, sender_link = process_author(message.sender, client, message.peer_id)
    system_message = process_system_message(message)

    # Форматируем дату сообщения
    message_date = format_message_date(message.date)

    # Обработка репоста
    repost_html = ""
    if message.fwd_from:
        repost_source, repost_avatar, repost_link = process_author(None, client, from_id=message.fwd_from.from_id)
        repost_date = format_message_date(message.fwd_from.date)
        repost_html = f"""
        <div class="repost">
            <p>Репост от: <strong><a href="{repost_link}" target="_blank">{repost_source}</a></strong></p>
            <p class="date">Дата: {repost_date}</p>
        </div>
        """

    if system_message:
        return {
            "sender_name": sender_name,
            "sender_avatar": sender_avatar,
            "sender_link": sender_link,
            "formatted_text": system_message,
            "media_html": "",
            "reactions_html": "",
            "reply_html": "",
            "repost_html": repost_html,
            "comments_html": "",
            "message_date": message_date,
        }

    # Обработка текста сообщения с учётом форматирования
    raw_text = message.message or ""
    formatted_text = parse_entities_to_html(raw_text, message.entities)

    # Обработка голосования, реакций и медиа
    poll_html = process_poll(message)
    reactions_html = process_reactions(message)
    media_html = process_media(message, client)

    # Обработка комментариев
    comments_html = ""
    if message.replies and message.replies.replies > 0:  # Если есть комментарии
        discussion_chat = client.get_entity(PeerChannel(message.peer_id.channel_id))  # Получаем чат обсуждений
        replies = client.iter_messages(discussion_chat, reply_to=message.id, limit=10, reverse=True)  # Получаем до 10 комментариев
        for reply in replies:
            # Обрабатываем комментарий как полноценное сообщение
            reply_data = process_message(reply, client)
            comments_html += generate_message_html(
                reply_data["sender_name"], reply_data["sender_avatar"], reply_data["sender_link"],
                reply_data["formatted_text"], reply_data.get("poll_html", ""),
                reply_data.get("media_html", ""), reply_data.get("reactions_html", ""),
                reply_data.get("reply_html", ""), reply_data.get("repost_html", ""),
                reply_data["message_date"]
            )

    return {
        "sender_name": sender_name,
        "sender_avatar": sender_avatar,
        "sender_link": sender_link,
        "formatted_text": formatted_text,  # Используем отформатированный текст
        "poll_html": poll_html,
        "media_html": media_html,
        "reactions_html": reactions_html,
        "reply_html": "",
        "repost_html": repost_html,
        "comments_html": comments_html,
        "message_date": message_date,
    }