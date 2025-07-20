
<template>
  <div class="reactions" v-if="reactions && reactions.recent_reactions.length">
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
        const match = reaction.reaction.match(/emoticon='(.*?)'/); // Извлекаем значение из ReactionEmoji
        return {
          reaction: match ? match[1] : reaction.reaction, // Если найдено, берём эмодзи, иначе оставляем как есть
          count: reaction.count,
        };
      });
    },
  },
};
</script>

<style>
.reactions {
  display: flex;
  margin-top: 10px;
  gap: 20px;
}

.reaction {
  display: flex;
  align-items: center;
  gap: 5px;
}
</style>