<template>
  <div class="channels-list">
    <h1>Список каналов</h1>
    <div v-if="loading" class="loading">Загрузка...</div>
    <ul v-else>
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
    <div class="add-channel">
      <input
        v-model="newChannel"
        type="text"
        placeholder="Введите имя канала"
        @keyup.enter="addChannel"
      />
      <button @click="addChannel">Добавить канал</button>
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
  },
};
</script>
