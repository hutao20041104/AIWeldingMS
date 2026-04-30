<script setup lang="ts">
import { computed, onMounted, ref, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Clock, Location, EditPen, Close, Tickets } from '@element-plus/icons-vue'
import { API_BASE_URL } from '../../composables/useAuth'
import { HolidayUtil, Lunar } from 'lunar-javascript'

type CourseRow = {
  id: number
  course_code: string
  classroom: string
  class_display: string
  status: 'not_started' | 'in_progress' | 'ended'
  status_label: string
  start_time: string
  end_time: string
  created_at: string
  student_count: number
}

type StudentOption = {
  id: string
  identity_code: string
  username: string
  major: string
  major_code: string
  class_code: string
  class_name: string
}

type DeviceOption = {
  id: number
  device_code: string
  status: string
  status_label: string
}

type ClassroomOption = {
  classroom: string
  devices: DeviceOption[]
}

type MajorOption = { name: string; code: string }
type ClassOption = { name: string; code: string; major_code: string }

const activeTab = ref('course-list')
const loading = ref(false)
const saving = ref(false)
const studentsLoading = ref(false)

const keyword = ref('')
const tableData = ref<CourseRow[]>([])
const currentPage = ref(1)
const pageSize = 10

const dialogVisible = ref(false)
const editingCourseId = ref<number | null>(null)
const autoCourseCode = ref('')
const allStudents = ref<StudentOption[]>([])
const majors = ref<MajorOption[]>([])
const classes = ref<ClassOption[]>([])
const classrooms = ref<ClassroomOption[]>([])

const studentFilters = ref({
  major_code: '',
  class_code: '',
  name: '',
})

const form = ref({
  classroom: '',
  start_time: '',
  end_time: '',
  student_ids: [] as string[],
  assistant_student_id: '' as string,
})

const groupingDialogVisible = ref(false)
const groupingLoading = ref(false)
const groupingSaving = ref(false)
const groupingCourseId = ref<number | null>(null)
const groupingCourseCode = ref('')
const groupingCourseStatus = ref('')
const groupingStudents = ref<Array<{ id: string; identity_code: string; username: string; major: string; class_name: string; device_id?: number | null }>>([])
const groupingDevices = ref<DeviceOption[]>([])

function authHeaders() {
  const token = localStorage.getItem('access_token')
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

const filteredTableData = computed(() => {
  const key = keyword.value.trim().toLowerCase()
  if (!key) return tableData.value
  return tableData.value.filter((item) => {
    return (
      item.course_code.toLowerCase().includes(key) ||
      item.classroom.toLowerCase().includes(key) ||
      item.class_display.toLowerCase().includes(key)
    )
  })
})

const coursesByDate = computed(() => {
  const map: Record<string, CourseRow[]> = {}
  tableData.value.forEach(course => {
    if (!course.start_time) return
    const dateObj = new Date(course.start_time)
    if (Number.isNaN(dateObj.getTime())) return
    const pad = (n: number) => `${n}`.padStart(2, '0')
    const dateKey = `${dateObj.getFullYear()}-${pad(dateObj.getMonth() + 1)}-${pad(dateObj.getDate())}`
    if (!map[dateKey]) map[dateKey] = []
    map[dateKey].push(course)
  })
  
  // 按照开始时间对每天的课程进行排序
  for (const dateKey in map) {
    map[dateKey].sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())
  }
  
  return map
})

const pagedTableData = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredTableData.value.slice(start, start + pageSize)
})

const filteredStudents = computed(() => {
  return allStudents.value.filter((item) => {
    if (studentFilters.value.major_code && item.major_code !== studentFilters.value.major_code) return false
    if (studentFilters.value.class_code && item.class_code !== studentFilters.value.class_code) return false
    const name = studentFilters.value.name.trim().toLowerCase()
    if (name && !item.username.toLowerCase().includes(name)) return false
    return true
  })
})

const selectedClassroomDevices = computed(() => {
  return classrooms.value.find((c) => c.classroom === form.value.classroom)?.devices ?? []
})

const selectedClassroomDevicesPairs = computed(() => {
  const devices = selectedClassroomDevices.value
  const pairs = []
  for (let i = 0; i < devices.length; i += 2) {
    pairs.push({
      dev1: devices[i],
      dev2: devices[i + 1] || null
    })
  }
  return pairs
})

function formatTime(value?: string) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n: number) => `${n}`.padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function formatShortTime(value?: string) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (n: number) => `${n}`.padStart(2, '0')
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function toDatetimeLocal(value?: string) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (n: number) => `${n}`.padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

const startTimePickerRef = ref()
const endTimePickerRef = ref()
const calendarRef = ref()

const startDate = computed({
  get: () => form.value.start_time ? form.value.start_time.split('T')[0] : '',
  set: (val: string) => {
    const time = form.value.start_time ? form.value.start_time.split('T')[1] : '00:00:00'
    form.value.start_time = val ? `${val}T${time}` : ''
    if (val) {
      nextTick(() => {
        startTimePickerRef.value?.focus()
      })
    }
  }
})

