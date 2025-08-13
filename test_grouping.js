// Простой тест логики группировки комментариев

const testPosts = [
  {
    id: 1,
    telegram_id: 100,
    channel_id: 'test_channel',
    message: 'Оригинальный пост',
    date: '2024-01-01T10:00:00Z',
    reply_to: null,
    grouped_id: null
  },
  {
    id: 2,
    telegram_id: 101,
    channel_id: 'test_channel',
    message: 'Комментарий 1',
    date: '2024-01-01T10:05:00Z',
    reply_to: 100,
    grouped_id: null
  },
  {
    id: 3,
    telegram_id: 102,
    channel_id: 'test_channel',
    message: 'Комментарий 2',
    date: '2024-01-01T10:10:00Z',
    reply_to: 100,
    grouped_id: null
  },
  {
    id: 4,
    telegram_id: 103,
    channel_id: 'test_channel',
    message: 'Другой пост без комментариев',
    date: '2024-01-01T11:00:00Z',
    reply_to: null,
    grouped_id: null
  }
];

function testGrouping() {
  // Копируем логику из Wall.vue
  const filteredPosts = testPosts.filter(post => !post.grouped_id && !post.reply_to);
  
  const commentsMap = {};
  const originalPostsMap = {};
  
  testPosts.forEach(post => {
    if (post.reply_to) {
      const replyToId = post.reply_to;
      if (!commentsMap[replyToId]) {
        commentsMap[replyToId] = [];
      }
      commentsMap[replyToId].push(post);
    } else if (!post.grouped_id) {
      originalPostsMap[post.telegram_id] = post;
    }
  });
  
  const postsWithComments = {};
  Object.keys(commentsMap).forEach(originalPostId => {
    const originalPost = originalPostsMap[originalPostId];
    if (originalPost) {
      postsWithComments[originalPostId] = {
        originalPost,
        comments: commentsMap[originalPostId]
      };
    }
  });
  
  console.log('=== Результат группировки ===');
  console.log('Отфильтрованные посты (без комментариев):', filteredPosts.length);
  console.log('Посты с комментариями:', Object.keys(postsWithComments).length);
  
  Object.entries(postsWithComments).forEach(([postId, data]) => {
    console.log(`Пост ${postId}: "${data.originalPost.message}" - ${data.comments.length} комментариев`);
    data.comments.forEach(comment => {
      console.log(`  - Комментарий ${comment.telegram_id}: "${comment.message}"`);
    });
  });
  
  filteredPosts.forEach(post => {
    if (!postsWithComments[post.telegram_id]) {
      console.log(`Одиночный пост ${post.telegram_id}: "${post.message}"`);
    }
  });
}

testGrouping();
