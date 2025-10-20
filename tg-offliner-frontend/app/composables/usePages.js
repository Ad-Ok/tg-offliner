/**
 * Композабл для работы с API страниц
 */
import { api } from '~/services/api'

export const usePages = () => {
  /**
   * Создает новую страницу для канала
   * @param {string} channelId - ID канала
   * @returns {Promise<Object>} - Созданная страница
   */
  const createPage = async (channelId) => {
    try {
      const response = await api.post('/api/pages', {
        channel_id: channelId,
        json_data: {
          version: 1,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          grid: {
            cellHeight: 100,
            columns: 12,
            rowHeight: 100
          },
          blocks: []
        }
      })
      return response.data
    } catch (error) {
      console.error('Error creating page:', error)
      throw error
    }
  }

  /**
   * Загружает страницу по ID
   * @param {number} pageId - ID страницы
   * @returns {Promise<Object>} - Данные страницы
   */
  const loadPage = async (pageId) => {
    try {
      const response = await api.get(`/api/pages/${pageId}`)
      return response.data
    } catch (error) {
      console.error('Error loading page:', error)
      throw error
    }
  }

  /**
   * Загружает все страницы канала
   * @param {string} channelId - ID канала
   * @returns {Promise<Array>} - Массив страниц
   */
  const loadChannelPages = async (channelId) => {
    try {
      const response = await api.get(`/api/pages?channel_id=${channelId}`)
      return response.data
    } catch (error) {
      console.error('Error loading channel pages:', error)
      throw error
    }
  }

  /**
   * Сохраняет layout страницы (позиции блоков)
   * @param {number} pageId - ID страницы
   * @param {Array} blocks - Массив блоков с координатами
   * @param {Object} existingData - Существующие данные страницы
   * @returns {Promise<Object>} - Обновленная страница
   */
  const saveLayout = async (pageId, blocks, existingData = {}) => {
    try {
      const json_data = {
        ...existingData,
        updated_at: new Date().toISOString(),
        blocks: blocks.map(block => ({
          id: block.i || block.id || `block-${Date.now()}-${Math.random()}`,
          x: block.x,
          y: block.y,
          w: block.w,
          h: block.h,
          content: block.content || {}
        }))
      }

      const response = await api.put(`/api/pages/${pageId}`, {
        json_data
      })
      return response.data
    } catch (error) {
      console.error('Error saving layout:', error)
      throw error
    }
  }

  /**
   * Удаляет страницу
   * @param {number} pageId - ID страницы
   * @returns {Promise<Object>} - Результат удаления
   */
  const deletePage = async (pageId) => {
    try {
      const response = await api.delete(`/api/pages/${pageId}`)
      return response.data
    } catch (error) {
      console.error('Error deleting page:', error)
      throw error
    }
  }

  /**
   * Преобразует блоки из формата базы данных в формат Vue Grid Layout
   * @param {Array} blocks - Блоки из базы данных
   * @returns {Array} - Массив блоков для Vue Grid Layout
   */
  const blocksToLayout = (blocks) => {
    return blocks.map(block => ({
      i: block.id,
      x: block.x,
      y: block.y,
      w: block.w,
      h: block.h,
      content: block.content || {}
    }))
  }

  /**
   * Преобразует layout из Vue Grid Layout в формат для сохранения в базу
   * @param {Array} layout - Layout из Vue Grid Layout
   * @param {Array} originalBlocks - Оригинальные блоки с content
   * @returns {Array} - Массив блоков для сохранения
   */
  const layoutToBlocks = (layout, originalBlocks = []) => {
    return layout.map(item => {
      const originalBlock = originalBlocks.find(b => b.id === item.i || b.i === item.i)
      return {
        id: item.i,
        x: item.x,
        y: item.y,
        w: item.w,
        h: item.h,
        content: originalBlock?.content || {}
      }
    })
  }

  return {
    createPage,
    loadPage,
    loadChannelPages,
    saveLayout,
    deletePage,
    blocksToLayout,
    layoutToBlocks
  }
}
