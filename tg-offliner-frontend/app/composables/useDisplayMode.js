import { computed } from 'vue'

/**
 * Composable для управления режимами отображения через data-mode атрибут
 * 
 * Режимы:
 * - default: обычный веб (/posts/channel)
 * - paper: PDF preview + браузерная печать (/preview/channel?export=pdf)
 * - minimal: IDML preview (/preview/channel?export=idml)
 * 
 * @returns {Object} Утилиты для работы с режимами
 */
export const useDisplayMode = () => {
  const route = useRoute()
  
  /**
   * Определяет текущий режим на основе URL
   * @returns {'default' | 'paper' | 'minimal'}
   */
  const currentMode = computed(() => {
    const exportParam = route.query.export
    
    // PDF export → paper mode
    if (exportParam === 'pdf' || exportParam === '1') {
      return 'paper'
    }
    
    // IDML export → minimal mode
    if (exportParam === 'idml') {
      return 'minimal'
    }
    
    // Default web mode
    return 'default'
  })
  
  /**
   * Проверяет, активен ли режим paper (PDF)
   */
  const isPaperMode = computed(() => currentMode.value === 'paper')
  
  /**
   * Проверяет, активен ли режим minimal (IDML)
   */
  const isMinimalMode = computed(() => currentMode.value === 'minimal')
  
  /**
   * Проверяет, активен ли обычный веб режим
   */
  const isDefaultMode = computed(() => currentMode.value === 'default')
  
  /**
   * Проверяет, активен ли любой режим экспорта (paper или minimal)
   */
  const isExportMode = computed(() => isPaperMode.value || isMinimalMode.value)
  
  return {
    currentMode,
    isPaperMode,
    isMinimalMode,
    isDefaultMode,
    isExportMode
  }
}
