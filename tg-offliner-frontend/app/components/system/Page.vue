<template>
  <div class="page-container mb-8">
    <!-- Заголовок страницы -->
    <div class="flex justify-between items-center mb-4 p-3 bg-gray-100 rounded-t-lg border-b">
      <h3 class="text-lg font-semibold text-gray-700">
        Страница {{ pageNumber }}
      </h3>
      <span class="text-sm text-gray-500">
        {{ blocksCount }} {{ blocksCount === 1 ? 'блок' : blocksCount < 5 ? 'блока' : 'блоков' }}
      </span>
    </div>

    <!-- Vue Grid Layout контейнер -->
    <ClientOnly>
      <div v-if="gridLoaded && layout && layout.length > 0" class="relative bg-gray-50 rounded-b-lg p-4 border border-t-0">
        <component
          :is="GridLayout"
          v-model:layout="layout"
          :col-num="12"
          :row-height="100"
          :is-draggable="isEditMode"
          :is-resizable="isEditMode"
          :is-mirrored="false"
          :vertical-compact="true"
          :margin="[10, 10]"
          :use-css-transforms="true"
          @layout-updated="handleLayoutUpdated"
        >
          <component
            :is="GridItem"
            v-for="item in layout"
            :key="item.i"
            :x="item.x"
            :y="item.y"
            :w="item.w"
            :h="item.h"
            :i="item.i"
            :static="!isEditMode"
            class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
          >
            <div class="h-full flex flex-col">
              <!-- Block header with delete button -->
              <div v-if="isEditMode" class="flex justify-between items-center p-2 bg-gray-100 border-b border-gray-200">
                <span class="text-xs text-gray-600 font-medium">{{ item.i }}</span>
                <button
                  @click="$emit('delete-block', item.i)"
                  class="text-red-500 hover:text-red-700 text-sm font-bold"
                  title="Delete block"
                >
                  ✕
                </button>
              </div>

              <!-- Block content -->
              <div class="flex-1 overflow-auto">
                <PageBlock
                  :block-id="item.i"
                  :content="item.content"
                  :is-edit-mode="isEditMode"
                  :channel-posts="channelPosts"
                  @edit="(blockId) => $emit('edit-block', blockId)"
                  @delete="(blockId) => $emit('delete-block', blockId)"
                />
              </div>
            </div>
          </component>
        </component>
      </div>

      <!-- Заглушка если нет блоков -->
      <div v-else-if="gridLoaded" class="text-center p-8 bg-gray-50 rounded-b-lg border border-t-0">
        <p class="text-gray-500">Нет блоков на этой странице</p>
      </div>

      <!-- Загрузка -->
      <div v-else class="text-center p-8 bg-gray-100 rounded-b-lg">
        <p class="text-gray-600">Загрузка...</p>
      </div>
    </ClientOnly>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, shallowRef, watch } from 'vue'
import PageBlock from '../PageBlock.vue'
import { usePages } from '~/composables/usePages'

const props = defineProps({
  page: {
    type: Object,
    required: true
  },
  pageNumber: {
    type: Number,
    required: true
  },
  isEditMode: {
    type: Boolean,
    default: false
  },
  channelPosts: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['layout-updated', 'edit-block', 'delete-block'])

const { blocksToLayout, layoutToBlocks } = usePages()

// Компоненты Vue Grid Layout (загружаются на клиенте)
const GridLayout = shallowRef(null)
const GridItem = shallowRef(null)
const gridLoaded = ref(false)

// Layout для Vue Grid Layout
const layout = ref([])

// Количество блоков
const blocksCount = computed(() => layout.value.length)

// Инициализация layout из данных страницы
const initializeLayout = () => {
  if (props.page?.json_data?.blocks) {
    layout.value = blocksToLayout(props.page.json_data.blocks)
  } else {
    layout.value = []
  }
}

// Инициализация при монтировании
initializeLayout()

// Reload layout when page changes
watch(() => props.page, () => {
  initializeLayout()
}, { deep: true })

// Load Vue Grid Layout components on client
onMounted(async () => {
  if (process.client) {
    try {
      const vueGridLayout = await import('vue-grid-layout-v3')
      GridLayout.value = vueGridLayout.GridLayout
      GridItem.value = vueGridLayout.GridItem
      gridLoaded.value = true
    } catch (error) {
      console.error('Error loading vue-grid-layout-v3:', error)
    }
  }
})

// Обработчик изменения layout
const handleLayoutUpdated = (newLayout) => {
  if (!props.isEditMode) return

  emit('layout-updated', {
    pageId: props.page.id,
    layout: newLayout,
    blocks: layoutToBlocks(newLayout, props.page.json_data.blocks)
  })
}
</script>

<style scoped>
/* Стили без печати */
</style>