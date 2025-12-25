<template>
  <div class="channels-list max-w-6xl mx-auto">
    
    <!-- Download status panel -->
    <DownloadStatus 
      :downloadStatuses="downloadStatuses"
      :channels="channels"
      :previewChannels="previewChannels"
      @stop-download="stopDownload"
      @cancel-download="cancelDownload"
      @clear-status="clearStatus"
    />

    <div v-if="channelsLoading" class="flex justify-center py-20">
      <div class="loading loading-xl text-primary mr-4"></div>
      <div class="text-xl">Loading channels list...</div>
    </div>
    
    <!-- Downloaded Channels -->
    <div v-if="!channelsLoading && channels.length > 0">
      <h2 class="text-2xl mb-2">Downloaded Channels</h2>

      <ul class="list bg-base-100 rounded-box shadow-md mb-8">
        <li v-for="channel in channels" :key="channel.id" class="list-row">
          <div class="avatar">
            <div class="w-16 h-16 rounded-xl bg-base-300">
              <img
                v-if="channel.avatar"
                :src="channelAvatarSrc(channel)"
                :alt="channel.name"
              />
            </div>
          </div>

          <div>
            <router-link :to="`/${channel.id}/posts`" class="text-md font-bold text-primary">{{ channel.name }}</router-link>
            <div>
              <span v-if="channel.creation_date">Created {{ channel.creation_date }}</span>
              <span v-if="channel.subscribers">&nbsp;•&nbsp;{{ channel.subscribers }} subscribers</span>
              <span v-if="channel.posts_count !== undefined">
                &nbsp;•&nbsp;{{ channel.posts_count }} posts
                <span v-if="channel.comments_count">&nbsp;+ {{ channel.comments_count }} comments</span>
              </span>
              <span v-if="channel.discussion_group_id && !channel.comments_count">&nbsp;•&nbsp;Has discussion group</span>
            </div>
            <div class="list-col-wrap text-xs mt-2" v-if="channel.description">
              {{ channel.description }}
            </div>
          </div>


          <div class="text-xs uppercase font-semibold opacity-60">
            <!-- Download status indicator -->
            <span v-if="isDownloading(channel.id)" class="download-status downloading">
              &nbsp;•&nbsp;⏳ Downloading...
              <span v-if="getDownloadProgress(channel.id)">
                ({{ getDownloadProgress(channel.id) }})
              </span>
            </span>
            <span v-else-if="getDownloadStatus(channel.id) === 'stopped'" class="download-status stopped">
              &nbsp;•&nbsp;⏸️ Stopped
            </span>
            <span v-else-if="getDownloadStatus(channel.id) === 'error'" class="download-status error">
              &nbsp;•&nbsp;❌ Error
            </span>
          </div>

          <div class="flex gap-2">
            <ChannelExports :channelId="channel.id" />
            <button @click="removeChannel(channel.id)" class="btn btn-xs btn-outline btn-error">Delete download</button>
          </div>
        </li>
      </ul>
    </div>

    <!-- Preview channels -->
    <div v-if="previewChannels.length > 0">
      <h2 class="text-2xl mb-2">Preview</h2>
      <ul class="list bg-base-100 rounded-box shadow-md mb-8">
        <li v-for="(preview, index) in previewChannels" :key="`preview-${preview.id}`" class="list-row">

          <div class="avatar">
            <div class="w-16 h-16 rounded-xl bg-base-300">
              <img
                v-if="preview.avatar"
                :src="channelAvatarSrc(preview)"
                alt="Avatar"
              />
            </div>
          </div>

          <div>
            <span class="text-md font-bold">{{ preview.name }}</span>
            <div>
              <span v-if="preview.creation_date">Created {{ preview.creation_date }}</span>
              <span v-if="preview.subscribers">&nbsp;•&nbsp;{{ preview.subscribers }} subscribers</span>
              <span v-if="preview.posts_count !== undefined">
                &nbsp;•&nbsp;{{ preview.posts_count }} posts
                <span v-if="preview.comments_count">&nbsp;+ {{ preview.comments_count }} comments</span>
              </span>
              <span v-if="preview.discussion_group_id && !preview.comments_count">&nbsp;•&nbsp;Has discussion group</span>
            </div>
            <div class="list-col-wrap text-xs mt-2" v-if="preview.description">
              {{ preview.description }}
            </div>
          </div>

            <!-- Export settings -->
            <div class="p-3 bg-base-200 rounded-lg list-col-wrap list-col-grow col-span-full">
              <div class="text-sm font-medium mb-2">Download:</div>
              <div class="flex items-end">
                <div>

                  <div class="flex gap-2 text-sm mb-3">
                    <label class="flex items-center gap-2 cursor-pointer">
                      <input 
                        type="checkbox" 
                        v-model="exportSettings.include_system_messages"
                        class="checkbox checkbox-sm"
                      />
                      <span>System messages</span>
                    </label>
                    <label class="flex items-center gap-2 cursor-pointer">
                      <input 
                        type="checkbox" 
                        v-model="exportSettings.include_reposts"
                        class="checkbox checkbox-sm"
                      />
                      <span>Reposts</span>
                    </label>
                    <label class="flex items-center gap-2 cursor-pointer">
                      <input 
                        type="checkbox" 
                        v-model="exportSettings.include_polls"
                        class="checkbox checkbox-sm"
                      />
                      <span>Polls</span>
                    </label>
                    <label class="flex items-center gap-2 cursor-pointer" v-if="preview.discussion_group_id">
                      <input 
                        type="checkbox" 
                        v-model="exportSettings.include_discussion_comments"
                        class="checkbox checkbox-sm"
                      />
                      <span>Comments</span>
                    </label>
                  </div>
                  <div class="flex items-center gap-2 text-sm">
                    <span>Message limit:</span>
                    <input 
                      type="number" 
                      v-model.number="exportSettings.message_limit"
                      placeholder="No limit"
                      class="input input-sm input-bordered w-24"
                      min="1"
                    />
                    <span class="text-xs opacity-70">(empty = all messages)</span>
                  </div>
                </div>

                <div class="flex gap-4 ml-auto">
                  <button @click="removePreview(index)" class="btn btn-soft btn-error">Cancel</button>
                  <button @click="loadChannel(preview, index)" class="btn btn-primary">Download channel</button>
                </div>
              </div>

            </div>
        </li>
      </ul>
    </div>

    <!-- Add channel form -->
    <h2 class="text-2xl mb-2">Add Channel</h2>
    <div class="rounded-box shadow-md bg-base-100 p-4 mb-8">
      <div class="flex items-baseline mb-2">
        <div class="join">
          <input
            v-model="newChannel"
            type="text"
            placeholder="Enter channel name or user ID"
            @keyup.enter="previewChannel"
            :disabled="previewLoading"
            class="input join-item w-80"
          />
          <button 
            @click="previewChannel" 
            :disabled="previewLoading"
            class="btn btn-primary join-item"
            :class="{'btn-disabled': previewLoading}"
          >
            {{ previewLoading ? 'Loading...' : 'Preview' }}
          </button>
        </div>
        <div v-if="previewLoading" class="ml-4 text-primary">
          <div class="loading loading-bars loading-sm mr-2"></div>
          Fetching channel info...
        </div>
      </div>
      <div class="text-xs text-info-content">
        Supported: @channelname, channelname, @username, username, PEER ID
      </div>
    </div>

    <!-- Edits (change history) -->
    <div v-if="!channelsLoading && transients.length > 0" class="mt-12">
      <h2 class="text-2xl mb-2">Edits (Change History)</h2>
      <p class="text-sm text-gray-600 mb-4">
        Edits are records of post changes (text editing, reactions, hiding). 
        They are saved in the database even after channel deletion and can be cleared manually.
      </p>

      <ul class="list bg-base-100 rounded-box shadow-md mb-8">
        <li v-for="transient in transients" :key="transient.channel_id" class="list-row">
          <div></div>
          <div>
            <span class="text-md font-bold">{{ transient.channel_id }}</span>
            <div class="text-sm text-gray-600">
              {{ transient.edits_count }} {{ transient.edits_count === 1 ? 'edit' : 'edits' }}
            </div>
          </div>

          <div class="flex gap-2">
            <button 
              @click="clearTransients(transient.channel_id)" 
              class="btn btn-xs btn-outline btn-warning"
            >
              Clear edits
            </button>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
