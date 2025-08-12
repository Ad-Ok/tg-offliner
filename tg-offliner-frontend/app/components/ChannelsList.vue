<template>
  <div class="channels-list">
    <h1>Список каналов</h1>
    <div v-if="loading" class="loading">Загрузка...</div>
    
    <!-- Загруженные каналы -->
    <div v-if="!loading && channels.length > 0">
      <h2>Загруженные каналы</h2>
      <ul>
        <li v-for="channel in channels" :key="channel.id" class="channel-item">
          <div class="channel-main">
            <img
              v-if="channel.avatar"
              :src="channelAvatarSrc(channel)"
              alt="Аватар"
              class="channel-avatar"
            />
            <router-link :to="`/${channel.id}/posts`">{{ channel.name }}</router-link>
            <div class="channel-info">
              <span v-if="channel.creation_date">Создан {{ channel.creation_date }}</span>
              <span v-if="channel.subscribers">&nbsp;•&nbsp;{{ channel.subscribers }} подписчиков</span>
            </div>
            <button @click="printPdf(channel.id)" class="print-button">Печать PDF</button>
            <button @click="removeChannel(channel.id)" class="delete-button">Удалить канал</button>
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
        placeholder="Введите имя канала"
        @keyup.enter="previewChannel"
      />
      <button @click="previewChannel">Предварительный просмотр</button>
    </div>
  </div>
</template>

<script>
import { eventBus } from "~/eventBus";
import { api, apiBase, mediaBase } from '~/services/api'; // добавь mediaBase

export default {
  name: "ChannelsList",
  data() {
    return {
      channels: [],
      previewChannels: [], // Отдельный массив для preview-каналов
      loading: true,
      newChannel: "", // Поле для ввода имени канала
      logs: "", // Логи сервера
      logsLoading: false, // Флаг загрузки логов
      logsInterval: null, // Интервал для обновления логов
      logsOffset: 0, // Offset для логов
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
      this.loading = true;
      api
        .get('/api/channels')
        .then((response) => {
          this.channels = response.data;
          this.loading = false;
        })
        .catch((error) => {
          console.error('Ошибка при загрузке каналов:', error);
          this.loading = false;
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
      this.loading = true;
      api.get(`/api/channel_preview?username=${encodeURIComponent(sanitizedChannel)}`)
        .then(response => {
          const preview = response.data;
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
          this.loading = false;
          this.newChannel = "";
        })
        .catch(error => {
          eventBus.showAlert("Ошибка: " + (error.response?.data?.error || error.message), "danger");
          this.loading = false;
        });
    },
    loadChannel(preview, index) {
      // Удаляем символ @ в начале строки, если он есть
      const sanitizedChannel = preview.username.replace(/^@/, "");

      // Показываем сообщение о начале загрузки
      eventBus.showAlert(`Загружаем канал ${preview.name}...`, "info");

      api
        .post('/api/add_channel', {
          channel_username: sanitizedChannel,
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
    }
  },
};
</script>

<style scoped>
h2 {
  color: #333;
  margin: 20px 0 10px 0;
  font-size: 1.3em;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 5px;
}

.preview-item {
  border: 2px dashed #007bff !important;
  background-color: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 10px;
}

.preview-item .channel-main {
  background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
}

.channel-name {
  font-weight: bold;
  color: #333;
  font-size: 1.1em;
}

.load-button {
  background-color: #28a745;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  margin-left: 10px;
  font-weight: bold;
}

.load-button:hover {
  background-color: #218838;
}

.cancel-button {
  background-color: #6c757d;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  margin-left: 10px;
}

.cancel-button:hover {
  background-color: #5a6268;
}

.channel-item {
  margin-bottom: 15px;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.channel-main {
  display: flex;
  align-items: center;
  padding: 15px;
  background-color: #f9f9f9;
}

.channel-avatar {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  margin-right: 15px;
  object-fit: cover;
}

.channel-info {
  flex-grow: 1;
  margin-left: 15px;
  color: #666;
  font-size: 0.9em;
}

.channel-description {
  padding: 15px;
  background-color: white;
  border-top: 1px solid #eee;
  color: #555;
  line-height: 1.4;
}

.print-button, .delete-button {
  margin-left: 10px;
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.print-button {
  background-color: #007bff;
  color: white;
}

.print-button:hover {
  background-color: #0056b3;
}

.delete-button {
  background-color: #dc3545;
  color: white;
}

.delete-button:hover {
  background-color: #c82333;
}

.add-channel {
  margin-top: 20px;
  padding: 20px;
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 8px;
}

.add-channel input {
  padding: 10px;
  margin-right: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  width: 250px;
}

.add-channel button {
  padding: 10px 20px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.add-channel button:hover {
  background-color: #0056b3;
}

.loading {
  text-align: center;
  padding: 20px;
  font-size: 1.1em;
  color: #666;
}

ul {
  list-style: none;
  padding: 0;
}

li {
  margin-bottom: 10px;
}

a {
  color: #007bff;
  text-decoration: none;
  font-weight: bold;
  font-size: 1.1em;
}

a:hover {
  text-decoration: underline;
}
</style>