<template>
  <div class="channels-list">
    <h1>Список каналов</h1>
    
    <!-- Панель статуса загрузок -->
    <DownloadStatus 
      :downloadStatuses="downloadStatuses"
      @stop-download="stopDownload"
      @clear-status="clearStatus"
    />
    
    <div v-if="channelsLoading" class="loading">Загрузка списка каналов...</div>
    
    <!-- Загруженные каналы -->
    <div v-if="!channelsLoading && channels.length > 0">
      <h2>Загруженные каналы</h2>
      <ul>
        <li v-for="channel in channels" :key="channel.id" class="channel-item">
          <div class="channel-main">
            <div class="channel-avatar-wrapper">
              <img
                v-if="channel.avatar"
                :src="channelAvatarSrc(channel)"
                :alt="channel.name"
                class="channel-avatar"
              />
            </div>
            <router-link :to="`/${channel.id}/posts`">{{ channel.name }}</router-link>
            <div class="channel-info">
              <span v-if="channel.creation_date">Создан {{ channel.creation_date }}</span>
              <span v-if="channel.subscribers">&nbsp;•&nbsp;{{ channel.subscribers }} подписчиков</span>
              <span v-if="channel.discussion_group_id">&nbsp;•&nbsp;Есть группа обсуждений</span>
              <!-- Индикатор статуса загрузки -->
              <span v-if="isDownloading(channel.id)" class="download-status downloading">
                &nbsp;•&nbsp;⏳ Загружается...
                <span v-if="getDownloadProgress(channel.id)">
                  ({{ getDownloadProgress(channel.id) }})
                </span>
              </span>
              <span v-else-if="getDownloadStatus(channel.id) === 'stopped'" class="download-status stopped">
                &nbsp;•&nbsp;⏸️ Остановлено
              </span>
              <span v-else-if="getDownloadStatus(channel.id) === 'error'" class="download-status error">
                &nbsp;•&nbsp;❌ Ошибка
              </span>
            </div>
            <div class="channel-actions">
              <!-- Кнопка остановки загрузки (показываем только во время загрузки) -->
              <button 
                v-if="isDownloading(channel.id)" 
                @click="stopDownload(channel.id)" 
                class="stop-button"
                title="Остановить загрузку"
              >
                ⏹️ Остановить
              </button>
              <button @click="printPdf(channel.id)" class="print-button">Печать PDF</button>
              <button @click="exportHtml(channel.id)" class="export-button">Создать HTML</button>
              <button @click="removeChannel(channel.id)" class="delete-button">Удалить канал</button>
            </div>
          </div>
          <div class="channel-description" v-if="channel.description">
            {{ channel.description }}
          </div>
        </li>
      </ul>
    </div>

    <!-- Preview каналы -->
    <div v-if="previewChannels.length > 0">
      <h2>Предварительный просмотр</h2>
      <ul>
        <li v-for="(preview, index) in previewChannels" :key="`preview-${preview.id}`" class="channel-item preview-item">
          <div class="channel-main">
            <img
              v-if="preview.avatar"
              :src="channelAvatarSrc(preview)"
              alt="Аватар"
              class="channel-avatar"
            />
            <span class="channel-name">{{ preview.name }}</span>
            <div class="channel-info">
              <span v-if="preview.creation_date">Создан {{ preview.creation_date }}</span>
              <span v-if="preview.subscribers">&nbsp;•&nbsp;{{ preview.subscribers }} подписчиков</span>
              <span v-if="preview.posts_count !== undefined">&nbsp;•&nbsp;{{ preview.posts_count }} постов</span>
              <span v-if="preview.discussion_group_id">&nbsp;•&nbsp;Есть группа обсуждений</span>
            </div>
            <button @click="loadChannel(preview, index)" class="load-button">Загрузить канал</button>
            <button @click="removePreview(index)" class="cancel-button">Отменить</button>
          </div>
          <div class="channel-description" v-if="preview.description">
            {{ preview.description }}
          </div>
        </li>
      </ul>
    </div>

    <!-- Форма добавления канала -->
    <div class="add-channel">
      <input
        v-model="newChannel"
        type="text"
        placeholder="Введите имя канала или ID пользователя"
        @keyup.enter="previewChannel"
        :disabled="previewLoading"
      />
      <button @click="previewChannel" :disabled="previewLoading">
        {{ previewLoading ? 'Загрузка...' : 'Предварительный просмотр' }}
      </button>
      <div class="input-hint">
        Поддерживается: @channelname, channelname, @username, username, или числовой ID (123456789)
      </div>
      <div v-if="previewLoading" class="preview-loading">Получаем информацию о канале...</div>
    </div>
  </div>
