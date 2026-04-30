<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { Monitor, Location, Timer, Warning, Tools, Clock } from '@element-plus/icons-vue'
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
const pageSize = 12 // Changed to 12 for grid layout (4x3)
const filters = ref({
  device_code: '',
  status: '',
  classroom: '',
})

const previousDeviceStatuses = ref<Record<number, string>>({})
let pollingTimer: any = null

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

async function fetchDevices(isPolling = false) {
  if (!isPolling) loading.value = true
  try {
    const query = new URLSearchParams()
    if (filters.value.device_code.trim()) query.set('device_code', filters.value.device_code.trim())
    if (filters.value.status) query.set('status', filters.value.status)
    if (filters.value.classroom.trim()) query.set('classroom', filters.value.classroom.trim())
    const suffix = query.toString() ? `?${query.toString()}` : ''

    const res = await fetch(`${API_BASE_URL}/api/devices${suffix}`, { headers: { ...authHeaders() } })
    const data = await res.json()
    if (!res.ok) {
      if (!isPolling) ElMessage.error(data.message || '获取设备失败')
      return
    }

    // Check for repair notifications
    if (Object.keys(previousDeviceStatuses.value).length > 0) {
      data.forEach((device: DeviceRow) => {
        const oldStatus = previousDeviceStatuses.value[device.id]
        if (oldStatus === 'maintaining' && (device.status === 'idle' || device.status === 'in_use')) {
          ElNotification({
            title: '设备修复通知',
            message: `设备 ${device.device_code} 已完成维护并恢复正常！`,
            type: 'success',
            duration: 6000
          })
        }
      })
    }

    // Update statuses map
    data.forEach((d: DeviceRow) => {
      previousDeviceStatuses.value[d.id] = d.status
    })

    tableData.value = data
  } catch {
    if (!isPolling) ElMessage.error('网络异常，获取设备失败')
  } finally {
    if (!isPolling) loading.value = false
  }
}

function resetFilters() {
  filters.value = {
    device_code: '',
    status: '',
    classroom: '',
  }
  currentPage.value = 1
  fetchDevices()
}