const startTimeOnly = computed({
  get: () => form.value.start_time ? form.value.start_time.split('T')[1] : '',
  set: (val: string) => {
    const date = form.value.start_time ? form.value.start_time.split('T')[0] : new Date().toISOString().split('T')[0]
    form.value.start_time = `${date}T${val || '00:00:00'}`
    handleStartTimeChange(form.value.start_time)
  }
})

const endDate = computed({
  get: () => form.value.end_time ? form.value.end_time.split('T')[0] : '',
  set: (val: string) => {
    const time = form.value.end_time ? form.value.end_time.split('T')[1] : '00:00:00'
    form.value.end_time = val ? `${val}T${time}` : ''
    if (val) {
      nextTick(() => {
        endTimePickerRef.value?.focus()
      })
    }
  }
})

const endTimeOnly = computed({
  get: () => form.value.end_time ? form.value.end_time.split('T')[1] : '',
  set: (val: string) => {
    const date = form.value.end_time ? form.value.end_time.split('T')[0] : new Date().toISOString().split('T')[0]
    form.value.end_time = `${date}T${val || '00:00:00'}`
  }
})

function handleStartTimeChange(value: string | null) {
  if (value) {
    const startDate = new Date(value)
    if (!Number.isNaN(startDate.getTime())) {
      const endDate = new Date(startDate.getTime() + 90 * 60000)
      const pad = (n: number) => `${n}`.padStart(2, '0')
      form.value.end_time = `${endDate.getFullYear()}-${pad(endDate.getMonth() + 1)}-${pad(endDate.getDate())}T${pad(endDate.getHours())}:${pad(endDate.getMinutes())}:00`
    }
  }
}

async function fetchCourses() {
  loading.value = true
  try {
    const res = await fetch(`${API_BASE_URL}/api/courses/`, { headers: { ...authHeaders() } })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '获取课程失败')
      return
    }
    tableData.value = data
    currentPage.value = 1
  } catch {
    ElMessage.error('网络异常，获取课程失败')
  } finally {
    loading.value = false
  }
}

async function openGroupingDialog(row: CourseRow) {
  groupingCourseId.value = row.id
  groupingCourseCode.value = row.course_code
  groupingCourseStatus.value = row.status
  groupingDialogVisible.value = true
  await fetchGroupingDetail()
}

async function fetchGroupingDetail() {
  if (!groupingCourseId.value) return
  groupingLoading.value = true
  try {
    const res = await fetch(`${API_BASE_URL}/api/courses/${groupingCourseId.value}/grouping/`, {
      headers: { ...authHeaders() },
    })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '获取分组信息失败')
      return
    }
    groupingStudents.value = data.students || []
    groupingDevices.value = data.devices || []
  } catch {
    ElMessage.error('网络异常，获取分组信息失败')
  } finally {
    groupingLoading.value = false
  }
}

async function runRandomGrouping() {
  if (!groupingCourseId.value) return
  groupingSaving.value = true
  try {
    const res = await fetch(`${API_BASE_URL}/api/courses/${groupingCourseId.value}/grouping/random/`, {
      method: 'POST',
      headers: { ...authHeaders() },
    })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '随机分组失败')
      return
    }
    ElMessage.success('随机分组成功')
    await fetchGroupingDetail()
  } catch {
    ElMessage.error('网络异常，随机分组失败')
  } finally {
    groupingSaving.value = false
  }
}

async function saveGrouping() {
  if (!groupingCourseId.value) return
  groupingSaving.value = true
  try {
    const assignments = groupingStudents.value
      .filter((s) => s.device_id)
      .map((s) => ({ student_id: s.id, device_id: Number(s.device_id) }))
    const res = await fetch(`${API_BASE_URL}/api/courses/${groupingCourseId.value}/grouping/`, {
      method: 'PUT',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ assignments }),
    })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '保存分组失败')
      return
    }
    ElMessage.success('分组保存成功')
    groupingDialogVisible.value = false
  } catch {
    ElMessage.error('网络异常，保存分组失败')
  } finally {
    groupingSaving.value = false
  }
}

async function fetchOptions() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/courses/options/`, { headers: { ...authHeaders() } })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '获取课程配置失败')
      return
    }
    majors.value = data.majors || []
    classes.value = data.classes || []
    classrooms.value = data.classrooms || []
  } catch {
    ElMessage.error('网络异常，获取课程配置失败')
  }
}

async function fetchStudents() {
  studentsLoading.value = true
  try {
    const params = new URLSearchParams()
    if (studentFilters.value.major_code) params.set('major_code', studentFilters.value.major_code)
    if (studentFilters.value.class_code) params.set('class_code', studentFilters.value.class_code)
    if (studentFilters.value.name.trim()) params.set('name', studentFilters.value.name.trim())
    const suffix = params.toString() ? `?${params.toString()}` : ''
    const res = await fetch(`${API_BASE_URL}/api/courses/students/${suffix}`, { headers: { ...authHeaders() } })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '获取学生列表失败')
      return
    }
    allStudents.value = data
  } catch {
    ElMessage.error('网络异常，获取学生列表失败')
  } finally {
    studentsLoading.value = false
  }
}

async function fetchNextCourseCode() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/courses/next-code/`, { headers: { ...authHeaders() } })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '获取课程编号失败')
      return
    }
    autoCourseCode.value = data.course_code || ''
  } catch {
    ElMessage.error('网络异常，获取课程编号失败')
  }
}