</template>

<script>
import { eventBus } from "~/eventBus";
import { api, apiBase, mediaBase } from '~/services/api'; // добавь mediaBase
import DownloadStatus from './DownloadStatus.vue';

export default {
  name: "ChannelsList",
  components: {
    DownloadStatus,
  },
  data() {
    return {
      channels: [],
      previewChannels: [], // Отдельный массив для preview-каналов
      channelsLoading: true, // Загрузка списка каналов
      previewLoading: false, // Загрузка preview канала
      newChannel: "", // Поле для ввода имени канала
      logs: "", // Логи сервера
      logsLoading: false, // Флаг загрузки логов
      logsInterval: null, // Интервал для обновления логов
      logsOffset: 0, // Offset для логов
      downloadStatuses: {}, // Статусы загрузки каналов
      statusCheckInterval: null, // Интервал проверки статусов
      loadingChannels: new Set(), // Set для отслеживания загружающихся каналов
    };
  },
  computed: {
    // Возвращает объект: id -> src для аватара
    channelAvatarSrc() {
      return (channel) =>
        channel.avatar
          ? `${mediaBase}/downloads/${channel.avatar}`
          : null;
    },
  },
  created() {
    this.fetchChannels();
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
          console.error('Ошибка при загрузке каналов:', error);
          this.channelsLoading = false;
        });
    },
    addChannel() {
      if (!this.newChannel.trim()) {
        eventBus.showAlert("Введите имя канала!", "warning");
        return;
      }

      // Удаляем символ @ в начале строки, если он есть
      const sanitizedChannel = this.newChannel.trim().replace(/^@/, "");

      // Показываем сообщение о начале отправки запроса
      eventBus.showAlert(`Отправка запроса с данными: ${sanitizedChannel}`, "info");

      api
        .post('/api/add_channel', {
          channel_username: sanitizedChannel,
        })
        .then((response) => {
          eventBus.showAlert(response.data.message, "success");
          this.newChannel = ""; // Очищаем поле ввода
          this.fetchChannels(); // Обновляем список каналов
        })
        .catch((error) => {
          if (error.response && error.response.status === 400) {
            eventBus.showAlert(error.response.data.error, "warning");
          } else {
            eventBus.showAlert("Ошибка при добавлении канала", "danger");
          }
        });
    },
    async printPdf(channelId) {
      try {
        const res = await fetch(`${apiBase}/api/channels/${channelId}/print`);
        const contentType = res.headers.get('content-type');
        if (!contentType || !contentType.includes('pdf')) {
          eventBus.showAlert("Сервер не вернул PDF-файл. Проверьте логи сервера.", "danger");
          return;
        }
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `${channelId}.pdf`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
      } catch (error) {
        eventBus.showAlert(error.message || "Ошибка при печати PDF", "danger");
        console.error("Ошибка при скачивании PDF:", error);
      }
    },
    async exportHtml(channelId) {
      try {
        this.loadingChannels.add(channelId);
        
        const res = await fetch(`${apiBase}/api/channels/${channelId}/export-html`);
        
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        
        eventBus.showAlert(`HTML файл для канала ${channelId} успешно создан в папке downloads/${channelId}/index.html`, "success");
        
      } catch (error) {
        eventBus.showAlert(error.message || "Ошибка при создании HTML", "danger");
        console.error("Ошибка при экспорте HTML:", error);
      } finally {
        this.loadingChannels.delete(channelId);
      }
    },
    removeChannel(channelId) {
      if (!confirm("Вы уверены, что хотите удалить этот канал?")) return;

      this.deleteChannel(channelId);
    },
    deleteChannel(channelId) {
      api
        .delete(`/api/channels/${channelId}`)
        .then((response) => {
          // Если запрос успешен, выводим сообщение об успехе
          if (response.data.message) {
            eventBus.showAlert(response.data.message, "success");
          }
          this.fetchChannels(); // Обновляем список каналов
        })
        .catch((error) => {
          // Если произошла ошибка, выводим сообщение об ошибке
          if (error.response && error.response.data.error) {
            eventBus.showAlert(error.response.data.error, "danger");
          } else {
            eventBus.showAlert("Неизвестная ошибка при удалении канала", "danger");
          }
        });
    },
    previewChannel() {
      if (!this.newChannel.trim()) {
        eventBus.showAlert("Введите имя канала!", "warning");
        return;
      }
      const sanitizedChannel = this.newChannel.trim().replace(/^@/, "");
      this.previewLoading = true;
      api.get(`/api/channel_preview?username=${encodeURIComponent(sanitizedChannel)}`)
        .then(response => {
          const preview = response.data;
          // Сохраняем оригинальный ввод пользователя для последующего использования
          preview.originalInput = sanitizedChannel;
          
          // Проверяем, не добавлен ли уже этот канал
          const existsInChannels = this.channels.some(ch => ch.id === preview.id);
          const existsInPreview = this.previewChannels.some(ch => ch.id === preview.id);
          
          if (existsInChannels) {
            eventBus.showAlert("Этот канал уже загружен!", "warning");
          } else if (existsInPreview) {
            eventBus.showAlert("Предварительный просмотр этого канала уже добавлен!", "warning");
          } else {
            this.previewChannels.push(preview); // Добавляем в preview-каналы
            eventBus.showAlert("Предварительный просмотр готов. Нажмите 'Загрузить канал' для добавления.", "info");
          }
          this.previewLoading = false;
          this.newChannel = "";
        })
        .catch(error => {
          eventBus.showAlert("Ошибка: " + (error.response?.data?.error || error.message), "danger");
          this.previewLoading = false;
        });
    },
    loadChannel(preview, index) {
      // Используем оригинальный ввод пользователя, а не трансформированный username
      const channelInput = preview.originalInput;

      // Показываем сообщение о начале загрузки
      eventBus.showAlert(`Загружаем канал ${preview.name}...`, "info");

      api
        .post('/api/add_channel', {
          channel_username: channelInput,
        })
        .then((response) => {
          eventBus.showAlert(response.data.message, "success");
          // Удаляем из preview после успешной загрузки
          this.previewChannels.splice(index, 1);
          this.fetchChannels(); // Обновляем список каналов
        })
        .catch((error) => {
          if (error.response && error.response.status === 400) {
            eventBus.showAlert(error.response.data.error, "warning");
          } else {
            eventBus.showAlert("Ошибка при добавлении канала", "danger");
          }
        });
    },
    removePreview(index) {
      this.previewChannels.splice(index, 1);
      eventBus.showAlert("Предварительный просмотр отменен", "info");
    },
    
    // Методы для управления загрузкой
    async checkDownloadStatuses() {
      try {
        const response = await api.get('/api/download/status');
        this.downloadStatuses = response.data;
      } catch (error) {
        console.error('Ошибка получения статусов загрузки:', error);
      }
    },
    
    async stopDownload(channelId) {
      try {
        const response = await api.post(`/api/download/stop/${channelId}`);
        eventBus.showAlert(response.data.message, "success");
        this.checkDownloadStatuses(); // Обновляем статусы
      } catch (error) {
        const errorMessage = error.response?.data?.error || 'Ошибка остановки загрузки';
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
          progress = `${posts_processed} из ${total_posts} постов`;
        } else {
          progress = `${posts_processed} постов`;
        }
        
        if (comments_processed) {
          progress += `, ${comments_processed} комментариев`;
        }
      }
      
      return progress;
    },
    
    startStatusPolling() {
      this.statusCheckInterval = setInterval(() => {
        this.checkDownloadStatuses();
      }, 2000); // Проверяем каждые 2 секунды
    },
    
    stopStatusPolling() {
      if (this.statusCheckInterval) {
        clearInterval(this.statusCheckInterval);
        this.statusCheckInterval = null;
      }
    },
    
    clearStatus(channel) {
      // Удаляем статус для канала из локального состояния
      delete this.downloadStatuses[channel];
      this.$forceUpdate(); // Принудительно обновляем компонент
    }
  },
  
  mounted() {
    this.checkDownloadStatuses(); // Проверяем статусы при загрузке
    this.startStatusPolling(); // Запускаем опрос статусов
  },
  
  beforeUnmount() {
    this.stopStatusPolling(); // Останавливаем опрос при выходе
  },
};
</script>
