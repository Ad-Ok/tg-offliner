import { createRouter, createWebHistory } from 'vue-router';
import Wall from '../src/components/Wall.vue';
import ChannelsList from '../src/components/ChannelsList.vue';

const routes = [
  {
    path: '/',
    name: 'Channels',
    component: ChannelsList,
  },
  {
    path: '/:channelName/posts',
    name: 'Wall',
    component: Wall,
    props: (route) => ({ channelId: route.params.channelName }),
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;