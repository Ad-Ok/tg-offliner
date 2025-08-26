import { api } from './api.js'

export const editsService = {
  /**
   * Создание новой правки поста
   * @param {number} telegramId - ID телеграм сообщения
   * @param {string} channelId - ID канала
   * @param {object} changes - Объект с изменениями
   * @returns {Promise} - Промис с результатом
   */
  async createEdit(telegramId, channelId, changes) {
    try {
      const response = await api.post('/api/edits', {
        telegram_id: telegramId,
        channel_id: channelId,
        changes: changes
      })
      return response.data
    } catch (error) {
      console.error('Error creating edit:', error)
      throw error
    }
  },

  /**
   * Получение всех правок для конкретного поста
   * @param {number} telegramId - ID телеграм сообщения
   * @param {string} channelId - ID канала
   * @returns {Promise} - Промис с массивом правок
   */
  async getEditsForPost(telegramId, channelId) {
    try {
      const response = await api.get(`/api/edits/${telegramId}/${channelId}`)
      return response.data.edits || []
    } catch (error) {
      console.error('Error fetching edits for post:', error)
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
   * Создание правки для скрытия поста
   * @param {number} telegramId - ID телеграм сообщения
   * @param {string} channelId - ID канала
   * @param {boolean} hidden - Скрыт ли пост
   * @returns {Promise} - Промис с результатом
   */
  async setPostHidden(telegramId, channelId, hidden) {
    return this.createEdit(telegramId, channelId, {
      hidden: hidden.toString()
    })
  }
}
