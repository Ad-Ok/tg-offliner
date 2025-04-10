from collections import deque
from html import escape, unescape
from html.parser import HTMLParser
from typing import Iterable, Tuple, List

from telethon.helpers import add_surrogate, del_surrogate, within_surrogate, strip_text
from telethon.tl import TLObject
from telethon.types import (
    MessageEntityBold, MessageEntityItalic, MessageEntityCode,
    MessageEntityPre, MessageEntityEmail, MessageEntityUrl,
    MessageEntityTextUrl, MessageEntityMentionName,
    MessageEntityUnderline, MessageEntityStrike, MessageEntityBlockquote,
    MessageEntityCustomEmoji, MessageEntitySpoiler, TypeMessageEntity
)

class HTMLToTelegramParser(HTMLParser):
    """
    Парсер HTML в entities Telegram.
    """

    def __init__(self):
        """
        Инициализирует парсер.
        """
        super().__init__()
        self.text = ''
        self.entities = []
        self._stack = deque()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """
        Обрабатывает начальные теги.
        """
        attrs_dict = dict(attrs)
        entity_type, args = self._get_entity_type(tag, attrs_dict)

        if entity_type:
            self._stack.append((tag, entity_type, args))
            # Начало сущности, добавляем в стек
            args['offset'] = len(self.text)
            args['length'] = 0

    def handle_data(self, data: str) -> None:
        """
        Обрабатывает текстовые данные.
        """
        self.text += data
        # Увеличиваем длину сущностей на стеке
        for _, _, args in self._stack:
            args['length'] += len(data)

    def handle_endtag(self, tag: str) -> None:
        """
        Обрабатывает конечные теги.
        """
        if self._stack and self._stack[0][0] == tag:
            _, entity_type, args = self._stack.popleft()
            # Закрываем сущность и добавляем в список
            self.entities.append(entity_type(**args))

    def _get_entity_type(self, tag: str, attrs: dict[str, str | None]) -> tuple[
        type[TypeMessageEntity] | None, dict]:
        """
        Определяет тип сущности по тегу и атрибутам.
        """
        entity_type = None
        args = {}
        if tag in ('strong', 'b'):
            entity_type = MessageEntityBold
        elif tag in ('em', 'i'):
            entity_type = MessageEntityItalic
        elif tag == 'u':
            entity_type = MessageEntityUnderline
        elif tag in ('del', 's'):
            entity_type = MessageEntityStrike
        elif tag == 'blockquote':
            entity_type = MessageEntityBlockquote
        elif tag == 'tg-spoiler':
            entity_type = MessageEntitySpoiler
        elif tag == 'code':
            if self._stack and self._stack[0][1] == MessageEntityPre:
                try:
                    self._stack[0][2]['language'] = attrs['class'][len('language-'):]
                except (KeyError, TypeError):
                    pass
            else:
                entity_type = MessageEntityCode
        elif tag == 'pre':
            entity_type = MessageEntityPre
            args['language'] = ''
        elif tag == 'a':
            url = attrs.get('href')
            if url:
                if url.startswith('mailto:'):
                    entity_type = MessageEntityEmail
                    args['email'] = url[len('mailto:'):]
                elif url == self.get_starttag_text():
                    entity_type = MessageEntityUrl
                    args['url'] = url
                else:
                    entity_type = MessageEntityTextUrl
                    args['url'] = del_surrogate(url)
        elif tag == 'tg-emoji':
            emoji_id = attrs.get('emoji-id')
            if emoji_id:
                try:
                    args['document_id'] = int(emoji_id)
                    entity_type = MessageEntityCustomEmoji
                except ValueError:
                    pass

        return entity_type, args

