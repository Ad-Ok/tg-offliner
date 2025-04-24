<template>
  <div>
    <h1>Список каналов</h1>
    <div v-if="loading" class="loading">Загрузка...</div>
    <ul v-else>
      <li v-for="channel in channels" :key="channel.id" class="channel-item">
        <router-link :to="`/${channel.id}/posts`">{{ channel.name }}</router-link>
        <button @click="printPdf(channel.id)" class="print-button">Печать PDF</button>
          <button @click="removeChannel(channel.id)" class="delete-button">Удалить канал</button>
      </li>
    </ul>

    <div class="add-channel">
      <input
        v-model="newChannel"
        type="text"
        placeholder="Введите имя канала"
      />
      <button @click="addChannel">Добавить канал</button>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { eventBus } from "@/eventBus";

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
  created() {
    this.fetchChannels();
  },
  methods: {
    fetchChannels() {
      this.loading = true;
      axios
        .get('http://127.0.0.1:5000/api/channels')
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

      axios
        .post('http://127.0.0.1:5000/api/add_channel', {
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
    printPdf(channelId) {
      axios
        .get(`http://127.0.0.1:5000/api/channels/${channelId}/print`, {
          responseType: 'blob', // Указываем, что ожидаем файл
        })
        .then((response) => {
          // Создаём ссылку для скачивания PDF
          const url = window.URL.createObjectURL(new Blob([response.data]));
          const link = document.createElement('a');
          link.href = url;
          link.setAttribute('download', `${channelId}.pdf`);
          document.body.appendChild(link);
          link.click();
          link.remove();
        })
        .catch((error) => {
          console.error('Ошибка при печати PDF:', error);
          alert('Ошибка при печати PDF');
        });
    },
    removeChannel(channelId) {
      if (!confirm("Вы уверены, что хотите удалить этот канал?")) return;

      axios
        .delete(`http://127.0.0.1:5000/api/channels/${channelId}`)
        .then((response) => {
          alert(response.data.message);
          this.fetchChannels(); // Обновляем список каналов
        })
        .catch((error) => {
          console.error('Ошибка при удалении канала:', error);
          alert(error.response?.data?.error || "Ошибка при удалении канала");
        });
    },
  },
};
</script>

<style>
.loading {
  font-size: 18px;
  text-align: center;
  margin-top: 20px;
}

ul {
  list-style-type: none;
  padding: 0;
}

li {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
}

a {
  text-decoration: none;
  color: #007bff;
}

a:hover {
  text-decoration: underline;
}

.add-channel {
  margin-top: 20px;
}

.add-channel input {
  padding: 8px;
  font-size: 16px;
  margin-right: 10px;
}

.add-channel button {
  padding: 8px 16px;
  font-size: 16px;
  cursor: pointer;
}

.print-button {
  padding: 5px 10px;
  font-size: 14px;
  cursor: pointer;
  background-color: #f0f0f0;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.print-button:hover {
  background-color: #e0e0e0;
}

.delete-button {
  padding: 5px 10px;
  font-size: 14px;
  cursor: pointer;
  background-color: #ffb3b3;
  color: white;
  border: none;
  border-radius: 4px;
}

.delete-button:hover {
  background-color: #ff1a1a;
}

</style>