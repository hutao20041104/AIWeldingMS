<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { UserFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { API_BASE_URL, currentUser } from '../../composables/useAuth'
import dashboardBg from '../../assets/dashboard.png'

type MonitorStudent = {
  student_id: string
  identity_code: string
  username: string
  major: string
  class_name: string
}

type MonitorDevice = {
  id: number
  device_code: string
  status: string
  status_label: string
  seat_usage: string
  students: MonitorStudent[]
}

const loading = ref(false)
const screenRef = ref<HTMLElement | null>(null)
const isFullscreen = ref(false)
const hasActiveCourse = ref(false)
const course = ref<{
  id: number
  course_code: string
  classroom: string
  start_time: string
  end_time: string
  assistant_student_name?: string | null
  student_count: number
} | null>(null)
const devices = ref<MonitorDevice[]>([])
const selectedDeviceId = ref<number | null>(null)
const trendData = ref({
  current: [72, 74, 70, 73, 75, 78, 77, 76, 74, 73, 75, 76],
  voltage: [24, 25, 24, 26, 25, 24, 23, 24, 25, 26, 25, 24],
  wireSpeed: [8.1, 8.3, 8.0, 8.4, 8.2, 8.5, 8.6, 8.4, 8.3, 8.2, 8.4, 8.5],
})
let timer: number | null = null
let trendTimer: number | null = null
let clockTimer: number | null = null
const nowText = ref('')

function authHeaders() {
  const token = localStorage.getItem('access_token')
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

const activeDeviceCount = computed(() => devices.value.filter((d) => d.students.length > 0).length)
const teacherName = computed(() => currentUser.value?.username || '当前教师')
const teacherAvatar = computed(() => currentUser.value?.avatar || '')
const totalAssignedStudents = computed(() => devices.value.reduce((sum, d) => sum + d.students.length, 0))
const ngCount = computed(() => Math.max(0, Math.round(totalAssignedStudents.value * 0.06)))
const goodCount = computed(() => Math.max(0, totalAssignedStudents.value - ngCount.value))
const aiScore = computed(() => {
  if (!course.value?.student_count) return 0
  return Math.round((goodCount.value / course.value.student_count) * 100)
})
const selectedDevice = computed(() => devices.value.find((d) => d.id === selectedDeviceId.value) || null)

function formatTime(value?: string) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n: number) => `${n}`.padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function tickNow() {
  const d = new Date()
  const pad = (n: number) => `${n}`.padStart(2, '0')
  nowText.value = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function fetchMonitor() {
  loading.value = true
  try {
    const res = await fetch(`${API_BASE_URL}/api/courses/monitor/current/`, { headers: { ...authHeaders() } })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '获取实验监控失败')
      return
    }
    hasActiveCourse.value = !!data.has_active_course
    course.value = data.course || null
    devices.value = data.devices || []
    if (!selectedDeviceId.value && devices.value.length > 0) {
      selectedDeviceId.value = devices.value[0].id
    }
    if (selectedDeviceId.value && !devices.value.some((d) => d.id === selectedDeviceId.value)) {
      selectedDeviceId.value = devices.value[0]?.id || null
    }
  } catch {
    ElMessage.error('网络异常，获取实验监控失败')
  } finally {
    loading.value = false
  }
}

function pushTrendPoint(key: 'current' | 'voltage' | 'wireSpeed') {
  const source = trendData.value[key]
  const last = source[source.length - 1]
  const jitter = key === 'wireSpeed' ? (Math.random() - 0.5) * 0.25 : (Math.random() - 0.5) * 2
  const next = Number((last + jitter).toFixed(2))
  source.push(next)
  if (source.length > 18) source.shift()
}

function buildPolyline(arr: number[]) {
  if (arr.length === 0) return ''
  const min = Math.min(...arr)
  const max = Math.max(...arr)
  const span = max - min || 1
  return arr
    .map((v, i) => {
      const x = (i / (arr.length - 1 || 1)) * 100
      const y = 100 - ((v - min) / span) * 100
      return `${x},${y}`
    })
    .join(' ')
}

async function toggleFullscreen() {
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen()
      return
    }
    if (screenRef.value) {
      await screenRef.value.requestFullscreen()
    }
  } catch {
    ElMessage.error('浏览器不支持全屏或全屏操作失败')
  }
}

function onFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement
}

onMounted(() => {
  tickNow()
  fetchMonitor()
  timer = window.setInterval(fetchMonitor, 20000)
  clockTimer = window.setInterval(tickNow, 1000)
  trendTimer = window.setInterval(() => {
    pushTrendPoint('current')
    pushTrendPoint('voltage')
    pushTrendPoint('wireSpeed')
  }, 2000)
  document.addEventListener('fullscreenchange', onFullscreenChange)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
  if (clockTimer) window.clearInterval(clockTimer)
  if (trendTimer) window.clearInterval(trendTimer)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
})
</script>

