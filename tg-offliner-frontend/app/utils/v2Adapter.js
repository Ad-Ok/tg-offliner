/**
 * Адаптер API v2 → формат компонентов
 * 
 * Компоненты (Wall, Post, Group, PostQuote) ожидают плоский формат:
 * - author_name, author_avatar, author_link (не вложенный author{})  
 * - isHidden (не is_hidden)
 * - Комментарии как отдельные посты с reply_to в общем массиве
 * - Группы как отдельные посты с одинаковым grouped_id в общем массиве
 * 
 * API v2 возвращает вложенный формат:
 * - author: {name, avatar, link}
 * - is_hidden
 * - comments: [{...}] вложенные в пост
 * - group_posts: [{...}] вложенные в пост
 * 
 * Этот адаптер конвертирует v2 → плоский формат для компонентов
 */

/**
 * Трансформирует один пост из v2 формата в плоский формат компонентов
 * 
 * @param {Object} post - пост в v2 формате
 * @returns {Object} - пост в плоском формате
 */
function flattenPost(post) {
  const flat = { ...post }
  
  // author: {name, avatar, link} → author_name, author_avatar, author_link
  if (post.author) {
    flat.author_name = post.author.name || null
    flat.author_avatar = post.author.avatar || null
    flat.author_link = post.author.link || null
  } else {
    flat.author_name = post.author_name || null
    flat.author_avatar = post.author_avatar || null
    flat.author_link = post.author_link || null
  }
  
  // repost_author: {name, avatar, link} → repost_author_name, etc.
  if (post.repost_author) {
    flat.repost_author_name = post.repost_author.name || null
    flat.repost_author_avatar = post.repost_author.avatar || null
    flat.repost_author_link = post.repost_author.link || null
  } else {
    flat.repost_author_name = post.repost_author_name || null
    flat.repost_author_avatar = post.repost_author_avatar || null
    flat.repost_author_link = post.repost_author_link || null
  }
  
  // is_hidden → isHidden
  flat.isHidden = post.is_hidden || false
  
  return flat
}

/**
 * Трансформирует ответ API v2 в массив постов для компонентов
 * 
 * API v2 возвращает:
 * - posts[].group_posts — вложенные посты группы
 * - posts[].comments — вложенные комментарии
 * 
 * Компоненты ожидают:
 * - Плоский массив, где группы = несколько постов с одинаковым grouped_id
 * - Плоский массив, где комментарии = посты с reply_to и channel_id дискуссии
 * 
 * @param {Object[]} v2Posts - массив постов из API v2
 * @param {string|null} discussionGroupId - ID дискуссионной группы (для channel_id комментариев)
 * @returns {Object[]} - плоский массив постов для компонентов
 */
export function transformV2PostsToFlat(v2Posts, discussionGroupId = null) {
  const result = []
  
  for (const post of v2Posts) {
    // Трансформируем основной пост
    const mainPost = flattenPost(post)
    
    // Если есть group_posts - добавляем все посты группы (в т.ч. основной)
    if (post.group_posts && post.group_posts.length > 0) {
      // group_posts уже содержит все посты группы включая основной
      for (const gp of post.group_posts) {
        const flatGp = flattenPost(gp)
        // Переносим layout из главного поста на все посты группы
        if (post.layout) {
          flatGp.layout = post.layout
        }
        result.push(flatGp)
      }
    } else {
      // Обычный пост (не группа)
      result.push(mainPost)
    }
    
    // Добавляем комментарии как отдельные посты
    if (post.comments && post.comments.length > 0) {
      for (const comment of post.comments) {
        const flatComment = flattenPost(comment)
        // Комментарии из дискуссионной группы имеют channel_id дискуссии
        // reply_to и channel_id уже правильные от API
        result.push(flatComment)
      }
    }
  }
  
  return result
}

export default transformV2PostsToFlat
