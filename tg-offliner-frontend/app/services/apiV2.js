/**
 * API v2 Client
 * 
 * Единый клиент для работы с API v2
 * Все endpoints возвращают полные данные (posts + layouts + hidden states)
 */

import { apiBase } from '~/services/api'

/**
 * @typedef {Object} ChannelSettings
 * @property {Object} display
 * @property {string} display.sort_order - 'asc' | 'desc'
 * @property {number} display.items_per_chunk
 * @property {Object} export
 * @property {string} export.page_size
 * @property {number[]} export.margins
 */

/**
 * @typedef {Object} Pagination
 * @property {number|null} current_chunk
 * @property {number} total_chunks
 * @property {number} total_posts
 * @property {number} total_comments
 * @property {number} items_per_chunk
 * @property {boolean} has_next
 * @property {boolean} has_prev
 */

/**
 * @typedef {Object} AppliedParams
 * @property {string} sort_order
 * @property {number|null} chunk
 * @property {number} items_per_chunk
 * @property {boolean} include_hidden
 * @property {boolean} include_comments
 * @property {string} source - 'url' | 'saved' | 'default'
 */

/**
 * @typedef {Object} PostAuthor
 * @property {string} name
 * @property {string|null} avatar
 * @property {string|null} link
 */

/**
 * @typedef {Object} Post
 * @property {number} id
 * @property {number} telegram_id
 * @property {string} channel_id
 * @property {string} date
 * @property {string|null} message
 * @property {string|null} media_url
 * @property {string|null} thumb_url
 * @property {string|null} media_type
 * @property {string|null} mime_type
 * @property {PostAuthor|null} author
 * @property {PostAuthor|null} repost_author
 * @property {Object|null} reactions
 * @property {number|null} grouped_id
 * @property {number|null} reply_to
 * @property {boolean} is_hidden
 * @property {Object|null} layout
 * @property {Post[]|null} group_posts
 * @property {Post[]} comments
 * @property {number} comments_count
 */

/**
 * @typedef {Object} Channel
 * @property {string} id
 * @property {string} name
 * @property {string|null} avatar
 * @property {string|null} description
 * @property {number|null} discussion_group_id
 * @property {ChannelSettings} settings
 */

/**
 * @typedef {Object} GetPostsResponse
 * @property {Channel} channel
 * @property {Pagination} pagination
 * @property {AppliedParams} applied_params
 * @property {Post[]} posts
 */

/**
 * @typedef {Object} GetPostsOptions
 * @property {string} [sortOrder] - 'asc' | 'desc'
 * @property {number} [chunk] - номер chunk
 * @property {number} [itemsPerChunk] - размер chunk
 * @property {boolean} [includeHidden] - включать скрытые
 * @property {boolean} [includeComments] - включать комментарии
 */

/**
 * Получить посты канала
 * 
 * @param {string} channelId - ID канала
 * @param {GetPostsOptions} [options] - опции запроса
 * @returns {Promise<GetPostsResponse>}
 */
export async function getChannelPosts(channelId, options = {}) {
  const params = new URLSearchParams()
  
  if (options.sortOrder !== undefined) {
    params.set('sort_order', options.sortOrder)
  }
  
  if (options.chunk !== undefined && options.chunk !== null) {
    params.set('chunk', String(options.chunk))
  }
  
  if (options.itemsPerChunk !== undefined) {
    params.set('items_per_chunk', String(options.itemsPerChunk))
  }
  
  if (options.includeHidden !== undefined) {
    params.set('include_hidden', options.includeHidden ? 'true' : 'false')
  }
  
  if (options.includeComments !== undefined) {
    params.set('include_comments', options.includeComments ? 'true' : 'false')
  }
  
  const queryString = params.toString()
  const url = `${apiBase}/api/v2/channels/${channelId}/posts${queryString ? '?' + queryString : ''}`
  
  const response = await fetch(url)
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(error.error || `HTTP ${response.status}`)
  }
  
  return response.json()
}

/**
 * Получить метаданные chunks канала
 * 
 * @param {string} channelId - ID канала
 * @param {Object} [options]
 * @param {string} [options.sortOrder]
 * @param {number} [options.itemsPerChunk]
 * @returns {Promise<Object>}
 */
export async function getChannelChunks(channelId, options = {}) {
  const params = new URLSearchParams()
  
  if (options.sortOrder !== undefined) {
    params.set('sort_order', options.sortOrder)
  }
  
  if (options.itemsPerChunk !== undefined) {
    params.set('items_per_chunk', String(options.itemsPerChunk))
  }
  
  const queryString = params.toString()
  const url = `${apiBase}/api/v2/channels/${channelId}/chunks${queryString ? '?' + queryString : ''}`
  
  const response = await fetch(url)
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(error.error || `HTTP ${response.status}`)
  }
  
  return response.json()
}

/**
 * Обновить настройки канала
 * 
 * @param {string} channelId - ID канала
 * @param {Partial<ChannelSettings>} settings - настройки для обновления
 * @returns {Promise<{success: boolean, settings: ChannelSettings}>}
 */
export async function updateChannelSettings(channelId, settings) {
  const url = `${apiBase}/api/v2/channels/${channelId}/settings`
  
  const response = await fetch(url, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(settings)
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(error.error || `HTTP ${response.status}`)
  }
  
  return response.json()
}

/**
 * Скрыть или показать пост
 * 
 * @param {string} channelId - ID канала
 * @param {number} telegramId - ID поста
 * @param {boolean} hidden - скрыть или показать
 * @returns {Promise<{success: boolean, hidden: boolean}>}
 */
export async function setPostVisibility(channelId, telegramId, hidden) {
  const url = `${apiBase}/api/v2/posts/${channelId}/${telegramId}/visibility`
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ hidden })
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(error.error || `HTTP ${response.status}`)
  }
  
  return response.json()
}

/**
 * Обновить layout галереи
 * 
 * @param {number|string} groupedId - ID группы
 * @param {Object} options
 * @param {string} options.channelId - ID канала
 * @param {number} [options.columns]
 * @param {string} [options.borderWidth]
 * @param {boolean} [options.noCrop]
 * @param {boolean} [options.regenerate] - пересоздать layout
 * @returns {Promise<{success: boolean, layout: Object}>}
 */
export async function updateLayout(groupedId, options) {
  const url = `${apiBase}/api/v2/layouts/${groupedId}`
  
  const body = {
    channel_id: options.channelId
  }
  
  if (options.columns !== undefined) {
    body.columns = options.columns
  }
  
  if (options.borderWidth !== undefined) {
    body.border_width = options.borderWidth
  }
  
  if (options.noCrop !== undefined) {
    body.no_crop = options.noCrop
  }
  
  if (options.regenerate !== undefined) {
    body.regenerate = options.regenerate
  }
  
  const response = await fetch(url, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(error.error || `HTTP ${response.status}`)
  }
  
  return response.json()
}

export default {
  getChannelPosts,
  getChannelChunks,
  updateChannelSettings,
  setPostVisibility,
  updateLayout
}
