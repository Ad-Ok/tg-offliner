import { api } from './api.js'

export const layoutsService = {
  async reloadLayout(groupedId, channelId, columns = null, noCrop = false, borderWidth = '0') {
    if (!groupedId) {
      throw new Error('groupedId is required to reload layout')
    }

    if (!channelId) {
      throw new Error('channelId is required to reload layout')
    }

    const payload = {
      channel_id: channelId,
      border_width: borderWidth
    }

    if (columns !== null) {
      payload.columns = columns
    }

    if (noCrop) {
      payload.no_crop = true
    }

    const response = await api.post(`/api/layouts/${groupedId}/reload`, payload)

    return response.data
  },

  async updateBorder(groupedId, channelId, borderWidth) {
    if (!groupedId) {
      throw new Error('groupedId is required to update border')
    }

    if (!channelId) {
      throw new Error('channelId is required to update border')
    }

    const payload = {
      channel_id: channelId,
      border_width: borderWidth
    }

    const response = await api.patch(`/api/layouts/${groupedId}/border`, payload)

    return response.data
  }
}