function addFilteredStudents() {
  const merged = new Set(form.value.student_ids)
  filteredStudents.value.forEach((item) => merged.add(item.id))
  form.value.student_ids = Array.from(merged)
  ElMessage.success(`已批量添加 ${filteredStudents.value.length} 名学生`)
}

function clearFilteredStudents() {
  const current = new Set(filteredStudents.value.map((item) => item.id))
  form.value.student_ids = form.value.student_ids.filter((id) => !current.has(id))
}

function openCreateDialog() {
  editingCourseId.value = null
  autoCourseCode.value = ''
  form.value = {
    classroom: '',
    start_time: '',
    end_time: '',
    student_ids: [],
    assistant_student_id: '',
  }
  studentFilters.value = { major_code: '', class_code: '', name: '' }
  fetchNextCourseCode()
  fetchStudents()
  dialogVisible.value = true
}

async function openEditDialog(row: CourseRow) {
  if (row.status !== 'not_started') {
    ElMessage.warning('仅未开始课程可编辑')
    return
  }
  editingCourseId.value = row.id
  autoCourseCode.value = row.course_code
  try {
    const res = await fetch(`${API_BASE_URL}/api/courses/${row.id}/`, { headers: { ...authHeaders() } })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '获取课程详情失败')
      return
    }
    form.value = {
      classroom: data.classroom || '',
      start_time: toDatetimeLocal(data.start_time),
      end_time: toDatetimeLocal(data.end_time),
      student_ids: data.student_ids || [],
      assistant_student_id: data.assistant_student_id || '',
    }
    studentFilters.value = { major_code: '', class_code: '', name: '' }
    await fetchStudents()
    dialogVisible.value = true
  } catch {
    ElMessage.error('网络异常，获取课程详情失败')
  }
}

async function handleDelete(row: CourseRow) {
  if (row.status === 'ended') {
    ElMessage.warning('已结束课程不可删除')
    return
  }
  try {
    await ElMessageBox.confirm(`确认删除课程 ${row.course_code} 吗？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    const res = await fetch(`${API_BASE_URL}/api/courses/${row.id}/`, {
      method: 'DELETE',
      headers: { ...authHeaders() },
    })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '删除失败')
      return
    }
    ElMessage.success('删除成功')
    fetchCourses()
  } catch {
    ElMessage.error('网络异常，删除失败')
  }
}

async function saveCourse() {
  if (!form.value.classroom) {
    ElMessage.warning('请选择教室')
    return
  }
  if (!form.value.start_time || !form.value.end_time) {
    ElMessage.warning('请选择授课开始与结束时间')
    return
  }
  if (form.value.student_ids.length === 0) {
    ElMessage.warning('请至少选择一名学生')
    return
  }

  saving.value = true
  try {
    const payload = {
      classroom: form.value.classroom,
      start_time: new Date(form.value.start_time).toISOString(),
      end_time: new Date(form.value.end_time).toISOString(),
      student_ids: form.value.student_ids,
      assistant_student_id: form.value.assistant_student_id || null,
    }
    const isEdit = editingCourseId.value !== null
    const res = await fetch(
      isEdit ? `${API_BASE_URL}/api/courses/${editingCourseId.value}/` : `${API_BASE_URL}/api/courses/`,
      {
        method: isEdit ? 'PUT' : 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
    )
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '保存失败')
      return
    }
    ElMessage.success(isEdit ? '课程更新成功' : '课程创建成功')
    dialogVisible.value = false
    fetchCourses()
  } catch {
    ElMessage.error('网络异常，保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await Promise.all([fetchOptions(), fetchCourses(), fetchCalendarOverrides()])
})

const calendarOverrides = ref<Record<string, { day_type: string, note: string }>>({})
const noteDialogVisible = ref(false)
const currentNoteDate = ref('')
const currentNoteText = ref('')
const dialogTop = ref(0)
const dialogLeft = ref(0)

async function fetchCalendarOverrides() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/courses/calendar/overrides/`, { headers: { ...authHeaders() } })
    const data = await res.json()
    if (res.ok) {
      const overrides: Record<string, { day_type: string, note: string }> = {}
      data.forEach((item: any) => {
        overrides[item.date] = { day_type: item.day_type, note: item.note || '' }
      })
      calendarOverrides.value = overrides
    }
  } catch (e) {
    console.error('Failed to fetch overrides', e)
  }
}

async function handleOverrideChange(dateString: string, dayType: string, note?: string) {
  const parts = dateString.split('-')
  const y = parseInt(parts[0])
  const m = parseInt(parts[1])
  const d = parseInt(parts[2])
  const standardizedDate = `${y}-${m.toString().padStart(2, '0')}-${d.toString().padStart(2, '0')}`
  
  const currentOverride = calendarOverrides.value[standardizedDate] || { day_type: 'default', note: '' }
  const finalDayType = dayType || currentOverride.day_type
  const finalNote = note !== undefined ? note : currentOverride.note

  try {
    const res = await fetch(`${API_BASE_URL}/api/courses/calendar/overrides/`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ date: standardizedDate, day_type: finalDayType, note: finalNote })
    })
    if (res.ok) {
      if (finalDayType === 'default' && !finalNote) {
        delete calendarOverrides.value[standardizedDate]
      } else {
        calendarOverrides.value[standardizedDate] = { day_type: finalDayType, note: finalNote }
      }
      ElMessage.success('设置成功')
    } else {
      ElMessage.error('设置失败')
    }
  } catch (e) {
    ElMessage.error('网络异常，设置失败')
  }
}