async function handleReportFault(device: DeviceRow) {
  try {
    await ElMessageBox.confirm(`确定要上报设备 ${device.device_code} 故障吗？上报后该设备将转为维护中状态，等待管理员处理。`, '故障上报', {
      confirmButtonText: '确定上报',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const res = await fetch(`${API_BASE_URL}/api/devices/${device.id}/report_fault`, {
      method: 'POST',
      headers: { ...authHeaders() }
    })
    const data = await res.json()
    if (res.ok) {
      ElMessage.success('故障上报成功，已通知后台管理员抢修')
      // Optimistic UI update
      device.status = 'maintaining'
      device.status_label = '维护中'
      previousDeviceStatuses.value[device.id] = 'maintaining'
    } else {
      ElMessage.error(data.message || '上报失败')
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('网络异常，上报失败')
  }
}

function formatTime(value?: string | null) {
  if (!value) return '尚未开始'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n: number) => `${n}`.padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function startPolling() {
  pollingTimer = setInterval(() => {
    fetchDevices(true)
  }, 5000)
}

onMounted(() => {
  fetchDevices()
  startPolling()
})

onUnmounted(() => {
  if (pollingTimer) clearInterval(pollingTimer)
})
</script>

<template>
  <section class="device-management-page">
    <el-card class="glass-card module-table-card" shadow="never">
      <div class="module-toolbar">
        <div class="toolbar-left">
          <el-input v-model="filters.device_code" placeholder="设备编号" clearable class="module-search search-input" />
          <el-select v-model="filters.status" placeholder="状态" clearable class="module-search search-input">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-select v-model="filters.classroom" placeholder="教室" clearable class="module-search search-input">
            <el-option v-for="room in classroomOptions" :key="room" :label="room" :value="room" />
          </el-select>
          <el-button @click="resetFilters" plain>重置</el-button>
          <el-button type="primary" @click="fetchDevices(false)" class="gradient-btn">查询</el-button>
        </div>
      </div>
      
      <div class="device-grid-wrap" v-loading="loading">
        <div class="device-grid" v-if="pagedTableData.length > 0">
          <div v-for="device in pagedTableData" :key="device.id" class="device-card" :class="[device.status]">
            <div class="card-header">
              <h3 class="device-code"><el-icon><Monitor /></el-icon> {{ device.device_code }}</h3>
              <el-tag 
                :type="device.status === 'in_use' ? 'success' : device.status === 'idle' ? 'info' : 'danger'" 
                effect="dark"
                round
                class="status-tag"
              >
                {{ device.status_label }}
              </el-tag>
            </div>
            
            <div class="card-body">
              <div class="info-row">
                <el-icon><Location /></el-icon>
                <span>教室: {{ device.classroom }}</span>
              </div>
              <div class="info-row">
                <el-icon><Clock /></el-icon>
                <span>开始: {{ formatTime(device.start_time) }}</span>
              </div>
              <div class="info-row">
                <el-icon><Timer /></el-icon>
                <span>结束: {{ formatTime(device.end_time) }}</span>
              </div>
            </div>
            
            <div class="card-footer">
              <el-button 
                v-if="device.status !== 'maintaining'" 
                type="danger" 
                plain 
                size="small"
                class="report-btn"
                @click="handleReportFault(device)">
                <el-icon><Warning /></el-icon> 故障上报
              </el-button>
              
              <div v-else class="maintaining-alert">
                <el-icon class="is-loading" :size="16"><Tools /></el-icon>
                <span>管理员紧急抢修中...</span>
              </div>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无设备数据" />
      </div>

      <div class="module-pagination">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          layout="total, prev, pager, next"
          :total="totalCount"
          background
        />
      </div>
    </el-card>
  </section>
</template>

<style scoped>
.device-management-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  background: linear-gradient(135deg, #f0f4f8 0%, #e2eafc 100%);
  height: calc(100vh - 64px);
  box-sizing: border-box;
  overflow: hidden;
}

.glass-card {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(31, 38, 135, 0.05);
  transition: all 0.3s ease;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

:deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 20px 24px;
}

.module-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.toolbar-left {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.search-input {
  width: 180px;
}
:deep(.search-input .el-input__wrapper) {
  border-radius: 20px;
  box-shadow: 0 0 0 1px #dcdfe6 inset;
  background: rgba(255,255,255,0.8);
}

.gradient-btn {
  background: linear-gradient(135deg, #409eff 0%, #3a8ee6 100%);
  border: none;
  border-radius: 20px;
  padding: 8px 24px;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
  transition: all 0.3s;
}
.gradient-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.4);
}

.device-grid-wrap {
  flex: 1;
  overflow-y: auto;
  padding-right: 8px;
}

.device-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  align-content: start;
}

.device-card {
  background: #ffffff;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  position: relative;
  overflow: hidden;
}

.device-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 4px;
  background: #909399; /* default idle */
  transition: all 0.3s;
}

.device-card.in_use::before { background: #67c23a; }
.device-card.idle::before { background: #909399; }
.device-card.maintaining::before { background: #f56c6c; }

.device-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px 0 rgba(0, 0, 0, 0.1);
  border-color: #dcdfe6;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-top: 4px;
}

.device-code {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 6px;
  letter-spacing: 0.5px;
}

.status-tag {
  font-weight: 600;
  letter-spacing: 1px;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 20px;
  flex: 1;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #606266;
}

.info-row .el-icon {
  color: #909399;
  font-size: 14px;
}

.card-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  height: 32px;
  border-top: 1px dashed #ebeef5;
  padding-top: 12px;
}

.report-btn {
  border-radius: 16px;
  transition: all 0.3s;
}
.report-btn:hover {
  box-shadow: 0 4px 12px rgba(245, 108, 108, 0.3);
}

.maintaining-alert {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #f56c6c;
  font-size: 13px;
  font-weight: 600;
  background: rgba(245, 108, 108, 0.1);
  padding: 6px 12px;
  border-radius: 16px;
  width: 100%;
  justify-content: center;
}

.module-pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
  border-top: 1px solid rgba(0,0,0,0.05);
}
</style>
