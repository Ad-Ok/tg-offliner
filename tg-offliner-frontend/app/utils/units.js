/**
 * Утилиты для конвертации единиц измерения
 * Загружаются из print-config.json (единый источник правды для Python и JS)
 */

import config from '../../print-config.json'

// Константы конвертации из конфига
export const MM_TO_POINTS = config.conversion.mmToPoints
export const MM_TO_PX = config.conversion.mmToPx
export const POINTS_TO_PX = MM_TO_PX / MM_TO_POINTS

// Размеры страниц в миллиметрах из конфига
export const PAGE_SIZES = config.pageSizes

/**
 * Конвертирует миллиметры в points (1mm = 2.83465 points)
 */
export function mmToPoints(mm) {
  return mm * MM_TO_POINTS
}

/**
 * Конвертирует points в миллиметры
 */
export function pointsToMm(points) {
  return points / MM_TO_POINTS
}

/**
 * Конвертирует миллиметры в пиксели при 96 DPI (1mm = 3.7795275591 px)
 */
export function mmToPx(mm) {
  return mm * MM_TO_PX
}

/**
 * Конвертирует пиксели в миллиметры при 96 DPI
 */
export function pxToMm(px) {
  return px / MM_TO_PX
}

/**
 * Конвертирует points в пиксели (1 point = 1.333... px)
 */
export function pointsToPx(points) {
  return points * POINTS_TO_PX
}

/**
 * Конвертирует пиксели в points
 */
export function pxToPoints(px) {
  return px / POINTS_TO_PX
}