function openNoteDialog(dateString: string, event: MouseEvent) {
  const parts = dateString.split('-')
  const y = parseInt(parts[0])
  const m = parseInt(parts[1])
  const d = parseInt(parts[2])
  const standardizedDate = `${y}-${m.toString().padStart(2, '0')}-${d.toString().padStart(2, '0')}`
  
  currentNoteDate.value = standardizedDate
  currentNoteText.value = calendarOverrides.value[standardizedDate]?.note || ''
  
  if (event) {
    let x = event.clientX + 10
    let y = event.clientY + 10
    if (x + 340 > window.innerWidth) x = event.clientX - 330
    if (y + 240 > window.innerHeight) y = event.clientY - 230
    dialogLeft.value = x
    dialogTop.value = y
  } else {
    dialogLeft.value = window.innerWidth / 2 - 160
    dialogTop.value = window.innerHeight / 2 - 100
  }
  
  noteDialogVisible.value = true
}

async function saveNote() {
  await handleOverrideChange(currentNoteDate.value, '', currentNoteText.value)
  noteDialogVisible.value = false
}

function getDayInfo(dateString: string) {
  const parts = dateString.split('-')
  const y = parseInt(parts[0])
  const m = parseInt(parts[1])
  const d = parseInt(parts[2])
  const standardizedDate = `${y}-${m.toString().padStart(2, '0')}-${d.toString().padStart(2, '0')}`
  
  const holiday = HolidayUtil.getHoliday(y, m, d)
  const dateObj = new Date(y, m - 1, d)
  
  let defaultType = 'work'
  let holidayName = ''
  let isWeekend = false
  
  if (holiday) {
    defaultType = holiday.isWork() ? 'work' : 'rest'
    holidayName = holiday.getName()
  } else {
    const dayOfWeek = dateObj.getDay()
    if (dayOfWeek === 0 || dayOfWeek === 6) {
      defaultType = 'rest'
      isWeekend = true
    } else {
      const lunar = Lunar.fromDate(dateObj)
      const festivals = lunar.getFestivals()
      if (festivals.length > 0) {
         holidayName = festivals[0]
      }
    }
  }
  
  const overrideData = calendarOverrides.value[standardizedDate]
  const finalType = (overrideData && overrideData.day_type !== 'default') ? overrideData.day_type : defaultType
  
  return {
    isRest: finalType === 'rest',
    holidayName,
    hasOverride: !!overrideData && overrideData.day_type !== 'default',
    isWeekend,
    note: overrideData?.note || ''
  }
}
</script>

