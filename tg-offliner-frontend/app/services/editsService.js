import { api } from './api.js'

export const editsService = {
  /**
   * Создание новой правки поста или обновление существующей
   * @param {number} telegramId - ID телеграм сообщения
   * @param {string} channelId - ID канала
   * @param {object} changes - Объект с изменениями
   * @returns {Promise} - Промис с результатом
   */
  async createOrUpdateEdit(telegramId, channelId, changes) {
    try {
      const response = await api.post('/api/edits', {
        telegram_id: telegramId,
        channel_id: channelId,
        changes: changes
      })
      return response.data
    } catch (error) {
      console.error('Error creating/updating edit:', error)
      throw error
    }
  },

  /**
   * Получение правки для конкретного поста
   * @param {number} telegramId - ID телеграм сообщения
   * @param {string} channelId - ID канала
   * @returns {Promise} - Промис с правкой или null
   */
  async getEditForPost(telegramId, channelId) {
    try {
      const response = await api.get(`/api/edits/${telegramId}/${channelId}`)
      return response.data.edit || null
    } catch (error) {
      console.error('Error fetching edit for post:', error)
      throw error
    }
  },

  /**
   * Получение всех правок для канала
   * @param {string} channelId - ID канала
   * @returns {Promise} - Промис с массивом правок
   */
  async getEditsForChannel(channelId) {
    try {
      const response = await api.get(`/api/edits/${channelId}`)
      return response.data.edits || []
    } catch (error) {
      console.error('Error fetching edits for channel:', error)
      throw error
    }
  },

  /**
   * Создание/обновление правки для скрытия поста
   * @param {number} telegramId - ID телеграм сообщения
   * @param {string} channelId - ID канала
   * @param {boolean} hidden - Скрыт ли пост
   * @returns {Promise} - Промис с результатом
   */
  async setPostHidden(telegramId, channelId, hidden) {
    return this.createOrUpdateEdit(telegramId, channelId, {
      hidden: hidden.toString()
    })
  },

  /**
   * Получение состояния скрытости поста
   * @param {number} telegramId - ID телеграм сообщения
   * @param {string} channelId - ID канала
   * @returns {Promise<boolean>} - Промис с состоянием скрытости
   */
  async getPostHiddenState(telegramId, channelId) {
    try {
      const edit = await this.getEditForPost(telegramId, channelId)
      if (edit && edit.changes && edit.changes.hidden) {
        return edit.changes.hidden === 'true'
      }
      return false
    } catch (error) {
      console.error('Error getting post hidden state:', error)
      return false
    }
  }
}
