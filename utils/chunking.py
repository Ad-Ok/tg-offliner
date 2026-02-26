"""
Модуль для разбиения канала на chunks (части)

Основные принципы:
- Пост + все его комментарии = неделимая единица
- Медиа-группа (альбом) + все комментарии = неделимая единица
- Скрытые посты пропускаются
- Вес: пост=1, комментарий=1, фото в группе=1
"""

from models import Post, Channel, Edit
from utils.post_filtering import should_hide_post


def get_visible_posts(channel_id, include_hidden=False):
    """
    Получает посты канала
    
    Args:
        channel_id: ID канала
        include_hidden: Включать скрытые посты
        
    Returns:
        list[Post]: Список постов, отсортированных по дате (новые первыми)
    """
    posts = Post.query.filter_by(channel_id=channel_id).all()
    
    if include_hidden:
        visible = posts
    else:
        edits = Edit.query.filter_by(channel_id=channel_id).all()
        visible = [p for p in posts if not should_hide_post(p, edits)]
    
    visible.sort(key=lambda p: p.date, reverse=True)
    
    return visible


def get_comments_for_post(telegram_id, discussion_channel_id):
    """
    Получает комментарии для поста из дискуссионной группы
    
    Args:
        telegram_id: ID поста в канале
        discussion_channel_id: ID дискуссионной группы (str или None)
        
    Returns:
        list[Post]: Список комментариев
    """
    if not discussion_channel_id:
        return []
    
    return Post.query.filter_by(
        channel_id=discussion_channel_id,
        reply_to=telegram_id
    ).all()


def build_content_units(channel_id, sort_order='desc', include_hidden=False):
    """
    Строит список ContentUnit из постов канала
    
    ContentUnit = {
        'post': Post,              # Главный пост (или первый в группе)
        'group_posts': list[Post], # Все посты медиа-группы (если is_group=True)
        'comments': list[Post],    # Все комментарии
        'weight': int,             # Сумма: len(group_posts или 1) + len(comments)
        'is_group': bool,          # Это медиа-группа?
        'date': str                # Дата для сортировки
    }
    
    Args:
        channel_id: ID канала
        sort_order: 'desc' (новые первыми) или 'asc' (старые первыми)
        include_hidden: Включать скрытые посты
        
    Returns:
        list[ContentUnit]: Список единиц контента, отсортированных по дате
    """
    channel = Channel.query.get(channel_id)
    if not channel:
        return []
    
    discussion_id = str(channel.discussion_group_id) if channel.discussion_group_id else None
    
    # Получаем посты (включая скрытые если нужно)
    visible_posts = get_visible_posts(channel_id, include_hidden=include_hidden)
    
    # Группируем по grouped_id
    groups = {}  # grouped_id -> list[Post]
    singles = []  # Одиночные посты
    
    for post in visible_posts:
        if post.grouped_id:
            if post.grouped_id not in groups:
                groups[post.grouped_id] = []
            groups[post.grouped_id].append(post)
        else:
            singles.append(post)
    
    units = []
    
    # Обрабатываем одиночные посты
    for post in singles:
        comments = get_comments_for_post(post.telegram_id, discussion_id)
        units.append({
            'post': post,
            'group_posts': [],
            'comments': comments,
            'weight': 1 + len(comments),
            'is_group': False,
            'date': post.date
        })
    
    # Обрабатываем медиа-группы
    for grouped_id, group_posts in groups.items():
        # Сортируем по telegram_id (порядок в альбоме)
        group_posts.sort(key=lambda p: p.telegram_id)
        first_post = group_posts[0]
        
        # Комментарии привязаны к первому посту группы
        comments = get_comments_for_post(first_post.telegram_id, discussion_id)
        
        units.append({
            'post': first_post,
            'group_posts': group_posts,
            'comments': comments,
            'weight': len(group_posts) + len(comments),
            'is_group': True,
            'date': first_post.date
        })
    
    # Сортируем по дате
    # desc = новые первыми (reverse=True), asc = старые первыми (reverse=False)
    units.sort(key=lambda u: u['date'], reverse=(sort_order == 'desc'))
    
    return units


def calculate_chunks(channel_id, items_per_chunk=50, overflow_threshold=0.2, sort_order='desc', include_hidden=False):
    """
    Разбивает канал на chunks
    
    Args:
        channel_id: ID канала
        items_per_chunk: Целевое количество единиц на chunk (по умолчанию 50)
        overflow_threshold: Допустимое превышение (по умолчанию 0.2 = 20%)
        sort_order: 'desc' (новые первыми) или 'asc' (старые первыми)
        include_hidden: Включать скрытые посты в чанки
        
    Returns:
        list[Chunk]: Список chunks
        
    Chunk = {
        'index': int,              # Индекс chunk (0, 1, 2...)
        'units': list[ContentUnit],# Единицы контента
        'total_weight': int,       # Сумма весов
        'posts_count': int,        # Количество постов (без комментариев)
        'comments_count': int,     # Количество комментариев
        'date_from': str,          # Дата первого поста
        'date_to': str             # Дата последнего поста
    }
    """
    units = build_content_units(channel_id, sort_order, include_hidden=include_hidden)
    
    if not units:
        return []
    
    max_weight = items_per_chunk * (1 + overflow_threshold)
    threshold_weight = items_per_chunk * 0.8  # 80% заполнения
    
    chunks = []
    current_chunk = _new_chunk(0)
    
    for unit in units:
        can_fit = current_chunk['total_weight'] + unit['weight'] <= max_weight
        chunk_almost_full = current_chunk['total_weight'] >= threshold_weight
        
        if can_fit:
            # Влезает - добавляем
            _add_unit_to_chunk(current_chunk, unit)
        elif chunk_almost_full and current_chunk['units']:
            # Chunk почти полный - начинаем новый
            chunks.append(current_chunk)
            current_chunk = _new_chunk(len(chunks))
            _add_unit_to_chunk(current_chunk, unit)
        else:
            # Chunk не полный, но unit огромный - добавляем как есть
            _add_unit_to_chunk(current_chunk, unit)
    
    # Не забываем последний chunk
    if current_chunk['units']:
        chunks.append(current_chunk)
    
    return chunks


def _new_chunk(index):
    """Создает пустой chunk"""
    return {
        'index': index,
        'units': [],
        'total_weight': 0,
        'posts_count': 0,
        'comments_count': 0,
        'date_from': None,
        'date_to': None
    }


def _add_unit_to_chunk(chunk, unit):
    """Добавляет unit в chunk"""
    chunk['units'].append(unit)
    chunk['total_weight'] += unit['weight']
    
    if unit['is_group']:
        chunk['posts_count'] += len(unit['group_posts'])
    else:
        chunk['posts_count'] += 1
    
    chunk['comments_count'] += len(unit['comments'])
    
    # Обновляем даты (units отсортированы по дате desc, первый = самый новый)
    if chunk['date_from'] is None or unit['date'] > chunk['date_from']:
        chunk['date_from'] = unit['date']
    if chunk['date_to'] is None or unit['date'] < chunk['date_to']:
        chunk['date_to'] = unit['date']


def get_chunk_posts_and_comments(chunk):
    """
    Извлекает плоские списки постов и комментариев из chunk
    
    Args:
        chunk: Chunk объект
        
    Returns:
        tuple[list[Post], list[Post]]: (посты, комментарии)
    """
    posts = []
    comments = []
    
    for unit in chunk['units']:
        if unit['is_group']:
            posts.extend(unit['group_posts'])
        else:
            posts.append(unit['post'])
        comments.extend(unit['comments'])
    
    return posts, comments
