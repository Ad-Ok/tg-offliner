<template>
  <div class="container mx-auto p-4 max-w-4xl">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold">💾 Бэкапы базы данных</h1>
        <p class="text-sm text-gray-500 mt-1">Создание и восстановление резервных копий</p>
      </div>
      <div class="flex gap-2">
        <NuxtLink to="/" class="btn btn-ghost btn-sm">← Назад</NuxtLink>
        <button 
          @click="createBackup" 
          :disabled="isCreating"
          class="btn btn-primary btn-sm"
        >
          <span v-if="isCreating" class="loading loading-spinner loading-xs"></span>
          {{ isCreating ? 'Создание...' : '+ Создать бэкап' }}
        </button>
      </div>
    </div>

    <!-- Alert -->
    <div v-if="alert" :class="['alert mb-4', alert.type === 'success' ? 'alert-success' : 'alert-error']">
      <span>{{ alert.message }}</span>
      <button @click="alert = null" class="btn btn-ghost btn-xs">✕</button>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex justify-center py-12">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <!-- Empty state -->
    <div v-else-if="backups.length === 0" class="text-center py-12 text-gray-500">
      <p class="text-4xl mb-4">📦</p>
      <p class="text-lg">Бэкапов пока нет</p>
      <p class="text-sm mt-2">Нажмите «Создать бэкап» или бэкап будет создан автоматически при запуске</p>
    </div>

    <!-- Backups table -->
    <div v-else class="overflow-x-auto">
      <table class="table table-zebra w-full">
        <thead>
          <tr>
            <th>Имя файла</th>
            <th>Дата</th>
            <th>Размер</th>
            <th>Содержимое</th>
            <th class="text-right">Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="backup in backups" :key="backup.name">
            <td>
              <div class="font-mono text-sm">{{ backup.name }}</div>
              <div v-if="backup.name.includes('before-restore')" class="badge badge-warning badge-xs mt-1">safety</div>
              <div v-else-if="backup.name.includes('auto')" class="badge badge-info badge-xs mt-1">auto</div>
              <div v-else class="badge badge-ghost badge-xs mt-1">manual</div>
            </td>
            <td class="text-sm">{{ formatDate(backup.created_at) }}</td>
            <td class="text-sm">{{ formatSize(backup.size) }}</td>
            <td class="text-sm">
              <span v-if="backup.rows">
                {{ backup.rows.channels || 0 }} каналов, {{ backup.rows.posts || 0 }} постов
              </span>
              <span v-else class="text-gray-400">—</span>
            </td>
            <td class="text-right">
              <div class="flex gap-1 justify-end">
                <button 
                  @click="confirmRestore(backup)" 
                  class="btn btn-outline btn-success btn-xs"
                  :disabled="isRestoring"
                >
                  Восстановить
                </button>
                <button 
                  @click="confirmDelete(backup)" 
                  class="btn btn-outline btn-error btn-xs"
                  :disabled="isRestoring"
                >
                  ✕
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Confirm dialog -->
    <dialog ref="confirmDialog" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg">{{ confirmTitle }}</h3>
        <p class="py-4">{{ confirmMessage }}</p>
        <div class="modal-action">
          <button @click="closeConfirm" class="btn btn-ghost">Отмена</button>
          <button 
            @click="executeConfirm" 
            :class="['btn', confirmAction === 'restore' ? 'btn-success' : 'btn-error']"
            :disabled="isRestoring"
          >
            <span v-if="isRestoring" class="loading loading-spinner loading-xs"></span>
            {{ confirmAction === 'restore' ? 'Восстановить' : 'Удалить' }}
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>
  </div>
</template>

<script setup>
import { apiBase } from '~/services/api'

const backups = ref([])
const isLoading = ref(true)
const isCreating = ref(false)
const isRestoring = ref(false)
const alert = ref(null)

// Confirm dialog
const confirmDialog = ref(null)
const confirmTitle = ref('')
const confirmMessage = ref('')
const confirmAction = ref('')
const confirmTarget = ref(null)

// Загрузка списка бэкапов
async function loadBackups() {
  try {
    const response = await fetch(`${apiBase}/api/backups`)
    const data = await response.json()
    backups.value = data.backups
  } catch (e) {
    showAlert('error', 'Ошибка загрузки списка бэкапов')
  } finally {
    isLoading.value = false
  }
}

// Создание бэкапа
async function createBackup() {
  isCreating.value = true
  try {
    const response = await fetch(`${apiBase}/api/backups`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ label: 'manual' })
    })
    const data = await response.json()
    if (data.success) {
      showAlert('success', `Бэкап создан: ${data.backup.name}`)
      await loadBackups()
    } else {
      showAlert('error', data.error || 'Ошибка создания бэкапа')
    }
  } catch (e) {
    showAlert('error', 'Ошибка создания бэкапа')
  } finally {
    isCreating.value = false
  }
}

// Подтверждение восстановления
function confirmRestore(backup) {
  confirmTitle.value = '⚠️ Восстановить базу?'
  confirmMessage.value = `Текущая база будет заменена данными из "${backup.name}". Автоматически создастся safety-бэкап текущего состояния.`
  confirmAction.value = 'restore'
  confirmTarget.value = backup
  confirmDialog.value?.showModal()
}

// Подтверждение удаления
function confirmDelete(backup) {
  confirmTitle.value = '🗑️ Удалить бэкап?'
  confirmMessage.value = `Бэкап "${backup.name}" будет удалён безвозвратно.`
  confirmAction.value = 'delete'
  confirmTarget.value = backup
  confirmDialog.value?.showModal()
}

function closeConfirm() {
  confirmDialog.value?.close()
}

async function executeConfirm() {
  if (confirmAction.value === 'restore') {
    await restoreBackup(confirmTarget.value)
  } else {
    await deleteBackup(confirmTarget.value)
  }
  closeConfirm()
}

// Восстановление из бэкапа
async function restoreBackup(backup) {
  isRestoring.value = true
  try {
    const response = await fetch(`${apiBase}/api/backups/${backup.name}/restore`, {
      method: 'POST'
    })
    const data = await response.json()
    if (data.success) {
      showAlert('success', `${data.message}. Safety-бэкап: ${data.safety_backup}`)
      await loadBackups()
    } else {
      showAlert('error', data.error || 'Ошибка восстановления')
    }
  } catch (e) {
    showAlert('error', 'Ошибка восстановления')
  } finally {
    isRestoring.value = false
  }
}

// Удаление бэкапа
async function deleteBackup(backup) {
  try {
    const response = await fetch(`${apiBase}/api/backups/${backup.name}`, {
      method: 'DELETE'
    })
    const data = await response.json()
    if (data.success) {
      showAlert('success', `Бэкап удалён`)
      await loadBackups()
    } else {
      showAlert('error', data.error || 'Ошибка удаления')
    }
  } catch (e) {
    showAlert('error', 'Ошибка удаления')
  }
}

function showAlert(type, message) {
  alert.value = { type, message }
  setTimeout(() => { alert.value = null }, 5000)
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

onMounted(() => {
  loadBackups()
})
</script>
