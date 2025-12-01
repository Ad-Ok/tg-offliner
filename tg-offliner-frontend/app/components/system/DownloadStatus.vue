<template>
  <div v-if="hasActiveDownloads">
    <h2 class="text-2xl mb-2">Active Downloads</h2>
    <div class="list bg-base-100 rounded-box shadow-md mb-8">
      <div 
        v-for="(status, channelId) in activeDownloads" 
        :key="channelId"
        class="list-row"
      >
        <div class="avatar">
          <div class="w-16 h-16 rounded-xl bg-base-300 flex justify-center items-center">
            <div class="flex w-full h-full items-center justify-center">
              <div class="loading loading-spinner loading-lg text-primary"></div>
            </div>
          </div>
        </div>

        <div class="flex-1 min-w-0">
          <div class="font-bold text-lg">{{ status.details.channel_name || channelId }}</div>
          <div class="mt-2">
            <span class="text-sm">⏳ Downloading...</span>
            
            <!-- Detailed statistics -->
            <div v-if="status.details.posts_processed !== undefined" class="mt-2 text-sm text-base-content/70">
              <div>
                Posts: {{ status.details.posts_processed }}
                <span v-if="getChannelTotalPosts(channelId) || status.details.total_posts"> 
                  of {{ getChannelTotalPosts(channelId) || status.details.total_posts }}
                </span>
                <span v-if="status.details.comments_processed">, comments: {{ status.details.comments_processed }}</span>
              </div>
            </div>
          </div>

          <!-- Progress bar for visual display -->
          <div v-if="status.details && status.details.posts_processed !== undefined" class="w-full mt-3">
            <progress 
              class="progress progress-primary w-full h-4"
              :value="getProgressPercentage(status, channelId)"
              max="100"
            ></progress>
            <div class="text-xs text-base-content/60 mt-1 text-center">
              {{ getProgressPercentage(status, channelId).toFixed(1) }}%
            </div>
          </div>
        </div>
        
        <div class="flex gap-2 flex-shrink-0">
          <button 
            @click="$emit('stop-download', channelId)"
            class="btn btn-sm btn-outline btn-warning"
          >
            Stop
          </button>
          <button 
            @click="$emit('cancel-download', channelId)"
            class="btn btn-sm btn-outline btn-error"
          >
            Cancel
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
      // Фильтруем только активные загрузки
      const filtered = {};
      
      Object.entries(this.downloadStatuses).forEach(([channelId, status]) => {
        if (status.status === 'downloading') {
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
      // Search in downloaded channels
      const channel = this.channels.find(ch => ch.id === channelId);
      if (channel && channel.posts_count !== undefined) {
        return channel.posts_count;
      }
      
      // Search in preview channels
      const previewChannel = this.previewChannels.find(ch => ch.id === channelId);
      if (previewChannel && previewChannel.posts_count !== undefined) {
        return previewChannel.posts_count;
      }
      
      return null;
    },
    getProgressPercentage(status, channelId) {
      const { posts_processed, total_posts } = status.details || {};
      
      // If total_posts is not set or is 0, try to get it from channel info
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
      
      // Show progress bar if there's info about posts
      return status.details && 
             status.details.posts_processed !== undefined &&
             (channelTotalPosts > 0 || status.details.total_posts > 0);
    }
  }
};
</script>