<template>
  <section class="course-management-page">
    <el-card class="glass-card module-table-card" shadow="never" v-loading="loading">
      <el-tabs v-model="activeTab" class="custom-tabs">
        <!-- 列表视图 -->
        <el-tab-pane label="课程列表" name="course-list">

      <div class="module-toolbar">
        <div class="section-title-wrap">
          <div class="title-icon-box">
            <el-icon><Tickets /></el-icon>
          </div>
          <h2 class="section-title">课程列表详情</h2>
        </div>
        <div class="toolbar-actions">
          <el-input v-model="keyword" placeholder="搜索课程编号/地点/班级(专业)" clearable class="module-search" :prefix-icon="Search" />
          <el-button type="primary" class="gradient-btn" @click="openCreateDialog">添加课程</el-button>
        </div>
      </div>
      <div class="module-table-wrap">
        <el-table :data="pagedTableData" border v-loading="loading" class="custom-table" header-cell-class-name="custom-table-header">
          <el-table-column prop="course_code" label="课程编号" min-width="180" align="center" />
          <el-table-column prop="classroom" label="地点" min-width="120" align="center" />
          <el-table-column prop="class_display" label="班级(专业)" min-width="200" align="center" />
          <el-table-column prop="status_label" label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.status === 'in_progress' ? 'success' : row.status === 'not_started' ? 'info' : 'warning'" effect="light">
                {{ row.status_label }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="人数" width="80" align="center">
            <template #default="{ row }">
              <span class="number-cell">{{ row.student_count }}</span>
            </template>
          </el-table-column>
          <el-table-column label="上课时间" min-width="300" align="center">
            <template #default="{ row }">
              <div class="time-cell">
                <span class="time-label">{{ formatTime(row.start_time) }}</span>
                <span class="time-divider">至</span>
                <span class="time-label">{{ formatShortTime(row.end_time) }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right" align="center">
            <template #default="{ row }">
              <el-button link type="primary" :disabled="row.status !== 'not_started'" @click="openEditDialog(row)">编辑</el-button>
              <el-button link type="primary" @click="openGroupingDialog(row)">设备分配</el-button>
              <el-button link type="danger" :disabled="row.status === 'ended'" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div class="module-pagination">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          layout="total, prev, pager, next"
          :total="filteredTableData.length"
          background
        />
      </div>
    
        </el-tab-pane>

        <!-- 日历视图 -->
        <el-tab-pane label="教学日历" name="course-calendar">
          <div class="calendar-wrapper">
            <el-calendar ref="calendarRef">
              <template #header="{ date }">
                <div style="display: flex; align-items: center; justify-content: center; width: 100%; position: relative;">
                  <el-button type="text" @click="calendarRef?.selectDate('prev-month')" style="font-size: 18px; padding: 4px 8px; color: #606266;">&lt;</el-button>
                  <span style="font-size: 16px; font-weight: 600; margin: 0 24px; color: #303133;">{{ date }}</span>
                  <el-button type="text" @click="calendarRef?.selectDate('next-month')" style="font-size: 18px; padding: 4px 8px; color: #606266;">&gt;</el-button>
                  <el-button type="primary" plain size="small" @click="calendarRef?.selectDate('today')" style="position: absolute; right: 0;">今天</el-button>
                </div>
              </template>

              <template #date-cell="{ data }">
                <div class="calendar-cell" :class="{ 'is-other-month': data.type !== 'current-month' }" @dblclick="openNoteDialog(data.day, $event)">
                  <div class="date-header-wrap">
                    <span class="date-num" :class="{ 'is-today': data.type === 'today' || data.day === new Date().toISOString().split('T')[0] }">{{ data.day.split('-').pop() }}</span>
                    <div class="date-info-wrap">
                      <span v-if="getDayInfo(data.day).holidayName" class="holiday-name">{{ getDayInfo(data.day).holidayName }}</span>
                      
                      <el-dropdown trigger="click" @command="(cmd: string) => handleOverrideChange(data.day, cmd)">
                        <span class="day-badge" :class="[getDayInfo(data.day).isRest ? 'is-rest' : 'is-work', { 'has-override': getDayInfo(data.day).hasOverride }]">
                          {{ getDayInfo(data.day).isRest ? '休' : '班' }}
                        </span>
                        <template #dropdown>
                          <el-dropdown-menu>
                            <el-dropdown-item command="rest">设为休息(休)</el-dropdown-item>
                            <el-dropdown-item command="work">设为工作(班)</el-dropdown-item>
                            <el-dropdown-item command="default" divided>恢复默认设置</el-dropdown-item>
                          </el-dropdown-menu>
                        </template>
                      </el-dropdown>
                    </div>
                  </div>
                  <div class="course-list">
              <template v-if="coursesByDate[data.day]">
                <el-popover
                  placement="right"
                  :width="280"
                  trigger="hover"
                >
                  <template #reference>
                    <div class="course-badge" :class="coursesByDate[data.day][0].status" style="cursor: pointer;">
                      <span class="c-time">{{ formatShortTime(coursesByDate[data.day][0].start_time) }}</span>
                      <span class="c-name">{{ coursesByDate[data.day][0].class_display.split('-')[0] || coursesByDate[data.day][0].class_display }}</span>
                    </div>
                  </template>

                  <div class="popover-course-list">
                    <div class="popover-course-header">
                      <span>{{ data.day }} 课程安排</span>
                      <span class="course-count">共 {{ coursesByDate[data.day].length }} 节</span>
                    </div>
                    <div 
                      v-for="course in coursesByDate[data.day]" 
                      :key="course.id"
                      class="popover-course-item"
                    >
                      <div class="course-status-dot" :class="course.status"></div>
                      <div class="course-details">
                        <div class="course-name">{{ course.class_display }}</div>
                        <div class="course-time-room">
                          <span><el-icon><Clock /></el-icon>{{ formatShortTime(course.start_time) }} - {{ formatShortTime(course.end_time) }}</span>
                          <span style="margin-left: 12px;"><el-icon><Location /></el-icon>{{ course.classroom }}</span>
                        </div>
                      </div>
                    </div>
                    <div v-if="getDayInfo(data.day).note" class="popover-note">
                      <el-icon><EditPen /></el-icon> {{ getDayInfo(data.day).note }}
                    </div>
                  </div>
                </el-popover>
              </template>
              <template v-else-if="getDayInfo(data.day).note">
                <div class="cell-note" :title="getDayInfo(data.day).note">
                  <span class="note-text">{{ getDayInfo(data.day).note }}</span>
                </div>
              </template>
            </div>
          </div>
        </template>
      
            </el-calendar>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <div v-if="noteDialogVisible" class="floating-note-dialog glass-card" :style="{ top: dialogTop + 'px', left: dialogLeft + 'px' }">
      <div class="dialog-header-custom" style="margin-bottom: 12px; font-size: 16px;">
        <el-icon><EditPen /></el-icon>
        <span>为 {{ currentNoteDate }} 备注</span>
        <el-button link type="info" style="margin-left: auto; font-size: 18px;" @click="noteDialogVisible = false">
           <el-icon><Close /></el-icon>
        </el-button>
      </div>
      <div class="note-input-wrap" style="margin-top: 0;">
        <el-input 
          v-model="currentNoteText" 
          type="textarea" 
          :rows="4" 
          placeholder="按 Enter 快速保存，Shift+Enter 换行" 
          @keydown.enter.exact.prevent="saveNote"
          resize="none"
        />
      </div>
      <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px;">
        <el-button size="small" @click="noteDialogVisible = false" round>取消</el-button>
        <el-button size="small" type="primary" class="gradient-btn" @click="saveNote" round>保存备注</el-button>
      </div>
    </div>

    <el-dialog v-model="dialogVisible" :title="editingCourseId ? '编辑课程' : '添加课程'" width="980px" class="custom-glass-dialog" top="12vh">
      <el-form label-width="120px">
        <el-form-item label="课程编号">
          <el-input :model-value="autoCourseCode || '加载中...'" disabled />
        </el-form-item>

        <el-form-item label="添加学生">
          <div class="student-panel-scroll" style="width: 100%">
            <div class="student-filter-sticky" style="display: flex; gap: 12px; margin-bottom: 12px">
              <el-select v-model="studentFilters.major_code" clearable placeholder="按专业过滤" style="width: 180px">
                <el-option v-for="item in majors" :key="item.code" :label="`${item.name}(${item.code})`" :value="item.code" />
              </el-select>
              <el-select v-model="studentFilters.class_code" clearable placeholder="按班级过滤" style="width: 180px">
                <el-option v-for="item in classes" :key="item.code" :label="`${item.name}(${item.code})`" :value="item.code" />
              </el-select>
              <el-input v-model="studentFilters.name" clearable placeholder="按姓名过滤" style="width: 180px" />
              <el-button @click="fetchStudents">查询学生</el-button>
              <el-button type="primary" plain @click="addFilteredStudents">批量添加筛选结果</el-button>
              <el-button @click="clearFilteredStudents">批量移除筛选结果</el-button>
            </div>
            <el-table
              :data="filteredStudents"
              border
              height="200"
              v-loading="studentsLoading"
            >
              <el-table-column width="100" align="center">
                <template #header>
                  <span>选择 ({{ form.student_ids.length }})</span>
                </template>
                <template #default="{ row }">
                  <el-checkbox
                    size="large"
                    :model-value="form.student_ids.includes(row.id)"
                    @change="
                      (checked: boolean) => {
                        if (checked) {
                          if (!form.student_ids.includes(row.id)) form.student_ids.push(row.id)
                        } else {
                          form.student_ids = form.student_ids.filter((id) => id !== row.id)
                        }
                      }
                    "
                  />
                </template>
              </el-table-column>
              <el-table-column prop="identity_code" label="学号" min-width="120" />
              <el-table-column prop="username" label="姓名" min-width="120" />
              <el-table-column prop="major" label="专业" min-width="140" />
              <el-table-column prop="class_name" label="班级" min-width="140" />
            </el-table>
          </div>
        </el-form-item>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="授课地点">
              <el-select v-model="form.classroom" filterable placeholder="请选择教室" style="width: 100%">
                <el-option v-for="item in classrooms" :key="item.classroom" :label="item.classroom" :value="item.classroom" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="助教学生">
              <el-select v-model="form.assistant_student_id" clearable placeholder="可选：从已选学生指定助教" style="width: 100%">
                <template #empty>
                  <p class="el-select-dropdown__empty">请先添加学生</p>
                </template>
                <el-option
                  v-for="item in allStudents.filter((s) => form.student_ids.includes(s.id))"
                  :key="item.id"
                  :label="`${item.username} (${item.identity_code})`"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="设备展示">
          <el-table :data="selectedClassroomDevicesPairs" border height="136" style="width: 100%">
            <template #empty>
              <span style="color: #909399;">{{ form.classroom ? '该教室暂无设备' : '请先选择教室' }}</span>
            </template>
            <el-table-column label="设备编号" min-width="140">
              <template #default="{ row }">{{ row.dev1?.device_code }}</template>
            </el-table-column>
            <el-table-column label="状态" min-width="100">
              <template #default="{ row }">
                <el-tag v-if="row.dev1" :type="row.dev1.status === 'in_use' ? 'success' : row.dev1.status === 'idle' ? 'info' : 'warning'" effect="light">
                  {{ row.dev1.status_label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="设备编号" min-width="140">
              <template #default="{ row }">{{ row.dev2?.device_code }}</template>
            </el-table-column>
            <el-table-column label="状态" min-width="100">
              <template #default="{ row }">
                <el-tag v-if="row.dev2" :type="row.dev2.status === 'in_use' ? 'success' : row.dev2.status === 'idle' ? 'info' : 'warning'" effect="light">
                  {{ row.dev2.status_label }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-form-item>

        <el-form-item label="授课时间" style="margin-bottom: 22px;">
          <div style="display: flex; align-items: center;">
            <div style="display: flex; gap: 8px; margin-right: 16px">
              <el-date-picker
                v-model="startDate"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始日期"
                style="width: 140px"
              />
              <el-time-picker
                ref="startTimePickerRef"
                v-model="startTimeOnly"
                value-format="HH:mm:ss"
                format="HH:mm"
                placeholder="时间"
                style="width: 100px"
              />
            </div>
            <span style="margin-right: 16px; color: #909399;">至</span>
            <div style="display: flex; gap: 8px;">
              <el-date-picker
                v-model="endDate"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束日期"
                style="width: 140px"
              />
              <el-time-picker
                ref="endTimePickerRef"
                v-model="endTimeOnly"
                value-format="HH:mm:ss"
                format="HH:mm"
                placeholder="时间"
                style="width: 100px"
              />
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveCourse">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="groupingDialogVisible" title="课程分组" width="960px" class="custom-glass-dialog" top="12vh">
      <div style="margin-bottom: 12px">课程编号：{{ groupingCourseCode }}</div>
      <div style="margin-bottom: 12px" v-if="groupingCourseStatus !== 'ended'">
        <el-button type="primary" :loading="groupingSaving" @click="runRandomGrouping">随机分组</el-button>
      </div>
      <el-table :data="groupingStudents" border v-loading="groupingLoading">
        <el-table-column prop="identity_code" label="学号" min-width="120" />
        <el-table-column prop="username" label="姓名" min-width="120" />
        <el-table-column prop="major" label="专业" min-width="140" />
        <el-table-column prop="class_name" label="班级" min-width="140" />
        <el-table-column label="分配设备" min-width="220">
          <template #default="{ row }">
            <el-select v-model="row.device_id" placeholder="选择设备" style="width: 200px" :disabled="groupingCourseStatus === 'ended'">
              <el-option v-for="d in groupingDevices" :key="d.id" :label="`${d.device_code}(${d.status_label})`" :value="d.id" />
            </el-select>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="groupingDialogVisible = false">{{ groupingCourseStatus === 'ended' ? '关闭' : '取消' }}</el-button>
        <el-button v-if="groupingCourseStatus !== 'ended'" type="primary" :loading="groupingSaving" @click="saveGrouping">保存分组</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.course-management-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  height: calc(100vh - 80px);
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
.glass-card:hover {
  box-shadow: 0 12px 40px rgba(31, 38, 135, 0.1);
}

:deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px 20px;
}

:deep(.custom-tabs) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
:deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
}
:deep(.el-tab-pane) {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.calendar-wrapper {
  flex: 1;
  overflow-y: auto;
  padding: 12px 20px;
}

:deep(.el-calendar) {
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 
    0 10px 25px rgba(0,0,0,0.06),
    0 4px 10px rgba(0,0,0,0.04),
    inset 0 -4px 0 rgba(0,0,0,0.02);
  position: relative;
  overflow: visible;
  margin-top: 12px;
}

/* Simulate physical metal ring binders */
:deep(.el-calendar::before) {
  content: '';
  position: absolute;
  top: -10px;
  left: 40px;
  right: 40px;
  height: 20px;
  background: repeating-linear-gradient(
    to right,
    transparent,
    transparent 14px,
    #909399 14px,
    #909399 20px,
    transparent 20px,
    transparent 36px
  );
  z-index: 10;
  opacity: 0.8;
  filter: drop-shadow(0 2px 2px rgba(0,0,0,0.2));
  pointer-events: none;
}

:deep(.el-calendar__header) {
  background: #fdf5f5;
  border-top: 8px solid #f56c6c;
  border-radius: 12px 12px 0 0;
  border-bottom: 1px dashed rgba(0, 0, 0, 0.08);
  padding: 12px 16px;
}

:deep(.el-calendar__body) {
  padding-bottom: 12px;
}

:deep(.el-calendar-table .el-calendar-day) {
  height: 64px;
  padding: 4px;
  border: none;
  background: transparent;
  transition: all 0.2s ease;
}
:deep(.el-calendar-table td) {
  border-right: 1px dashed rgba(0, 0, 0, 0.05);
  border-bottom: 1px dashed rgba(0, 0, 0, 0.05);
}
:deep(.el-calendar-table .el-calendar-day:hover) {
  background: rgba(245, 247, 250, 0.6);
}

.calendar-cell {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.date-num {
  font-size: 14px;
  font-weight: 500;
  color: #606266;
  display: inline-block;
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}
.date-num.is-today {
  color: #409eff;
  font-weight: bold;
  background: #e6f1fc;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  text-align: center;
  line-height: 24px;
}

.course-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.course-badge {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  background: #f0f2f5;
  border: 1px solid transparent;
  transition: all 0.2s;
}
.course-badge:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.course-badge.not_started {
  background: #e6f1fc;
  color: #409eff;
  border-color: #c6e2ff;
}
.course-badge.in_progress {
  background: #f0f9eb;
  color: #67c23a;
  border-color: #e1f3d8;
}
.course-badge.ended {
  background: #f4f4f5;
  color: #909399;
  border-color: #e9e9eb;
}
.c-time {
  font-weight: 600;
  margin-right: 4px;
}
.c-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}
.course-more {
  font-size: 12px;
  color: #909399;
  text-align: center;
  margin-top: 2px;
}


.module-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 0 4px;
}
.section-title-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}
.title-icon-box {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #409eff 0%, #3a8ee6 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 18px;
  box-shadow: 0 4px 10px rgba(64, 158, 255, 0.3);
}
.section-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  letter-spacing: 0.5px;
  position: relative;
}
.section-title::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: -4px;
  width: 24px;
  height: 3px;
  background: #409eff;
  border-radius: 2px;
}
.toolbar-actions {
  display: flex;
  gap: 16px;
  align-items: center;
}
.module-search {
  width: 280px;
}
:deep(.module-search .el-input__wrapper) {
  border-radius: 20px;
  box-shadow: 0 0 0 1px #dcdfe6 inset;
  background: rgba(255,255,255,0.8);
}

