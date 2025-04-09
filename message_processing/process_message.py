from .author import process_author
from .system_messages import process_system_message
from .polls import process_poll
from .reactions import process_reactions
from .media import process_media

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
        }

    formatted_text = message.message or ""
    poll_html = process_poll(message)
    reactions_html = process_reactions(message)
    media_html = process_media(message, client)

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
    }