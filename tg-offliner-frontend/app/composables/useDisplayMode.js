import { computed } from 'vue'

/**
 * Composable для управления режимами отображения через data-mode атрибут
 * 
 * Режимы:
 * - default: обычный веб (везде по умолчанию)
 * - minimal: preview для IDML (/preview/channel)
 * 
 * Примечание: Для PDF/печати используется встроенный Tailwind вариант `print:` (@media print)
 * 
 * @returns {Object} Утилиты для работы с режимами
 */
export const useDisplayMode = () => {
  const route = useRoute()
  
  /**
   * Определяет текущий режим на основе URL
   * @returns {'default' | 'minimal'}
   */
  const currentMode = computed(() => {
    // minimal: только на /preview/* (для IDML)
    if (route.path.startsWith('/preview/')) {
      return 'minimal'
    }
    
    // Default web mode (везде остальное)
    return 'default'
  })
  
  /**
   * Проверяет, активен ли режим minimal (IDML preview)
   */
  const isMinimalMode = computed(() => currentMode.value === 'minimal')
  
  /**
   * Проверяет, активен ли обычный веб режим
   */
  const isDefaultMode = computed(() => currentMode.value === 'default')
  
  return {
    currentMode,
    isMinimalMode,
    isDefaultMode
  }
}
