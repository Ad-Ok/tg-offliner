import { createRouter, createWebHistory } from 'vue-router';
import Wall from '../src/components/Wall.vue';

const routes = [
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