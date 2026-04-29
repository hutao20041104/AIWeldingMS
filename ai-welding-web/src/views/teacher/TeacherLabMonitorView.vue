<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, nextTick } from 'vue'
import { UserFilled, ZoomIn, ZoomOut } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { API_BASE_URL, currentUser } from '../../composables/useAuth'
import { useCharts } from '../../composables/useCharts'
import type * as echarts from 'echarts'
import dashboardBg from '../../assets/dashboard.png'

type MonitorStudent = {
  student_id: string; identity_code: string; username: string; major: string; class_name: string
}
type MonitorDevice = {
  id: number; device_code: string; status: string; status_label: string; seat_usage: string; students: MonitorStudent[]
}

const loading = ref(false)
const screenRef = ref<HTMLElement | null>(null)
const isFullscreen = ref(false)
const hasActiveCourse = ref(false)
const course = ref<{
  id: number; course_code: string; classroom: string; start_time: string; end_time: string;
  assistant_student_name?: string | null; student_count: number
} | null>(null)
const devices = ref<MonitorDevice[]>([])
const selectedDeviceId = ref<number | null>(null)
const nowText = ref('')
const nowTime = ref('')
const nowDate = ref('')
const nowWeekday = ref('')

let timer: number | null = null
let clockTimer: number | null = null

const { initChart, startTrendTimer, resizeAll, dispose } = useCharts()

const chartRefs = ref<Record<string, HTMLElement | null>>({
  weldVoltage: null, arcVoltage: null, wireSpeed: null, gasFlow: null,
})
const chartInstMap: Record<string, echarts.ECharts | null> = {
  weldVoltage: null, arcVoltage: null, wireSpeed: null, gasFlow: null,
}

function authHeaders() {
  const token = localStorage.getItem('access_token')
  const h: Record<string, string> = {}
  if (token) h.Authorization = `Bearer ${token}`
  return h
}

const activeDeviceCount = computed(() => devices.value.filter(d => d.students.length > 0).length)
const teacherName = computed(() => currentUser.value?.username || '教师')
const totalStudents = computed(() => devices.value.reduce((s, d) => s + d.students.length, 0))
const ngCount = computed(() => Math.max(0, Math.round(totalStudents.value * 0.06)))
const goodCount = computed(() => Math.max(0, totalStudents.value - ngCount.value))
const aiScore = computed(() => {
  if (!course.value?.student_count) return 0
  return Math.round((goodCount.value / course.value.student_count) * 100)
})
const selectedDevice = computed(() => devices.value.find(d => d.id === selectedDeviceId.value) || null)
const displayedStudents = computed(() => {
  if (selectedDeviceId.value) {
    const d = devices.value.find(dev => dev.id === selectedDeviceId.value)
    return d ? d.students : []
  }
  return devices.value.flatMap(d => d.students)
})

const runHours = computed(() => {
  if (!course.value?.start_time) return 0
  const diff = Date.now() - new Date(course.value.start_time).getTime()
  return Math.max(0, Math.round(diff / 3600000))
})
const powerUsage = computed(() => (runHours.value * 1.2).toFixed(0))