class CustomHtmlParser:
    """
    Парсер HTML для Telegram.
    """

    @staticmethod
    def parse(html: str) -> Tuple[str, List[TypeMessageEntity]]:
        """
        Парсит HTML и возвращает текст и entities.
        """
        if not html:
            return '', []

        parser = HTMLToTelegramParser()
        parser.feed(add_surrogate(html))
        text = strip_text(parser.text, parser.entities)
        # Сортируем entities по смещению
        parser.entities.sort(key=lambda entity: entity.offset)
        return del_surrogate(text), parser.entities

    @staticmethod
    def unparse(text: str, entities: Iterable[TypeMessageEntity]) -> str:
        """
        Преобразует текст и entities в HTML.
        """
        if not text:
            return ''
        if not entities:
            return escape(text)

        text = add_surrogate(text)
        # Преобразуем итератор в список для возможности сортировки
        entities = list(entities)
        # Сортируем entities по смещению в обратном порядке
        entities.sort(key=lambda e: (e.offset, -e.length), reverse=True)

        # Используем map для создания списка вставок
        insert_at = list(map(lambda e: (
            (e.offset, CustomHtmlParser._get_formatter(e, text)[0]),
            (e.offset + e.length, CustomHtmlParser._get_formatter(e, text)[1])
        ), entities))

        # Объединяем вставки в один список и сортируем
        insert_at = [item for sublist in insert_at for item in sublist]
        insert_at.sort(key=lambda t: (t[0], -len(t[1])), reverse=True)

        # Вставляем теги в текст
        for at, what in insert_at:
            at = next((i for i in range(at, len(text)) if not within_surrogate(text, i)), len(text))
            text = text[:at] + what + text[at:]

        return del_surrogate(escape(text))

    @staticmethod
    def _get_formatter(entity: TypeMessageEntity, text: str) -> tuple[str, str]:
        """
        Возвращает теги форматирования для сущности.
        """
        s = entity.offset
        e = entity.offset + entity.length
        if isinstance(entity, MessageEntityBold):
            return '<strong>', '</strong>'
        elif isinstance(entity, MessageEntityItalic):
            return '<em>', '</em>'
        elif isinstance(entity, MessageEntityCode):
            return '<code>', '</code>'
        elif isinstance(entity, MessageEntityUnderline):
            return '<u>', '</u>'
        elif isinstance(entity, MessageEntityStrike):
            return '<del>', '</del>'
        elif isinstance(entity, MessageEntityBlockquote):
            return '<blockquote>', '</blockquote>'
        elif isinstance(entity, MessageEntitySpoiler):
            return '<tg-spoiler>', '</tg-spoiler>'
        elif isinstance(entity, MessageEntityPre):
            return f"<pre><code class='language-{entity.language}'>", "</code></pre>"
        elif isinstance(entity, MessageEntityEmail):
            return f'<a href="mailto:{text[s:e]}">', '</a>'
        elif isinstance(entity, MessageEntityUrl):
            return f'<a href="{text[s:e]}">', '</a>'
        elif isinstance(entity, MessageEntityTextUrl):
            return f'<a href="{escape(entity.url)}">', '</a>'
        elif isinstance(entity, MessageEntityMentionName):
            return f'<a href="tg://user?id={entity.user_id}">', '</a>'
        elif isinstance(entity, MessageEntityCustomEmoji):
            return f'<tg-emoji emoji-id="{entity.document_id}">', '</tg-emoji>'
        else:
            return '', ''

from typing import List
from telethon.types import TypeMessageEntity
from .text_format import CustomHtmlParser

def parse_entities_to_html(text: str, entities: List[TypeMessageEntity]) -> str:
    """
    Преобразует текст и сущности Telegram в HTML.

    :param text: Исходный текст сообщения.
    :param entities: Список сущностей (например, жирный текст, ссылки и т.д.).
    :return: Текст, преобразованный в HTML.
    """
    if not text:
        return ""
    if not entities:
        return text.replace("\n", "<br>")  # Заменяем \n на <br> для разбиения на строки

    # Используем CustomHtmlParser.unparse для преобразования в HTML
    html = CustomHtmlParser.unparse(text, entities)

    # Декодируем экранированный HTML
    html = unescape(html)

    return html