<template>
  <div>
    <h1>Список каналов</h1>
    <div v-if="loading" class="loading">Загрузка...</div>
    <ul v-else>
      <li v-for="channel in channels" :key="channel.id">
        <router-link :to="`/${channel.id}/posts`">{{ channel.name }}</router-link>
      </li>
    </ul>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: "ChannelList",
  data() {
    return {
      channels: [],
      loading: true,
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
}

a {
  text-decoration: none;
  color: #007bff;
}

a:hover {
  text-decoration: underline;
}
</style>