<template>
  <section ref="screenRef" class="module-page lab-screen" v-loading="loading" :style="{ backgroundImage: `url(${dashboardBg})` }">
    <div class="screen-mask">
      <div class="screen-header">
        <div class="left-time">
          <div class="time-label">实时时间</div>
          <div class="time-value">{{ nowText }}</div>
        </div>
        <h2 class="screen-title">AI焊接实战教学数字化平台</h2>
        <div class="module-toolbar-actions">
          <el-button type="primary" @click="toggleFullscreen">
            {{ isFullscreen ? '恢复' : '大屏显示' }}
          </el-button>
        </div>
      </div>

      <div v-if="!hasActiveCourse" class="empty-state">
        当前无课程进行中
      </div>

      <template v-else>
        <div class="score-circles">
          <div class="circle-card">
            <div class="circle-num">{{ ngCount }}</div>
            <div class="circle-label">NG</div>
          </div>
          <div class="circle-card">
            <div class="circle-num">{{ goodCount }}</div>
            <div class="circle-label">GOOD</div>
          </div>
          <div class="circle-card">
            <div class="circle-num">{{ aiScore }}</div>
            <div class="circle-label">AI评分</div>
          </div>
        </div>

        <div class="summary-grid">
          <el-card shadow="hover" class="neon-card">课程编号：{{ course?.course_code }}</el-card>
          <el-card shadow="hover" class="neon-card">教室：{{ course?.classroom }}</el-card>
          <el-card shadow="hover" class="neon-card">学生人数：{{ course?.student_count }}</el-card>
          <el-card shadow="hover" class="neon-card">已使用设备：{{ activeDeviceCount }}/{{ devices.length }}</el-card>
        </div>

        <div class="time-line">
          上课时间：{{ formatTime(course?.start_time) }} ~ {{ formatTime(course?.end_time) }}
          <span v-if="course?.assistant_student_name">，助教：{{ course.assistant_student_name }}</span>
        </div>

        <div class="monitor-layout">
          <div class="device-grid">
            <div
              v-for="d in devices"
              :key="d.id"
              class="device-tile"
              :class="{ active: selectedDeviceId === d.id }"
              @click="selectedDeviceId = d.id"
            >
              <div class="device-title">
                <span>{{ d.device_code }}</span>
                <span class="seat-usage">{{ d.seat_usage }}</span>
              </div>
              <div class="device-lights">
                <span class="light red"></span>
                <span class="light yellow"></span>
                <span class="light green"></span>
              </div>
              <div class="device-status">状态：{{ d.status_label }}</div>
            </div>
          </div>

          <div class="right-panel">
            <div class="chart-card">
              <div class="chart-title">电流强度</div>
              <svg viewBox="0 0 100 100" preserveAspectRatio="none">
                <polyline :points="buildPolyline(trendData.current)" />
              </svg>
            </div>
            <div class="chart-card">
              <div class="chart-title">电压强度</div>
              <svg viewBox="0 0 100 100" preserveAspectRatio="none">
                <polyline :points="buildPolyline(trendData.voltage)" />
              </svg>
            </div>
            <div class="chart-card">
              <div class="chart-title">送丝速度</div>
              <svg viewBox="0 0 100 100" preserveAspectRatio="none">
                <polyline :points="buildPolyline(trendData.wireSpeed)" />
              </svg>
            </div>
          </div>
        </div>

        <div class="group-panel neon-card">
          <div class="group-title">当前设备分组（点击设备查看）</div>
          <template v-if="selectedDevice">
            <div class="group-sub">设备：{{ selectedDevice.device_code }}（最多 3 人）</div>
            <div v-if="selectedDevice.students.length === 0" class="empty-device">该设备暂无学生</div>
            <div v-else class="group-students">
              <div v-for="s in selectedDevice.students.slice(0, 3)" :key="s.student_id" class="student-chip">
                {{ s.username }}（{{ s.identity_code }}）{{ s.major ? ` - ${s.major}` : '' }}
              </div>
            </div>
          </template>
          <template v-else>
            <div class="empty-device">暂无设备数据</div>
          </template>
        </div>
      </template>

      <div class="people-panel">
        <div class="person-card">
          <el-avatar :src="teacherAvatar || undefined" :icon="teacherAvatar ? undefined : UserFilled" :size="56" />
          <div>
            <div class="person-role">教师</div>
            <div class="person-name">{{ teacherName }}</div>
          </div>
        </div>
        <div class="person-card">
          <el-avatar :icon="UserFilled" :size="56" />
          <div>
            <div class="person-role">助教</div>
            <div class="person-name">{{ course?.assistant_student_name || '未指定助教' }}</div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.lab-screen {
  height: calc(100vh - 120px);
  max-height: calc(100vh - 120px);
  background-size: cover;
  background-position: center;
  border-radius: 14px;
  overflow: hidden;
}
.screen-mask {
  height: 100%;
  max-height: 100%;
  padding: 16px;
  background: linear-gradient(180deg, rgba(2, 16, 34, 0.84), rgba(2, 16, 34, 0.92));
  position: relative;
  overflow: auto;
}
.screen-header {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  color: #d6f6ff;
}
.screen-header .module-toolbar-actions {
  justify-self: end;
}
.left-time {
  justify-self: start;
}
.time-label {
  font-size: 12px;
  color: #8ec8de;
}
.time-value {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 1px;
}
.screen-title {
  display: flex;
  justify-self: center;
  text-align: center;
}
.screen-header h2 {
  margin: 0;
  letter-spacing: 1px;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(180px, 1fr));
  gap: 12px;
  margin: 16px 0;
}
.monitor-layout {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 14px;
}
.device-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}
.device-tile {
  border: 1px solid rgba(80, 203, 255, 0.35);
  background: rgba(3, 24, 48, 0.72);
  border-radius: 10px;
  padding: 10px;
  color: #d7f6ff;
  cursor: pointer;
}
.device-tile.active {
  border-color: #36d5ff;
  box-shadow: 0 0 12px rgba(54, 213, 255, 0.5);
}
.neon-card {
  border: 1px solid rgba(56, 201, 255, 0.35);
  background: rgba(3, 24, 48, 0.58);
  color: #d7f6ff;
}
.score-circles {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin: 8px 0 14px;
}
.circle-card {
  width: 110px;
  height: 110px;
  border-radius: 50%;
  border: 2px solid rgba(54, 213, 255, 0.75);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(3, 24, 48, 0.7);
  color: #d7f6ff;
}
.circle-num {
  font-size: 28px;
  font-weight: 700;
}
.circle-label {
  font-size: 12px;
  color: #8ec8de;
}
.time-line {
  margin-bottom: 12px;
  color: #b3d9e6;
}
.device-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.seat-usage {
  color: #35d5ff;
}
.device-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.device-lights {
  display: flex;
  gap: 6px;
  margin: 8px 0;
}
.light {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.light.red {
  background: #ff4d4f;
}
.light.yellow {
  background: #fadb14;
}
.light.green {
  background: #52c41a;
}
.device-status,
.empty-device {
  color: #a7c8d8;
  margin-top: 4px;
}
.right-panel {
  display: grid;
  gap: 12px;
}
.chart-card {
  border: 1px solid rgba(80, 203, 255, 0.35);
  border-radius: 10px;
  background: rgba(3, 24, 48, 0.72);
  padding: 10px;
  color: #d7f6ff;
}
.chart-title {
  margin-bottom: 8px;
  color: #8ec8de;
}
.chart-card svg {
  width: 100%;
  height: 90px;
}
.chart-card polyline {
  fill: none;
  stroke: #36d5ff;
  stroke-width: 2.2;
}
.group-panel {
  margin-top: 14px;
  padding: 12px;
}
.group-title {
  font-weight: 700;
}
.group-sub {
  color: #8ec8de;
  margin: 6px 0 8px;
}
.group-students {
  display: grid;
  grid-template-columns: repeat(3, minmax(180px, 1fr));
  gap: 8px;
}
.student-grid {
  display: grid;
  gap: 6px;
}
.student-chip {
  padding: 6px 8px;
  border: 1px solid rgba(80, 203, 255, 0.35);
  border-radius: 6px;
  color: #d2eeff;
}
.people-panel {
  position: absolute;
  left: 16px;
  bottom: 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
}
.person-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(80, 203, 255, 0.35);
  background: rgba(3, 24, 48, 0.72);
  color: #d7f6ff;
  min-width: 220px;
}
.person-role {
  color: #8ec8de;
  font-size: 12px;
}
.person-name {
  font-weight: 600;
}
.empty-state {
  padding: 120px 20px;
  text-align: center;
  color: #9ec7d6;
  font-size: 26px;
}
@media (max-width: 1200px) {
  .monitor-layout {
    grid-template-columns: 1fr;
  }
  .right-panel {
    grid-template-columns: repeat(3, minmax(180px, 1fr));
    display: grid;
  }
}
@media (max-width: 1280px) {
  .screen-title {
    display: none;
  }
}
@media (max-width: 900px) {
  .lab-screen {
    height: calc(100vh - 84px);
    max-height: calc(100vh - 84px);
    border-radius: 8px;
  }
  .screen-mask {
    padding: 10px;
  }
  .screen-header {
    grid-template-columns: 1fr auto;
    gap: 8px;
  }
  .time-value {
    font-size: 16px;
  }
  .score-circles {
    gap: 10px;
  }
  .circle-card {
    width: 86px;
    height: 86px;
  }
  .circle-num {
    font-size: 22px;
  }
  .summary-grid {
    grid-template-columns: repeat(2, minmax(140px, 1fr));
  }
  .device-grid {
    grid-template-columns: repeat(2, minmax(140px, 1fr));
  }
  .right-panel {
    grid-template-columns: 1fr;
  }
  .people-panel {
    position: static;
    margin-top: 10px;
    justify-content: center;
    flex-wrap: wrap;
  }
  .person-card {
    min-width: 180px;
  }
}
</style>
