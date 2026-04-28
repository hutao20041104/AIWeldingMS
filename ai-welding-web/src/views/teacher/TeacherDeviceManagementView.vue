<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { API_BASE_URL } from '../../composables/useAuth'

type DeviceRow = {
  id: number
  device_code: string
  status: string
  status_label: string
  classroom: string
  start_time?: string | null
  end_time?: string | null
}

const loading = ref(false)
const tableData = ref<DeviceRow[]>([])
const currentPage = ref(1)
const pageSize = 25
const filters = ref({
  device_code: '',
  status: '',
  classroom: '',
})

const statusOptions = [
  { label: '使用中', value: 'in_use' },
  { label: '空闲', value: 'idle' },
  { label: '维护中', value: 'maintaining' },
]
const classroomOptions = computed(() =>
  Array.from(new Set(tableData.value.map((item) => item.classroom))).filter(Boolean),
)

const pagedTableData = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return tableData.value.slice(start, start + pageSize)
})

const totalCount = computed(() => {
  return tableData.value.length
})

function authHeaders() {
  const token = localStorage.getItem('access_token')
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

async function fetchDevices() {
  loading.value = true
  try {
    const query = new URLSearchParams()
    if (filters.value.device_code.trim()) query.set('device_code', filters.value.device_code.trim())
    if (filters.value.status) query.set('status', filters.value.status)
    if (filters.value.classroom.trim()) query.set('classroom', filters.value.classroom.trim())
    const suffix = query.toString() ? `?${query.toString()}` : ''

    const res = await fetch(`${API_BASE_URL}/api/devices${suffix}`, { headers: { ...authHeaders() } })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '获取设备失败')
      return
    }
    tableData.value = data
    currentPage.value = 1
  } catch {
    ElMessage.error('网络异常，获取设备失败')
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.value = {
    device_code: '',
    status: '',
    classroom: '',
  }
  fetchDevices()
}

function formatTime(value?: string | null) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n: number) => `${n}`.padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

onMounted(() => {
  fetchDevices()
})
</script>

<template>
  <section class="module-page">
    <el-card class="module-table-card" shadow="never">
      <div class="module-toolbar">
        <el-input v-model="filters.device_code" placeholder="设备编号" clearable class="module-search" />
        <el-select v-model="filters.status" placeholder="状态" clearable class="module-search">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.classroom" placeholder="教室" clearable class="module-search">
          <el-option v-for="room in classroomOptions" :key="room" :label="room" :value="room" />
        </el-select>
        <div class="module-toolbar-actions">
          <el-button @click="resetFilters">重置</el-button>
          <el-button type="primary" @click="fetchDevices">查询</el-button>
        </div>
      </div>
      <div class="module-table-wrap">
        <el-table :data="pagedTableData" border v-loading="loading">
          <el-table-column prop="device_code" label="设备编号" min-width="200" />
          <el-table-column prop="status_label" label="状态" min-width="160" />
          <el-table-column prop="classroom" label="教室" min-width="220" />
          <el-table-column label="开始时间" min-width="180">
            <template #default="{ row }">
              {{ formatTime(row.start_time) }}
            </template>
          </el-table-column>
          <el-table-column label="结束时间" min-width="180">
            <template #default="{ row }">
              {{ formatTime(row.end_time) }}
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div class="module-pagination">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          layout="total, prev, pager, next"
          :total="totalCount"
        />
      </div>
    </el-card>
  </section>
</template>
