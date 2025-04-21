<template>
  <div>
    <h1>Список каналов</h1>
    <div v-if="loading" class="loading">Загрузка...</div>
    <ul v-else>
      <li v-for="channel in channels" :key="channel.id" class="channel-item">
        <router-link :to="`/${channel.id}/posts`">{{ channel.name }}</router-link>
        <button @click="printPdf(channel.id)" class="print-button">Печать PDF</button>
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

    <div class="logs">
      <h2>Серверные логи</h2>
      <div v-if="logsLoading" class="loading">Загрузка логов...</div>
      <pre v-else>{{ logs }}</pre>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

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
    };
  },
  created() {
    this.fetchChannels();
    this.startLogsFetching();
  },
  beforeUnmount() {
    this.stopLogsFetching();
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
        alert("Введите имя канала!");
        return;
      }

      // Удаляем символ @ в начале строки, если он есть
      const sanitizedChannel = this.newChannel.trim().replace(/^@/, "");

      console.log("Отправка запроса с данными:", sanitizedChannel);

      axios
        .post('http://127.0.0.1:5000/api/add_channel', {
          channel_username: sanitizedChannel,
        })
        .then((response) => {
          alert(response.data.message);
          this.newChannel = ""; // Очищаем поле ввода
          this.fetchChannels(); // Обновляем список каналов
        })
        .catch((error) => {
          console.error('Ошибка при добавлении канала:', error);
          alert(error.response?.data?.error || "Ошибка при добавлении канала");
        });
    },
    printPdf(channelId) {
      console.log(`Печать PDF для канала с ID: ${channelId}`);
      // Здесь будет логика для печати PDF
    },
    fetchLogs() {
      this.logsLoading = true;
      axios
        .get('http://127.0.0.1:5000/api/logs')
        .then((response) => {
          this.logs = response.data;
          this.logsLoading = false;
        })
        .catch((error) => {
          console.error('Ошибка при загрузке логов:', error);
          this.logsLoading = false;
        });
    },
    startLogsFetching() {
      this.fetchLogs(); // Загружаем логи сразу
      this.logsInterval = setInterval(this.fetchLogs, 5000); // Обновляем каждые 5 секунд
    },
    stopLogsFetching() {
      if (this.logsInterval) {
        clearInterval(this.logsInterval);
        this.logsInterval = null;
      }
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

.logs {
  margin-top: 30px;
}

.logs pre {
  background-color: #f8f9fa;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  max-height: 500px;
  overflow-y: auto;
  min-height: 300px;
}
</style>