.gradient-btn {
  background: linear-gradient(135deg, #409eff 0%, #3a8ee6 100%);
  border: none;
  border-radius: 20px;
  padding: 8px 20px;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
  transition: all 0.3s;
}
.gradient-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.4);
}

.module-table-wrap {
  flex: 1;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
}
.module-table-wrap :deep(.el-table) {
  height: 100% !important;
}
:deep(.custom-table) {
  --el-table-border-color: #ebeef5;
  --el-table-header-bg-color: #f8f9fb;
}
:deep(.custom-table-header th) {
  color: #606266;
  font-weight: 600;
}
.number-cell {
  font-weight: 600;
  color: #303133;
}
.time-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  white-space: nowrap;
}
.time-label {
  font-family: 'Inter', monospace;
  color: #606266;
}
.time-divider {
  color: #c0c4cc;
  font-size: 12px;
}

.module-pagination {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.student-panel-scroll {
  max-height: 360px;
  overflow-y: auto;
  padding-right: 4px;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.student-panel-scroll::-webkit-scrollbar {
  width: 0;
  height: 0;
}

.student-filter-sticky {
  position: sticky;
  top: 0;
  z-index: 2;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(4px);
  padding-bottom: 8px;
}

/* Dialog Styles */
:deep(.custom-glass-dialog) {
  border-radius: 16px !important;
  overflow: hidden;
}
:deep(.custom-glass-dialog .el-dialog__title) {
  font-weight: 600;
  color: #303133;
}

.calendar-cell.is-other-month {
  opacity: 0.3;
  background-color: #fafafa;
}

.calendar-cell.is-other-month .course-list {
  pointer-events: none;
}

.popover-course-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.popover-course-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
  color: #303133;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
  margin-bottom: 4px;
}

.popover-course-header .course-count {
  font-size: 12px;
  color: #909399;
  font-weight: normal;
  background: #f4f4f5;
  padding: 2px 6px;
  border-radius: 4px;
}

.popover-course-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.course-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}

