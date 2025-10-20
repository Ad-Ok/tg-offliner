import { api } from './api.js'

export const layoutsService = {
  async reloadLayout(groupedId, channelId, columns = null, noCrop = false) {
    if (!groupedId) {
      throw new Error('groupedId is required to reload layout')
    }

    if (!channelId) {
      throw new Error('channelId is required to reload layout')
    }

    const payload = {
      channel_id: channelId
    }

    if (columns !== null) {
      payload.columns = columns
    }

    if (noCrop) {
      payload.no_crop = true
    }

    const response = await api.post(`/api/layouts/${groupedId}/reload`, payload)

    return response.data
  }
}
