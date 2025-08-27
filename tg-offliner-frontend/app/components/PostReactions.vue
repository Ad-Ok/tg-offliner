
<template>
  <div class="reactions flex space-x-4" v-if="reactions && reactions.recent_reactions.length">
    <div
      v-for="reaction in parsedReactions(reactions.recent_reactions)"
      :key="reaction.reaction"
      class="reaction"
    >
      <span>{{ reaction.reaction }}</span> <span>{{ reaction.count }}</span>
    </div>
  </div>
</template>

<script>
export default {
  name: "PostReactions",
  props: {
    reactions: {
      type: Object,
      required: true,
    },
  },
  methods: {
    parsedReactions(reactions) {
      // Преобразуем реакции, чтобы извлечь только эмодзи
      return reactions.map(reaction => {
        let reactionStr = reaction.reaction;
        // Заменяем экранированный и реальный ZWJ на '+'
        reactionStr = reactionStr.replace(/\\u200d/g, '+').replace(/\u200d/g, '+');
        // Проверяем, является ли это обычной эмодзи-реакцией
        const emojiMatch = reactionStr.match(/emoticon='(.*?)'/);
        if (emojiMatch) {
          return {
            reaction: emojiMatch[1],
            count: reaction.count,
          };
        }
        // Проверяем, является ли это платной реакцией
        if (reactionStr.includes('ReactionPaid')) {
          return {
            reaction: '⭐', // Показываем звездочку для платных реакций
            count: reaction.count,
          };
        }
        // Для всех остальных случаев оставляем как есть
        return {
          reaction: reactionStr,
          count: reaction.count,
        };
      });
    },
  },
};
</script>
