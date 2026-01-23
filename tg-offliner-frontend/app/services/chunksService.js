/**
 * Сервис для работы с API chunks
 * Разбиение больших каналов на части
 */

import { apiBase } from '~/services/api'

/**
 * @typedef {Object} ChunkInfo
 * @property {number} index - Индекс chunk (0-based)
 * @property {number} posts_count - Количество постов в chunk
 * @property {number} comments_count - Количество комментариев
 * @property {number} total_weight - Общий вес (посты + комментарии + фото в группах)
 * @property {string} date_from - Дата самого нового поста
 * @property {string} date_to - Дата самого старого поста
 */

/**
 * @typedef {Object} ChannelChunksResponse
 * @property {string} channel_id - ID канала
 * @property {number} items_per_chunk - Размер chunk
 * @property {number} overflow_threshold - Порог переполнения
 * @property {number} total_chunks - Общее количество chunks
 * @property {number} total_posts - Общее количество постов
 * @property {number} total_comments - Общее количество комментариев
 * @property {number} total_weight - Общий вес
 * @property {ChunkInfo[]} chunks - Информация о каждом chunk
 */

/**
 * @typedef {Object} ChunkPostsResponse
 * @property {string} channel_id - ID канала
 * @property {number} chunk_index - Индекс chunk
 * @property {Object[]} posts - Посты в chunk
 * @property {Object[]} comments - Комментарии к постам
 */

/**
 * Получить информацию о chunks канала
 * @param {string} channelId - ID канала
 * @param {Object} options - Опции
 * @param {number} [options.itemsPerChunk] - Количество элементов на chunk
 * @param {number} [options.overflowThreshold] - Порог переполнения (0.0-1.0)
 * @param {string} [options.sortOrder] - Порядок сортировки ('desc' или 'asc')
 * @returns {Promise<ChannelChunksResponse>}
 */
export async function getChannelChunks(channelId, options = {}) {
  const params = new URLSearchParams()
  
  if (options.itemsPerChunk !== undefined) {
    params.set('items_per_chunk', options.itemsPerChunk)
  }
  
  if (options.overflowThreshold !== undefined) {
    params.set('overflow_threshold', options.overflowThreshold)
  }
  
  if (options.sortOrder !== undefined) {
    params.set('sort_order', options.sortOrder)
  }
  
  const queryString = params.toString()
  const url = `${apiBase}/api/chunks/${channelId}${queryString ? '?' + queryString : ''}`
  
  const response = await fetch(url)
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(error.error || `HTTP ${response.status}`)
  }
  
  return response.json()
}

/**
 * Получить посты и комментарии из конкретного chunk
 * @param {string} channelId - ID канала
 * @param {number} chunkIndex - Индекс chunk (0-based)
 * @param {Object} options - Опции
 * @param {number} [options.itemsPerChunk] - Количество элементов на chunk
 * @param {number} [options.overflowThreshold] - Порог переполнения
 * @param {string} [options.sortOrder] - Порядок сортировки ('desc' или 'asc')
 * @returns {Promise<ChunkPostsResponse>}
 */
export async function getChunkPosts(channelId, chunkIndex, options = {}) {
  const params = new URLSearchParams()
  
  if (options.itemsPerChunk !== undefined) {
    params.set('items_per_chunk', options.itemsPerChunk)
  }
  
  if (options.overflowThreshold !== undefined) {
    params.set('overflow_threshold', options.overflowThreshold)
  }
  
  if (options.sortOrder !== undefined) {
    params.set('sort_order', options.sortOrder)
  }
  
  const queryString = params.toString()
  const url = `${apiBase}/api/chunks/${channelId}/${chunkIndex}/posts${queryString ? '?' + queryString : ''}`
  
  const response = await fetch(url)
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(error.error || `HTTP ${response.status}`)
  }
  
  return response.json()
}

/**
 * Получить все посты и комментарии для нескольких chunks
 * @param {string} channelId - ID канала
 * @param {number[]} chunkIndexes - Индексы chunks
 * @param {Object} options - Опции
 * @returns {Promise<{posts: Object[], comments: Object[]}>}
 */
export async function getMultipleChunksPosts(channelId, chunkIndexes, options = {}) {
  const results = await Promise.all(
    chunkIndexes.map(index => getChunkPosts(channelId, index, options))
  )
  
  const allPosts = []
  const allComments = []
  
  for (const result of results) {
    allPosts.push(...result.posts)
    allComments.push(...result.comments)
  }
  
  return {
    posts: allPosts,
    comments: allComments
  }
}

/**
 * Итератор для загрузки всех chunks канала
 * @param {string} channelId - ID канала
 * @param {Object} options - Опции
 * @yields {ChunkPostsResponse}
 */
export async function* iterateChunks(channelId, options = {}) {
  const chunksInfo = await getChannelChunks(channelId, options)
  
  for (const chunk of chunksInfo.chunks) {
    const posts = await getChunkPosts(channelId, chunk.index, options)
    yield posts
  }
}

/**
 * Форматирование диапазона дат для chunk
 * @param {ChunkInfo} chunk - Информация о chunk
 * @returns {string}
 */
export function formatChunkDateRange(chunk) {
  const from = chunk.date_from
  const to = chunk.date_to
  
  if (from === to) {
    return from
  }
  
  return `${from} — ${to}`
}

/**
 * Форматирование описания chunk
 * @param {ChunkInfo} chunk - Информация о chunk
 * @returns {string}
 */
export function formatChunkDescription(chunk) {
  const posts = chunk.posts_count === 1 
    ? '1 пост' 
    : `${chunk.posts_count} постов`
  
  if (chunk.comments_count === 0) {
    return posts
  }
  
  const comments = chunk.comments_count === 1 
    ? '1 комментарий' 
    : `${chunk.comments_count} комментариев`
  
  return `${posts}, ${comments}`
}

export default {
  getChannelChunks,
  getChunkPosts,
  getMultipleChunksPosts,
  iterateChunks,
  formatChunkDateRange,
  formatChunkDescription
}
