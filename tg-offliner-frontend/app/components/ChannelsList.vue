<template>
  <div class="channels-list max-w-6xl mx-auto">
    <h1 class="text-4xl mb-4">Список каналов</h1>
    
    <!-- Панель статуса загрузок -->
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
      <div class="text-xl">Загрузка списка каналов...</div>
    </div>
    
    <!-- Загруженные каналы -->
    <div v-if="!channelsLoading && channels.length > 0">
      <h2 class="text-2xl mb-2">Загруженные каналы</h2>

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
              <span v-if="channel.creation_date">Создан {{ channel.creation_date }}</span>
              <span v-if="channel.subscribers">&nbsp;•&nbsp;{{ channel.subscribers }} подписчиков</span>
              <span v-if="channel.discussion_group_id">&nbsp;•&nbsp;Есть группа обсуждений</span>
            </div>
            <div class="list-col-wrap text-xs mt-2" v-if="channel.description">
              {{ channel.description }}
            </div>
          </div>


          <div class="text-xs uppercase font-semibold opacity-60">
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

          <div class="flex space-x-2">
            <button @click="printPdf(channel.id)" class="btn btn-sm btn-soft btn-primary">Создать PDF</button>
            <button @click="exportHtml(channel.id)" class="btn btn-sm btn-soft btn-info">Создать HTML</button>
            <button @click="removeChannel(channel.id)" class="btn btn-sm btn-outline btn-error">Удалить канал</button>
          </div>
        </li>
      </ul>
    </div>

    <!-- Preview каналы -->
    <div v-if="previewChannels.length > 0">
      <h2 class="text-2xl mb-2">Предварительный просмотр</h2>
      <ul class="list bg-base-100 rounded-box shadow-md mb-8">
        <li v-for="(preview, index) in previewChannels" :key="`preview-${preview.id}`" class="list-row">

          <div class="avatar">
            <div class="w-16 h-16 rounded-xl bg-base-300">
              <img
                v-if="preview.avatar"
                :src="channelAvatarSrc(preview)"
                alt="Аватар"
              />
            </div>
          </div>

          <div>
            <span class="text-md font-bold">{{ preview.name }}</span>
            <div>
              <span v-if="preview.creation_date">Создан {{ preview.creation_date }}</span>
              <span v-if="preview.subscribers">&nbsp;•&nbsp;{{ preview.subscribers }} подписчиков</span>
              <span v-if="preview.posts_count !== undefined">&nbsp;•&nbsp;{{ preview.posts_count }} постов</span>
              <span v-if="preview.discussion_group_id">&nbsp;•&nbsp;Есть группа обсуждений</span>
            </div>
            <div class="list-col-wrap text-xs mt-2" v-if="preview.description">
              {{ preview.description }}
            </div>
          </div>

            <!-- Настройки экспорта -->
            <div class="p-3 bg-base-200 rounded-lg list-col-wrap list-col-grow col-span-full">
              <div class="text-sm font-medium mb-2">Загрузить:</div>
              <div class="flex items-end">
                <div>

                  <div class="flex space-x-2 text-sm mb-3">
                    <label class="flex items-center space-x-2 cursor-pointer">
                      <input 
                        type="checkbox" 
                        v-model="exportSettings.include_system_messages"
                        class="checkbox checkbox-sm"
                      />
                      <span>Системные сообщения</span>
                    </label>
                    <label class="flex items-center space-x-2 cursor-pointer">
                      <input 
                        type="checkbox" 
                        v-model="exportSettings.include_reposts"
                        class="checkbox checkbox-sm"
                      />
                      <span>Репосты</span>
                    </label>
                    <label class="flex items-center space-x-2 cursor-pointer">
                      <input 
                        type="checkbox" 
                        v-model="exportSettings.include_polls"
                        class="checkbox checkbox-sm"
                      />
                      <span>Опросы</span>
                    </label>
                    <label class="flex items-center space-x-2 cursor-pointer" v-if="preview.discussion_group_id">
                      <input 
                        type="checkbox" 
                        v-model="exportSettings.include_discussion_comments"
                        class="checkbox checkbox-sm"
                      />
                      <span>Комментарии</span>
                    </label>
                  </div>
                  <div class="flex items-center space-x-2 text-sm">
                    <span>Лимит сообщений:</span>
                    <input 
                      type="number" 
                      v-model.number="exportSettings.message_limit"
                      placeholder="Без лимита"
                      class="input input-sm input-bordered w-24"
                      min="1"
                    />
                    <span class="text-xs opacity-70">(пусто = все сообщения)</span>
                  </div>
                </div>

                <div class="flex space-x-4 ml-auto">
                  <button @click="removePreview(index)" class="btn btn-soft btn-error">Отменить</button>
                  <button @click="loadChannel(preview, index)" class="btn btn-primary">Загрузить канал</button>
                </div>
              </div>

            </div>
        </li>
      </ul>
    </div>

    <!-- Форма добавления канала -->
    <h2 class="text-2xl mb-2">Добавить канал</h2>
    <div class="rounded-box shadow-md bg-base-100 p-4 mb-8">
      <div class="flex items-baseline mb-2">
        <div class="join">
          <input
            v-model="newChannel"
            type="text"
            placeholder="Введите имя канала или ID пользователя"
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
            {{ previewLoading ? 'Загрузка...' : 'Предварительный просмотр' }}
          </button>
        </div>
        <button @click="testLoadLlamatest" class="btn ml-auto">
          Загрузить llamatest
        </button>
        <div v-if="previewLoading" class="ml-4 text-primary">
          <div class="loading loading-bars loading-sm mr-2"></div>
          Получаем информацию о канале...
        </div>
      </div>
      <div class="text-xs text-info-content">
        Поддерживается: @channelname, channelname, @username, username, PEER ID
      </div>
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
      // Настройки экспорта
      exportSettings: {
        include_system_messages: false,
        include_reposts: true,
        include_polls: true,
        include_discussion_comments: true,
        message_limit: null, // null для безлимитного, число для ограничения
      },
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
        
        // Проверяем, что сервер вернул JSON (а не PDF файл как раньше)
        if (contentType && contentType.includes('application/json')) {
          const result = await res.json();
          if (result.success) {
            eventBus.showAlert(result.message, "success");
          } else {
            eventBus.showAlert(result.error || "Ошибка при создании PDF", "danger");
          }
        } else {
          // Если вернулся не JSON, возможно старое поведение
          eventBus.showAlert("Неожиданный ответ сервера", "danger");
        }
      } catch (error) {
        eventBus.showAlert(error.message || "Ошибка при создании PDF", "danger");
        console.error("Ошибка при создании PDF:", error);
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
      return api
        .delete(`/api/channels/${channelId}`)
        .then((response) => {
          // Если запрос успешен, выводим сообщение об успехе
          if (response.data.message) {
            eventBus.showAlert(response.data.message, "success");
          }
          this.fetchChannels(); // Обновляем список каналов
          return response;
        })
        .catch((error) => {
          // Если произошла ошибка, выводим сообщение об ошибке
          if (error.response && error.response.data.error) {
            eventBus.showAlert(error.response.data.error, "danger");
          } else {
            eventBus.showAlert("Неизвестная ошибка при удалении канала", "danger");
          }
          throw error;
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
          export_settings: this.exportSettings,
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
    
    async cancelDownload(channelId) {
      // Подтверждение действия
      if (!confirm('Вы уверены, что хотите отменить загрузку и удалить канал? Это действие нельзя отменить.')) {
        return;
      }
      
      try {
        // Сначала останавливаем загрузку
        await api.post(`/api/download/stop/${channelId}`);
        
        // Затем удаляем канал и дискуссионную группу
        const response = await api.delete(`/api/channels/${channelId}`);
        
        eventBus.showAlert('Загрузка отменена, канал удален', "success");
        
        // Обновляем список каналов и статусы
        this.loadChannels();
        this.checkDownloadStatuses();
      } catch (error) {
        const errorMessage = error.response?.data?.error || 'Ошибка отмены загрузки';
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
    },
    
    // Тестовая загрузка канала llamatest
    async testLoadLlamatest() {
      const channelUsername = 'llamatest';
      
      try {
        // Сначала удаляем канал, если он существует
        eventBus.showAlert('Удаляем существующий канал llamatest...', 'info');
        
        // Ищем канал в списке загруженных каналов
        const existingChannel = this.channels.find(ch => 
          ch.username === channelUsername || 
          ch.name?.toLowerCase().includes('llamatest') ||
          ch.id?.toString().includes('llamatest')
        );
        
        if (existingChannel) {
          await this.deleteChannel(existingChannel.id);
          // Небольшая задержка после удаления
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
        
        // Затем загружаем канал
        eventBus.showAlert('Загружаем канал llamatest...', 'info');
        
        const response = await api.post('/api/add_channel', {
          channel_username: channelUsername,
        });
        
        eventBus.showAlert(response.data.message, 'success');
        this.fetchChannels(); // Обновляем список каналов
        
      } catch (error) {
        const errorMessage = error.response?.data?.error || error.message || 'Ошибка при тестовой загрузке';
        eventBus.showAlert(errorMessage, 'danger');
        console.error('Ошибка при тестовой загрузке llamatest:', error);
      }
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
