<template>
  <div v-if="hasActiveDownloads" class="download-status-panel">
    <h3>Активные загрузки</h3>
    <div class="downloads-list">
      <div 
        v-for="(status, channelId) in activeDownloads" 
        :key="channelId"
        class="download-item"
        :class="status.status"
      >
        <div class="download-info">
          <strong>{{ status.details.channel_name || channelId }}</strong>
          <div class="download-progress">
            <span v-if="status.status === 'downloading'">
              ⏳ Загрузка...
            </span>
            <span v-else-if="status.status === 'completed'">
              ✅ Завершено
            </span>
            <span v-else-if="status.status === 'stopped'">
              ⏸️ Остановлено пользователем
            </span>
            <span v-else-if="status.status === 'error'">
              ❌ Ошибка: {{ status.details.error }}
            </span>
            
            <!-- Детальная статистика -->
            <div v-if="status.details.posts_processed !== undefined" class="download-stats">
              <div class="stats-line">
                Постов: {{ status.details.posts_processed }}
                <span v-if="getChannelTotalPosts(channelId) || status.details.total_posts"> 
                  из {{ getChannelTotalPosts(channelId) || status.details.total_posts }}
                </span>
                <span v-if="status.details.comments_processed">, комментариев: {{ status.details.comments_processed }}</span>
              </div>
            </div>
          </div>
          <!-- Прогресс-бар для визуального отображения -->
          <div 
            v-if="shouldShowProgressBar(status, channelId)"
            class="progress-bar"
            :class="{ 'completed': status.status === 'completed' }"
          >
            <div 
              class="progress-fill"
              :style="{ width: getProgressPercentage(status, channelId) + '%' }"
              :class="status.status"
            ></div>
            <span class="progress-text">{{ getProgressPercentage(status, channelId).toFixed(1) }}%</span>
          </div>
        </div>
        <div class="download-actions">
          <button 
            v-if="status.status === 'downloading'"
            @click="$emit('stop-download', channelId)"
            class="stop-button"
          >
            Остановить
          </button>
          <button 
            v-if="['completed', 'stopped', 'error'].includes(status.status)"
            @click="$emit('clear-status', channelId)"
            class="clear-button"
          >
            ❌ Очистить
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "DownloadStatus",
  props: {
    downloadStatuses: {
      type: Object,
      default: () => ({})
    },
    channels: {
      type: Array,
      default: () => []
    },
    previewChannels: {
      type: Array,
      default: () => []
    }
  },
  computed: {
    activeDownloads() {
      // Фильтруем только активные или недавно завершенные загрузки
      const cutoffTime = Date.now() / 1000 - 300; // 5 минут назад
      const filtered = {};
      
      Object.entries(this.downloadStatuses).forEach(([channelId, status]) => {
        if (status.status === 'downloading' || 
            (status.timestamp && status.timestamp > cutoffTime)) {
          filtered[channelId] = status;
        }
      });
      
      return filtered;
    },
    hasActiveDownloads() {
      return Object.keys(this.activeDownloads).length > 0;
    }
  },
  methods: {
    getChannelTotalPosts(channelId) {
      // Ищем в загруженных каналах
      const channel = this.channels.find(ch => ch.id === channelId);
      if (channel && channel.posts_count !== undefined) {
        return channel.posts_count;
      }
      
      // Ищем в preview каналах
      const previewChannel = this.previewChannels.find(ch => ch.id === channelId);
      if (previewChannel && previewChannel.posts_count !== undefined) {
        return previewChannel.posts_count;
      }
      
      return null;
    },
    getProgressPercentage(status, channelId) {
      const { posts_processed, total_posts } = status.details || {};
      
      // Если total_posts не задан или равен 0, пытаемся получить из информации о канале
      let actualTotalPosts = total_posts;
      if (!actualTotalPosts || actualTotalPosts === 0) {
        actualTotalPosts = this.getChannelTotalPosts(channelId);
      }
      
      if (!actualTotalPosts || actualTotalPosts === 0) return 0;
      if (posts_processed === undefined) return 0;
      return Math.min((posts_processed / actualTotalPosts) * 100, 100);
    },
    shouldShowProgressBar(status, channelId) {
      const channelTotalPosts = this.getChannelTotalPosts(channelId);
      
      // Отладочная информация
      console.log('shouldShowProgressBar debug:', {
        channelId,
        status: status.status,
        details: status.details,
        total_posts: status.details?.total_posts,
        posts_processed: status.details?.posts_processed,
        channelTotalPosts,
        hasDetails: !!status.details
      });
      
      // Показываем прогресс-бар если есть информация о постах
      return status.details && 
             status.details.posts_processed !== undefined &&
             (channelTotalPosts > 0 || status.details.total_posts > 0) &&
             ['downloading', 'completed', 'stopped'].includes(status.status);
    }
  }
};
</script>

<style scoped>
.download-status-panel {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}

.download-status-panel h3 {
  margin: 0 0 12px 0;
  color: #495057;
  font-size: 16px;
}

.downloads-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.download-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid transparent;
}

.download-item.downloading {
  background: #e3f2fd;
  border-color: #2196f3;
}

.download-item.completed {
  background: #e8f5e8;
  border-color: #4caf50;
}

.download-item.stopped {
  background: #fff3cd;
  border-color: #ffc107;
}

.download-item.error {
  background: #f8d7da;
  border-color: #dc3545;
}

.download-info {
  flex: 1;
}

.download-progress {
  font-size: 13px;
  color: #6c757d;
  margin-top: 2px;
}

.download-stats {
  margin-top: 8px;
}

.stats-line {
  font-size: 14px;
  font-weight: 500;
  color: #495057;
  padding: 4px 0;
}

.download-actions {
  display: flex;
  gap: 6px;
}

.stop-button, .clear-button {
  padding: 4px 8px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  transition: background-color 0.2s;
}

.stop-button {
  background-color: #ffc107;
  color: #000;
}

.stop-button:hover {
  background-color: #e0a800;
}

.clear-button {
  background-color: #6c757d;
  color: white;
}

.clear-button:hover {
  background-color: #5a6268;
}

.progress-bar {
  position: relative;
  width: 100%;
  height: 20px;
  background-color: #e9ecef;
  border-radius: 2px;
  margin-top: 8px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #28a745, #20c997);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.progress-fill.downloading {
  background: linear-gradient(90deg, #007bff, #17a2b8);
}

.progress-fill.completed {
  background: linear-gradient(90deg, #28a745, #20c997);
}

.progress-fill.stopped {
  background: linear-gradient(90deg, #ffc107, #fd7e14);
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 11px;
  font-weight: 600;
  color: #495057;
  z-index: 1;
}
</style>
