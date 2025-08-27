import { api } from './api.js'

export const editsService = {
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

  async getEditForPost(telegramId, channelId) {
    try {
      const response = await api.get(`/api/edits/${telegramId}/${channelId}`)
      return response.data.edit || null
    } catch (error) {
      console.error('Error fetching edit for post:', error)
      throw error
    }
  },

  async getEditsForChannel(channelId) {
    try {
      const response = await api.get(`/api/edits/${channelId}`)
      return response.data.edits || []
    } catch (error) {
      console.error('Error fetching edits for channel:', error)
      throw error
    }
  },

  async setPostHidden(telegramId, channelId, hidden) {
    return this.createOrUpdateEdit(telegramId, channelId, {
      hidden: hidden.toString()
    })
  },

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