import { eventBus } from "~/eventBus";
import { api, apiBase, mediaBase } from '~/services/api';
import DownloadStatus from './DownloadStatus.vue';
import ChannelExports from './ChannelExports.vue';
import { useConfirmDialog } from '~/composables/useConfirmDialog';

export default {
  name: "ChannelsList",
  components: {
    DownloadStatus,
    ChannelExports,
  },
  setup() {
    const { showConfirmDialog } = useConfirmDialog();
    return {
      showConfirmDialog
    };
  },
  data() {
    return {
      channels: [],
      previewChannels: [], // Separate array for preview channels
      transients: [], // Transients statistics (edit history)
      channelsLoading: true, // Loading channels list
      previewLoading: false, // Loading preview channel
      newChannel: "", // Channel name input field
      logs: "", // Server logs
      logsLoading: false, // Logs loading flag
      logsInterval: null, // Logs update interval
      logsOffset: 0, // Logs offset
      downloadStatuses: {}, // Channel download statuses
      statusCheckInterval: null, // Status check interval
      // Export settings
      exportSettings: {
        include_system_messages: false,
        include_reposts: true,
        include_polls: true,
        include_discussion_comments: true,
        message_limit: null, // null for unlimited, number for limit
      },
    };
  },
  computed: {
    // Returns object: id -> src for avatar
    channelAvatarSrc() {
      return (channel) =>
        channel.avatar
          ? `${mediaBase}/downloads/${channel.avatar}`
          : null;
    },
  },
  created() {
    this.fetchChannels();
    this.fetchTransients();
  },
  methods: {
    fetchChannels() {
      this.channelsLoading = true;
      api
        .get('/api/channels')
        .then((response) => {
          this.channels = response.data;
          this.channelsLoading = false;
        })
        .catch((error) => {
          console.error('Error loading channels:', error);
          this.channelsLoading = false;
        });
    },
    fetchTransients() {
      api
        .get('/api/edits')
        .then((response) => {
          const edits = response.data.edits || [];
          
          // Group edits by channel_id and count them
          const statsMap = {};
          edits.forEach(edit => {
            if (!statsMap[edit.channel_id]) {
              statsMap[edit.channel_id] = 0;
            }
            statsMap[edit.channel_id]++;
          });
          
          // Convert to array for display
          this.transients = Object.keys(statsMap).map(channel_id => ({
            channel_id: channel_id,
            edits_count: statsMap[channel_id]
          }));
        })
        .catch((error) => {
          console.error('Error loading edits:', error);
        });
    },
    async clearTransients(channelId) {
      const confirmed = await this.showConfirmDialog({
        title: 'Clear Edits',
        message: `Are you sure you want to delete all edits for channel ${channelId}? This action cannot be undone.`,
        confirmText: 'Clear',
        cancelText: 'Cancel',
        type: 'warning'
      });

      if (!confirmed) return;

      api
        .delete(`/api/edits/${channelId}`)
        .then((response) => {
          eventBus.showAlert(response.data.message, "success");
          this.fetchTransients(); // Update edits list
        })
        .catch((error) => {
          const errorMessage = error.response?.data?.error || 'Error clearing edits';
          eventBus.showAlert(errorMessage, "danger");
        });
    },
    addChannel() {
      if (!this.newChannel.trim()) {
        eventBus.showAlert("Enter channel name!", "warning");
        return;
      }

      // Remove @ symbol at the beginning if present
      const sanitizedChannel = this.newChannel.trim().replace(/^@/, "");

      // Show request start message
      eventBus.showAlert(`Sending request with data: ${sanitizedChannel}`, "info");

      api
        .post('/api/add_channel', {
          channel_username: sanitizedChannel,
        })
        .then((response) => {
          eventBus.showAlert(response.data.message, "success");
          this.newChannel = ""; // Clear input field
          this.fetchChannels(); // Update channels list
        })
        .catch((error) => {
          if (error.response && error.response.status === 400) {
            eventBus.showAlert(error.response.data.error, "warning");
          } else {
            eventBus.showAlert("Error adding channel", "danger");
          }
        });
    },
    async removeChannel(channelId) {
      const confirmed = await this.showConfirmDialog({
        title: 'Delete Channel Download',
        message: 'Are you sure you want to delete the downloaded data for this channel?',
        confirmText: 'Delete',
        cancelText: 'Cancel',
        type: 'error'
      });

      if (!confirmed) return;

      this.deleteChannel(channelId);
    },
    deleteChannel(channelId) {
      return api
        .delete(`/api/channels/${channelId}`)
        .then((response) => {
          // If request is successful, show success message
          if (response.data.message) {
            eventBus.showAlert(response.data.message, "success");
          }
          this.fetchChannels(); // Update channels list
          return response;
        })
        .catch((error) => {
          // If an error occurs, show error message
          if (error.response && error.response.data.error) {
            eventBus.showAlert(error.response.data.error, "danger");
          } else {
            eventBus.showAlert("Unknown error deleting channel", "danger");
          }
          throw error;
        });
    },
    previewChannel() {
      if (!this.newChannel.trim()) {
        eventBus.showAlert("Enter channel name!", "warning");
        return;
      }
      const sanitizedChannel = this.newChannel.trim().replace(/^@/, "");
      this.previewLoading = true;
      api.get(`/api/channel_preview?username=${encodeURIComponent(sanitizedChannel)}`)
        .then(response => {
          const preview = response.data;
          // Save original user input for later use
          preview.originalInput = sanitizedChannel;
          
          // Check if this channel is already added
          const existsInChannels = this.channels.some(ch => ch.id === preview.id);
          const existsInPreview = this.previewChannels.some(ch => ch.id === preview.id);
          
          if (existsInChannels) {
            eventBus.showAlert("This channel is already downloaded!", "warning");
          } else if (existsInPreview) {
            eventBus.showAlert("Preview for this channel already added!", "warning");
          } else {
            this.previewChannels.push(preview); // Add to preview channels
            eventBus.showAlert("Preview ready. Click 'Download channel' to add.", "info");
          }
          this.previewLoading = false;
          this.newChannel = "";
        })
        .catch(error => {
          eventBus.showAlert("Error: " + (error.response?.data?.error || error.message), "danger");
          this.previewLoading = false;
        });
    },
    loadChannel(preview, index) {
      // Use original user input, not transformed username
      const channelInput = preview.originalInput;

      // Show loading start message
      eventBus.showAlert(`Loading channel ${preview.name}...`, "info");

      api
        .post('/api/add_channel', {
          channel_username: channelInput,
          export_settings: this.exportSettings,
        })
        .then((response) => {
          eventBus.showAlert(response.data.message, "success");
          // Remove from preview after successful loading
          this.previewChannels.splice(index, 1);
          this.fetchChannels(); // Update channels list
        })
        .catch((error) => {
          if (error.response && error.response.status === 400) {
            eventBus.showAlert(error.response.data.error, "warning");
          } else {
            eventBus.showAlert("Error adding channel", "danger");
          }
        });
    },
    removePreview(index) {
      this.previewChannels.splice(index, 1);
      eventBus.showAlert("Preview canceled", "info");
    },
    
    // Methods for download management
    async checkDownloadStatuses() {
      try {
        const response = await api.get('/api/download/status');
        this.downloadStatuses = response.data;
      } catch (error) {
        console.error('Error getting download statuses:', error);
      }
    },
    
    async stopDownload(channelId) {
      try {
        const response = await api.post(`/api/download/stop/${channelId}`);
        eventBus.showAlert(response.data.message, "success");
        this.checkDownloadStatuses(); // Update statuses
      } catch (error) {
        const errorMessage = error.response?.data?.error || 'Error stopping download';
        eventBus.showAlert(errorMessage, "danger");
      }
    },
    
    async cancelDownload(channelId) {
      // Confirm action
      const confirmed = await this.showConfirmDialog({
        title: 'Cancel Download',
        message: 'Are you sure you want to cancel the download and delete the downloaded channel data? This action cannot be undone.',
        confirmText: 'Cancel download',
        cancelText: 'Continue download',
        type: 'warning'
      });

      if (!confirmed) {
        return;
      }
      
      try {
        // First stop the download
        await api.post(`/api/download/stop/${channelId}`);
        
        // Then delete channel and discussion group
        const response = await api.delete(`/api/channels/${channelId}`);
        
        eventBus.showAlert('Download canceled, channel deleted', "success");
        
        // Update channels list and statuses
        this.loadChannels();
        this.checkDownloadStatuses();
      } catch (error) {
        const errorMessage = error.response?.data?.error || 'Error canceling download';
        eventBus.showAlert(errorMessage, "danger");
      }
    },
    
    getDownloadStatus(channelId) {
      return this.downloadStatuses[channelId]?.status || 'unknown';
    },
    
    isDownloading(channelId) {
      return this.getDownloadStatus(channelId) === 'downloading';
    },
    
    getDownloadProgress(channelId) {
      const status = this.downloadStatuses[channelId];
      if (!status || !status.details) return '';
      
      const { posts_processed, total_posts, comments_processed } = status.details;
      let progress = '';
      
      if (posts_processed !== undefined) {
        if (total_posts) {
          progress = `${posts_processed} of ${total_posts} posts`;
        } else {
          progress = `${posts_processed} posts`;
        }
        
        if (comments_processed !== undefined && comments_processed > 0) {
          progress += ` • ${comments_processed} comments`;
        }
      }
      
      return progress;
    },
    
    startStatusPolling() {
      this.statusCheckInterval = setInterval(() => {
        this.checkDownloadStatuses();
      }, 2000); // Check every 2 seconds
    },
    
    stopStatusPolling() {
      if (this.statusCheckInterval) {
        clearInterval(this.statusCheckInterval);
        this.statusCheckInterval = null;
      }
    },
    
    clearStatus(channel) {
      // Remove status for channel from local state
      delete this.downloadStatuses[channel];
      this.$forceUpdate(); // Force component update
    }
  },
  
  mounted() {
    this.checkDownloadStatuses(); // Check statuses on load
    this.startStatusPolling(); // Start status polling
  },
  
  beforeUnmount() {
    this.stopStatusPolling(); // Stop polling on exit
  },
};
</script>