.course-status-dot.not_started {
  background-color: #909399;
}

.course-status-dot.in_progress {
  background-color: #67c23a;
}

.course-status-dot.ended {
  background-color: #e6a23c;
}

.course-details {
  flex: 1;
}

.course-details .course-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.course-details .course-time-room {
  font-size: 12px;
  color: #606266;
  display: flex;
  align-items: center;
}

.course-details .course-time-room .el-icon {
  margin-right: 4px;
  vertical-align: text-bottom;
}

.date-header-wrap {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-bottom: 2px;
  height: 24px;
  position: relative;
}

.date-info-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}

.holiday-name {
  font-size: 11px;
  color: #409eff;
  background: #ecf5ff;
  padding: 1px 5px;
  border-radius: 4px;
  font-weight: 500;
}

.day-badge {
  font-size: 11px;
  padding: 1px 5px;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
}

.day-badge:hover {
  opacity: 0.8;
}

.day-badge.is-rest {
  color: #67c23a;
  background: #f0f9eb;
  border: 1px solid #c2e7b0;
}

.day-badge.is-work {
  color: #f56c6c;
  background: #fef0f0;
  border: 1px solid #fbc4c4;
}

.day-badge.has-override {
  box-shadow: 0 0 0 1px currentColor inset;
  border-style: dashed;
}

