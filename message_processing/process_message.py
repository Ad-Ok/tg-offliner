from .author import process_author
from .system_messages import process_system_message
from .polls import process_poll
from .reactions import process_reactions
from .media import process_media
from telethon.tl.types import PeerChannel

def process_message(message, client):
    """Обрабатывает одно сообщение и возвращает данные для HTML."""
    sender_name, sender_avatar, sender_link = process_author(message.sender, client)
    system_message = process_system_message(message)

    if system_message:
        return {
            "sender_name": sender_name,
            "sender_avatar": sender_avatar,
            "sender_link": sender_link,
            "formatted_text": system_message,
            "media_html": "",
            "reactions_html": "",
            "reply_html": "",
            "repost_html": "",
            "comments_html": "",
        }

    # Обработка текста сообщения
    formatted_text = message.message or ""


    # Обработка голосования, реакций и медиа
    poll_html = process_poll(message)
    reactions_html = process_reactions(message)
    media_html = process_media(message, client)

    # Обработка комментариев
    comments_html = ""
    if message.replies and message.replies.replies > 0:  # Если есть комментарии
        comments_html = "<div class='comments'><h3>Комментарии:</h3><ul>"
        discussion_chat = client.get_entity(PeerChannel(message.peer_id.channel_id))  # Получаем чат обсуждений
        replies = client.iter_messages(discussion_chat, reply_to=message.id, limit=10)  # Получаем до 10 комментариев
        for reply in replies:
            reply_author = reply.sender.first_name if reply.sender and hasattr(reply.sender, 'first_name') else "Аноним"
            reply_text = reply.message if reply.message else "Без текста"
            comments_html += f"<li><strong>{reply_author}:</strong> {reply_text}</li>"
        comments_html += "</ul></div>"

    return {
        "sender_name": sender_name,
        "sender_avatar": sender_avatar,
        "sender_link": sender_link,
        "formatted_text": formatted_text,
        "poll_html": poll_html,
        "media_html": media_html,
        "reactions_html": reactions_html,
        "reply_html": "",
        "repost_html": "",
        "comments_html": comments_html,
    }