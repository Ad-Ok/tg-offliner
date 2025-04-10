from telethon.tl.types import (
    MessageEntityBold, MessageEntityItalic, MessageEntityUnderline,
    MessageEntityStrike, MessageEntityCode, MessageEntityPre,
    MessageEntityTextUrl, MessageEntityMention
)

def parse_entities_to_html(message_text, entities):
    """Преобразует текст сообщения с форматированием в HTML."""
    if not entities:
        # Если нет форматирования, заменяем \n на <br> для разбиения на строки
        return message_text.replace('\n', '<br>')

    html_text = message_text
    offset_adjustment = 0  # Для корректировки смещения после вставки тегов

    for entity in sorted(entities, key=lambda e: e.offset):
        start = entity.offset + offset_adjustment
        end = start + entity.length

        if isinstance(entity, MessageEntityBold):
            html_text = html_text[:start] + "<b>" + html_text[start:end] + "</b>" + html_text[end:]
            offset_adjustment += 7  # <b> и </b> добавляют 7 символов
        elif isinstance(entity, MessageEntityItalic):
            html_text = html_text[:start] + "<i>" + html_text[start:end] + "</i>" + html_text[end:]
            offset_adjustment += 7  # <i> и </i> добавляют 7 символов
        elif isinstance(entity, MessageEntityUnderline):
            html_text = html_text[:start] + "<u>" + html_text[start:end] + "</u>" + html_text[end:]
            offset_adjustment += 7  # <u> и </u> добавляют 7 символов
        elif isinstance(entity, MessageEntityStrike):
            html_text = html_text[:start] + "<s>" + html_text[start:end] + "</s>" + html_text[end:]
            offset_adjustment += 7  # <s> и </s> добавляют 7 символов
        elif isinstance(entity, MessageEntityCode):
            html_text = html_text[:start] + "<code>" + html_text[start:end] + "</code>" + html_text[end:]
            offset_adjustment += 13  # <code> и </code> добавляют 13 символов
        elif isinstance(entity, MessageEntityPre):
            html_text = html_text[:start] + "<pre>" + html_text[start:end] + "</pre>" + html_text[end:]
            offset_adjustment += 11  # <pre> и </pre> добавляют 11 символов
        elif isinstance(entity, MessageEntityTextUrl):
            html_text = html_text[:start] + f'<a href="{entity.url}">' + html_text[start:end] + "</a>" + html_text[end:]
            offset_adjustment += len(f'<a href="{entity.url}"></a>') - entity.length
        elif isinstance(entity, MessageEntityMention):
            html_text = html_text[:start] + f'<a href="https://t.me/{html_text[start:end]}">' + html_text[start:end] + "</a>" + html_text[end:]
            offset_adjustment += len(f'<a href="https://t.me/"></a>') - entity.length

    # Заменяем оставшиеся \n на <br> для разбиения на строки
    html_text = html_text.replace('\n', '<br>')
    return html_text