.cell-note {
  font-size: 12px;
  color: #e6a23c;
  background: #fdf6ec;
  border-radius: 4px;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  box-sizing: border-box;
  padding: 8px;
}
.cell-note .note-text {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
  text-align: center;
  line-height: 1.4;
  word-break: break-all;
}

.floating-note-dialog {
  position: fixed;
  z-index: 9999;
  width: 320px;
  padding: 16px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.15), 0 2px 10px rgba(0,0,0,0.05);
  border: 1px solid rgba(255,255,255,0.6);
}

.dialog-header-custom {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
.dialog-header-custom .el-icon {
  color: #409eff;
  font-size: 22px;
}
.note-input-wrap {
  margin-top: -10px;
}
:deep(.note-input-wrap .el-textarea__inner) {
  border-radius: 8px;
  background: rgba(245,247,250,0.8);
  box-shadow: 0 0 0 1px #dcdfe6 inset;
  padding: 12px;
  font-size: 14px;
  transition: all 0.3s;
}
:deep(.note-input-wrap .el-textarea__inner:focus) {
  background: #ffffff;
  box-shadow: 0 0 0 1px #409eff inset;
}

.popover-note {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed #ebeef5;
  font-size: 12px;
  color: #606266;
  line-height: 1.4;
  display: flex;
  align-items: flex-start;
  gap: 4px;
}
.popover-note .el-icon {
  margin-top: 2px;
  color: #909399;
}
</style>