function tickNow() {
  const d = new Date()
  const pad = (n: number) => `${n}`.padStart(2, '0')
  const weeks = ['星期日','星期一','星期二','星期三','星期四','星期五','星期六']
  nowTime.value = `${pad(d.getHours())}:${pad(d.getMinutes())}`
  nowDate.value = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`
  nowWeekday.value = weeks[d.getDay()]
}

async function fetchMonitor() {
  loading.value = true
  try {
    const res = await fetch(`${API_BASE_URL}/api/courses/monitor/current/`, { headers: { ...authHeaders() } })
    const data = await res.json()
    if (!res.ok) { ElMessage.error(data.message || '获取监控失败'); return }
    hasActiveCourse.value = !!data.has_active_course
    course.value = data.course || null
    devices.value = data.devices || []
    if (!selectedDeviceId.value && devices.value.length > 0) selectedDeviceId.value = devices.value[0].id
    if (selectedDeviceId.value && !devices.value.some(d => d.id === selectedDeviceId.value))
      selectedDeviceId.value = devices.value[0]?.id || null
  } catch { ElMessage.error('网络异常') } finally { loading.value = false }
}

async function toggleFullscreen() {
  try {
    if (document.fullscreenElement) { await document.exitFullscreen(); return }
    if (screenRef.value) await screenRef.value.requestFullscreen()
  } catch { ElMessage.error('全屏操作失败') }
}
function onFsChange() { isFullscreen.value = !!document.fullscreenElement }

function setChartRef(key: string) {
  return (el: any) => { chartRefs.value[key] = el }
}

onMounted(async () => {
  tickNow()
  await fetchMonitor()
  timer = window.setInterval(fetchMonitor, 20000)
  clockTimer = window.setInterval(tickNow, 1000)
  document.addEventListener('fullscreenchange', onFsChange)
  window.addEventListener('resize', resizeAll)
  await nextTick()
  for (const key of ['weldVoltage','arcVoltage','wireSpeed'] as const) {
    const el = chartRefs.value[key]
    if (el) chartInstMap[key] = initChart(el, key)
  }
  startTrendTimer(chartInstMap as any)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
  if (clockTimer) window.clearInterval(clockTimer)
  document.removeEventListener('fullscreenchange', onFsChange)
  window.removeEventListener('resize', resizeAll)
  dispose()
})
</script>

<template>
  <section ref="screenRef" class="module-page lab-screen" v-loading="loading" :style="{ backgroundImage: `url(${dashboardBg})` }">
    <div class="screen-mask">
      <!-- HEADER -->
      <header class="ds-header">
        <div class="ds-header-left">
          <div class="ds-time">{{ nowTime }}</div>
          <div class="ds-date">{{ nowDate }}<span class="ds-week">{{ nowWeekday }}</span></div>
        </div>
        <h1 class="ds-title">AI焊接实践教学数字化平台</h1>
        <div class="ds-header-right">
          <el-avatar :size="32" :icon="UserFilled" />
          <span class="ds-user-name">{{ teacherName }}</span>
          <button class="ds-btn-outline ds-btn-icon" @click="toggleFullscreen" title="全屏/恢复">
            <el-icon :size="16"><ZoomOut v-if="isFullscreen" /><ZoomIn v-else /></el-icon>
          </button>
        </div>
      </header>

      <div v-if="!hasActiveCourse" class="empty-state">当前无课程进行中</div>

      <template v-else>
        <div class="ds-body">
          <!-- LEFT -->
          <aside class="ds-left">
            <div class="ds-panel">
              <div class="ds-panel-title"><span class="dot green"></span>设备运行情况</div>
              <div class="ds-run-info">
                <div class="ds-run-item">
                  <div class="ds-run-label">运行时间</div>
                  <div class="ds-run-val"><b>{{ runHours }}</b>小时</div>
                </div>
                <div class="ds-run-item">
                  <div class="ds-run-label">耗电量</div>
                  <div class="ds-run-val"><b>{{ powerUsage }}</b>kW·h</div>
                </div>
              </div>
              <div class="ds-station">
                <span class="ds-station-label">工位</span>
                <span class="ds-station-val">{{ String(activeDeviceCount).padStart(2,'0') }}</span>
              </div>
            </div>

            <div class="ds-panel">
              <div class="ds-panel-title"><span class="dot cyan"></span>实习学生信息</div>
              <div class="ds-student-chips">
                <el-tooltip v-for="s in displayedStudents.slice(0,6)" :key="s.student_id" effect="dark" placement="top">
                  <template #content>
                    学号：{{ s.identity_code }}<br>专业：{{ s.major || '无' }}<br>班级：{{ s.class_name || '无' }}
                  </template>
                  <div class="ds-stu-chip">
                    <el-avatar :size="32" :icon="UserFilled" class="ds-stu-avatar" />
                    <span class="ds-stu-name">{{ s.username }}</span>
                  </div>
                </el-tooltip>
                <div v-if="displayedStudents.length > 6" class="ds-stu-chip ds-stu-more">
                  +{{ displayedStudents.length - 6 }}
                </div>
                <div v-if="displayedStudents.length === 0" style="color: rgba(255,255,255,0.4); font-size: 12px; margin-top: 5px;">暂无学生</div>
              </div>
            </div>

            <div class="ds-panel">
              <div class="ds-panel-title">今日</div>
              <div class="ds-today-card">
                <div class="ds-today-class">{{ course?.classroom || '教室' }}</div>
                <div class="ds-today-date">{{ nowDate }}</div>
                <div class="ds-today-count">{{ course?.course_code }}，{{ course?.student_count }}人</div>
              </div>
            </div>

            <div class="ds-people">
              <div class="ds-person">
                <el-avatar :size="64" :icon="UserFilled" class="ds-person-avatar" />
                <div class="ds-person-name">{{ teacherName }}</div>
                <div class="ds-person-role">教师</div>
              </div>
              <div class="ds-person">
                <el-avatar :size="64" :icon="UserFilled" class="ds-person-avatar" />
                <div class="ds-person-name">{{ course?.assistant_student_name || '未指定' }}</div>
                <div class="ds-person-role">助教</div>
              </div>
            </div>
          </aside>

          <!-- CENTER -->
          <main class="ds-center">
            <div class="ds-gauges">
              <div class="ds-gauge ng">
                <svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="52" class="gauge-bg"/><circle cx="60" cy="60" r="52" class="gauge-ring ng-ring"/></svg>
                <div class="gauge-inner"><div class="gauge-num">{{ ngCount }}</div><div class="gauge-label">NG</div></div>
              </div>
              <div class="ds-gauge good">
                <svg viewBox="0 0 140 140"><circle cx="70" cy="70" r="62" class="gauge-bg"/><circle cx="70" cy="70" r="62" class="gauge-ring good-ring"/></svg>
                <div class="gauge-inner"><div class="gauge-num lg">{{ goodCount }}</div><div class="gauge-label">GOOD</div></div>
              </div>
              <div class="ds-gauge ai">
                <svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="52" class="gauge-bg"/><circle cx="60" cy="60" r="52" class="gauge-ring ai-ring"/></svg>
                <div class="gauge-inner"><div class="gauge-num">{{ aiScore }}</div><div class="gauge-label">AI评分</div></div>
              </div>
            </div>

            <div class="ds-export-row">
              <button class="ds-btn-export">导出成绩</button>
            </div>

            <div class="ds-section-label"><span class="dot orange"></span>焊接器材</div>
            <div class="ds-device-grid">
              <div v-for="d in devices" :key="d.id"
                class="ds-device" :class="{ active: selectedDeviceId === d.id }"
                @click="selectedDeviceId = d.id">
                <div class="ds-dev-lights">
                  <span class="lt red" :class="{ on: d.status === 'error' }"></span>
                  <span class="lt yellow" :class="{ on: d.status === 'idle' }"></span>
                  <span class="lt green" :class="{ on: d.status === 'running' || d.students.length > 0 }"></span>
                </div>
                <div class="ds-dev-icon">
                  <svg viewBox="0 0 40 40" class="welder-svg"><rect x="4" y="8" width="32" height="22" rx="3" fill="#1a4a6e" stroke="#36d5ff" stroke-width="0.8"/><rect x="8" y="11" width="14" height="8" rx="1" fill="#0a2a44"/><circle cx="28" cy="15" r="2.5" fill="#00e5ff" opacity="0.8"/><rect x="8" y="22" width="24" height="3" rx="1" fill="#0e3654"/><line x1="20" y1="30" x2="20" y2="35" stroke="#36d5ff" stroke-width="0.8"/></svg>
                </div>
                <div class="ds-dev-code">{{ d.device_code }}</div>
              </div>
            </div>
          </main>

          <!-- RIGHT -->
          <aside class="ds-right">
            <div class="ds-chart-card" v-for="key in ['weldVoltage','arcVoltage','wireSpeed']" :key="key">
              <div class="ds-chart-title">
                {{ {weldVoltage:'焊接电压',arcVoltage:'电弧电压',wireSpeed:'送丝速度'}[key] }}
              </div>
              <div class="ds-chart-box" :ref="setChartRef(key)"></div>
            </div>
          </aside>
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
.lab-screen {
  height: calc(100vh - 90px);
  max-height: calc(100vh - 90px);
  background-color: #020a15;
  background-size: cover;
  background-position: center;
  border-radius: 12px;
  overflow: hidden;
  position: relative;
  box-shadow: inset 0 0 40px rgba(0,229,255,0.05);
}
.screen-mask {
  height: 100%;
  padding: 12px 18px;
  background: linear-gradient(180deg, rgba(2,10,21,0.85), rgba(2,15,30,0.95));
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* HEADER */
.ds-header { display: flex; align-items: center; justify-content: space-between; padding: 0 0 10px; border-bottom: 1px solid rgba(0,229,255,0.12); flex-shrink: 0; }
.ds-header-left { display: flex; flex-direction: column; }
.ds-time { font-size: 32px; font-weight: 800; color: #00e5ff; line-height: 1; font-family: 'Courier New', monospace; text-shadow: 0 0 15px rgba(0,229,255,0.6); }
.ds-date { font-size: 12px; color: rgba(255,255,255,0.5); margin-top: 2px; }
.ds-week { margin-left: 8px; color: rgba(0,229,255,0.6); }
.ds-title { font-size: clamp(20px, 2.5vw, 30px); font-weight: 800; color: #fff; text-align: center; letter-spacing: 4px; text-shadow: 0 0 25px rgba(0,229,255,0.4); margin: 0; }
.ds-header-right { display: flex; align-items: center; gap: 10px; }
.ds-user-name { color: rgba(255,255,255,0.8); font-size: 14px; }
.ds-btn-outline { background: transparent; border: 1px solid rgba(0,229,255,0.4); color: #00e5ff; padding: 6px 14px; border-radius: 4px; cursor: pointer; font-size: 12px; transition: all 0.3s; }
.ds-btn-outline:hover { background: rgba(0,229,255,0.1); border-color: #00e5ff; box-shadow: 0 0 10px rgba(0,229,255,0.3); }
.ds-btn-icon { display: flex; align-items: center; justify-content: center; padding: 6px; }

/* BODY 3-col */
.ds-body { display: grid; grid-template-columns: 0.8fr 1.2fr 1fr; gap: 16px; flex: 1; min-height: 0; padding-top: 14px; overflow: hidden; }

/* TECH PANELS */
.ds-panel, .ds-chart-card {
  position: relative;
  background: rgba(0, 20, 40, 0.45);
  border: 1px solid rgba(0, 229, 255, 0.15);
  border-radius: 4px; /* Harder corners for tech look */
  padding: 12px;
  box-shadow: inset 0 0 20px rgba(0, 229, 255, 0.05);
  backdrop-filter: blur(4px);
}
.ds-panel::before, .ds-panel::after, .ds-chart-card::before, .ds-chart-card::after {
  content: ''; position: absolute; width: 12px; height: 12px; border: 2px solid transparent; pointer-events: none;
}
.ds-panel::before, .ds-chart-card::before {
  top: -1px; left: -1px; border-top-color: #00e5ff; border-left-color: #00e5ff;
}
.ds-panel::after, .ds-chart-card::after {
  bottom: -1px; right: -1px; border-bottom-color: #00e5ff; border-right-color: #00e5ff;
}

/* LEFT */
.ds-left { display: flex; flex-direction: column; gap: 14px; overflow-y: auto; padding-right: 4px; }
.ds-panel-title { font-size: 13px; font-weight: 600; color: #d7f6ff; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; text-shadow: 0 0 8px rgba(0,229,255,0.4); }
.tech-dot { width: 4px; height: 14px; background: #00e5ff; display: inline-block; box-shadow: 0 0 8px #00e5ff; transform: skewX(-15deg); }
.tech-dot.green { background: #39ff14; box-shadow: 0 0 8px #39ff14; }
.tech-dot.orange { background: #fa8c16; box-shadow: 0 0 8px #fa8c16; }

.ds-run-info { display: flex; gap: 16px; margin-bottom: 8px; }
.ds-run-item { flex: 1; }
.ds-run-label { font-size: 11px; color: rgba(255,255,255,0.5); text-transform: uppercase; }
.ds-run-val { font-size: 14px; color: #00e5ff; margin-top: 4px; font-family: 'Courier New', monospace; }
.ds-run-val b { font-size: 26px; font-weight: 800; margin-right: 2px; text-shadow: 0 0 10px rgba(0,229,255,0.5); }
.ds-station { display: flex; align-items: center; justify-content: space-between; padding-top: 8px; border-top: 1px dashed rgba(0,229,255,0.2); }
.ds-station-label { font-size: 12px; color: rgba(255,255,255,0.5); }
.ds-station-val { font-size: 32px; font-weight: 800; color: #fff; font-family: 'Courier New', monospace; text-shadow: 0 0 15px rgba(255,255,255,0.4); }

.ds-student-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.ds-stu-chip { display: flex; align-items: center; gap: 8px; padding: 4px 14px 4px 4px; background: linear-gradient(90deg, rgba(0,229,255,0.1), rgba(0,229,255,0.02)); border: 1px solid rgba(0,229,255,0.2); border-radius: 4px; cursor: pointer; transition: all 0.3s; position: relative; overflow: hidden; }
.ds-stu-chip::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 2px; background: #00e5ff; }
.ds-stu-chip:hover { border-color: #00e5ff; box-shadow: 0 0 15px rgba(0,229,255,0.3); transform: translateX(2px); }
.ds-stu-avatar { flex-shrink: 0; border: 1px solid rgba(0,229,255,0.5); border-radius: 2px; }
.ds-stu-name { font-size: 13px; color: #fff; font-weight: 600; white-space: nowrap; }
.ds-stu-more { background: rgba(0,229,255,0.15); color: #00e5ff; padding: 6px 14px; font-size: 13px; font-weight: 800; border-radius: 4px; }

.ds-today-card { background: linear-gradient(135deg, rgba(0,229,255,0.08), rgba(0,100,200,0.02)); border: 1px solid rgba(0,229,255,0.1); border-radius: 4px; padding: 12px; position: relative; }
.ds-today-class { font-size: 15px; color: #00e5ff; font-weight: 700; text-shadow: 0 0 8px rgba(0,229,255,0.4); }
.ds-today-date { font-size: 12px; color: rgba(255,255,255,0.5); margin: 4px 0; font-family: 'Courier New', monospace; }
.ds-today-count { font-size: 13px; color: rgba(255,255,255,0.7); }

.ds-people { display: flex; gap: 14px; margin-top: auto; padding-top: 10px; }
.ds-person { flex: 1; text-align: center; background: rgba(0,20,40,0.3); border: 1px solid rgba(0,229,255,0.1); padding: 10px 0; border-radius: 4px; }
.ds-person-avatar { border: 2px solid rgba(0,229,255,0.4); box-shadow: 0 0 10px rgba(0,229,255,0.2); }
.ds-person-name { font-size: 14px; font-weight: 600; color: #fff; margin-top: 8px; }
.ds-person-role { font-size: 11px; color: #00e5ff; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px; }

/* CENTER */
.ds-center { display: flex; flex-direction: column; gap: 14px; overflow-y: auto; padding: 0 4px; }
.ds-gauges { display: flex; justify-content: center; align-items: center; gap: 24px; padding: 10px 0; }
.ds-gauge { position: relative; display: flex; align-items: center; justify-content: center; }
.ds-gauge svg { width: 120px; height: 120px; }
.ds-gauge.good svg { width: 140px; height: 140px; }
.gauge-bg { fill: none; stroke: rgba(0,229,255,0.05); stroke-width: 6; }
.gauge-ring { fill: none; stroke-width: 4; stroke-linecap: round; stroke-dasharray: 280 400; transform: rotate(-90deg); transform-origin: center; animation: pulseRing 3s infinite alternate ease-in-out; }
@keyframes pulseRing { 0% { opacity: 0.7; } 100% { opacity: 1; filter: drop-shadow(0 0 12px currentColor); } }
.ng-ring { stroke: #ff073a; color: #ff073a; }
.good-ring { stroke: #00e5ff; color: #00e5ff; stroke-dasharray: 330 400; }
.ai-ring { stroke: #39ff14; color: #39ff14; }

.gauge-inner { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.gauge-num { font-size: 32px; font-weight: 800; color: #fff; line-height: 1; font-family: 'Courier New', monospace; }
.gauge-num.lg { font-size: 38px; }
.ng .gauge-num { text-shadow: 0 0 15px rgba(255,7,58,0.6); }
.good .gauge-num { text-shadow: 0 0 15px rgba(0,229,255,0.6); }
.ai .gauge-num { text-shadow: 0 0 15px rgba(57,255,20,0.6); }
.gauge-label { font-size: 12px; color: rgba(255,255,255,0.6); margin-top: 6px; letter-spacing: 1px; font-weight: 600; }

.ds-export-row { text-align: center; margin: 10px 0; }
.ds-btn-export { background: linear-gradient(90deg, #0088a8, #00e5ff); color: #020a15; font-weight: 800; font-size: 15px; letter-spacing: 4px; padding: 10px 36px; border: none; cursor: pointer; clip-path: polygon(12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%, 0 12px); box-shadow: 0 0 20px rgba(0,229,255,0.3); transition: all 0.3s; text-transform: uppercase; }
.ds-btn-export:hover { filter: brightness(1.2); box-shadow: 0 0 30px rgba(0,229,255,0.6); transform: scale(1.02); }

.ds-section-label { font-size: 14px; font-weight: 600; color: #d7f6ff; display: flex; align-items: center; gap: 8px; margin: 6px 0; text-shadow: 0 0 8px rgba(0,229,255,0.4); }

.ds-device-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 12px; flex: 1; min-height: 0; overflow-y: auto; align-content: start; padding-right: 4px; }
.ds-device { background: rgba(0,20,40,0.6); border: 1px solid rgba(0,229,255,0.15); border-radius: 6px; padding: 10px; cursor: pointer; transition: all 0.3s; text-align: center; position: relative; box-shadow: inset 0 0 10px rgba(0,229,255,0.05); }
.ds-device:hover { border-color: rgba(0,229,255,0.5); background: rgba(0,30,60,0.7); box-shadow: 0 0 15px rgba(0,229,255,0.2), inset 0 0 15px rgba(0,229,255,0.1); transform: translateY(-2px); }
.ds-device.active { border-color: #00e5ff; box-shadow: 0 0 20px rgba(0,229,255,0.4), inset 0 0 20px rgba(0,229,255,0.2); }
.ds-device.active::after { content: ''; position: absolute; inset: -4px; border: 1px solid #00e5ff; border-radius: 8px; opacity: 0.4; pointer-events: none; }

.ds-dev-lights { display: flex; justify-content: center; gap: 6px; margin-bottom: 8px; }
.lt { width: 8px; height: 8px; border-radius: 50%; opacity: 0.2; }
.lt.red { background: #ff073a; }
.lt.yellow { background: #fadb14; }
.lt.green { background: #39ff14; }
.lt.on { opacity: 1; box-shadow: 0 0 10px currentColor, inset 0 0 4px #fff; }

.ds-dev-icon { height: 50px; display: flex; align-items: center; justify-content: center; filter: drop-shadow(0 0 6px rgba(0,229,255,0.2)); }
.welder-svg { width: 50px; height: 50px; }
.ds-dev-code { font-size: 11px; color: rgba(255,255,255,0.7); margin-top: 6px; font-family: 'Courier New', monospace; letter-spacing: 1px; }

/* RIGHT */
.ds-right { display: flex; flex-direction: column; gap: 14px; overflow-y: auto; }
.ds-chart-card { display: flex; flex-direction: column; flex: 1; min-height: 0; padding: 10px 12px; }
.ds-chart-title { font-size: 13px; font-weight: 600; color: #d7f6ff; margin-bottom: 6px; display: flex; align-items: center; gap: 8px; text-shadow: 0 0 8px rgba(0,229,255,0.4); }
.ds-chart-box { flex: 1; min-height: 120px; }

.empty-state { flex: 1; display: grid; place-items: center; color: rgba(0,229,255,0.4); font-size: 24px; letter-spacing: 2px; }

@media(max-width:1300px) {
  .ds-body { grid-template-columns: 240px 1fr 280px; }
}
@media(max-width:1100px) {
  .ds-body { grid-template-columns: 1fr; grid-template-rows: auto 1fr auto; }
  .ds-left { flex-direction: row; flex-wrap: wrap; overflow-x: auto; }
  .ds-panel { min-width: 220px; flex: 1; }
}
</style>
