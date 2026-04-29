<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { API_BASE_URL } from '../../composables/useAuth'

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

function formatTime(value?: string) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n: number) => `${n}`.padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function toDatetimeLocal(value?: string) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (n: number) => `${n}`.padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
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
      start_time: form.value.start_time,
      end_time: form.value.end_time,
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
  await Promise.all([fetchOptions(), fetchCourses()])
})
</script>

<template>
  <section class="module-page">
    <el-card class="module-table-card" shadow="never">
      <div class="module-toolbar">
        <el-button type="primary" @click="openCreateDialog">添加课程</el-button>
        <el-input v-model="keyword" placeholder="搜索课程编号/地点/班级(专业)" clearable class="module-search" />
      </div>
      <div class="module-table-wrap">
        <el-table :data="pagedTableData" border v-loading="loading">
          <el-table-column prop="course_code" label="课程编号" min-width="180" />
          <el-table-column prop="classroom" label="地点" min-width="140" />
          <el-table-column prop="class_display" label="班级(专业)" min-width="220" />
          <el-table-column prop="status_label" label="状态" width="120" />
          <el-table-column label="学生人数" width="100">
            <template #default="{ row }">
              {{ row.student_count }}
            </template>
          </el-table-column>
          <el-table-column label="创建时间" min-width="170">
            <template #default="{ row }">
              {{ formatTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" :disabled="row.status !== 'not_started'" @click="openEditDialog(row)">
                编辑
              </el-button>
              <el-button link type="primary" @click="openGroupingDialog(row)">分组</el-button>
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
        />
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingCourseId ? '编辑课程' : '添加课程'" width="980px">
      <el-form label-width="120px">
        <el-form-item label="课程编号">
          <el-input :model-value="autoCourseCode || '加载中...'" disabled />
        </el-form-item>

        <el-form-item label="添加学生">
          <div style="width: 100%">
            <div style="display: flex; gap: 12px; margin-bottom: 12px">
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
              height="260"
              v-loading="studentsLoading"
            >
              <el-table-column label="选择" width="60">
                <template #default="{ row }">
                  <el-checkbox
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
            <div style="margin-top: 8px; color: #606266">已选择学生：{{ form.student_ids.length }} 人</div>
          </div>
        </el-form-item>

        <el-form-item label="授课地点(教室)">
          <el-select v-model="form.classroom" filterable placeholder="请选择教室" style="width: 320px">
            <el-option v-for="item in classrooms" :key="item.classroom" :label="item.classroom" :value="item.classroom" />
          </el-select>
        </el-form-item>

        <el-form-item label="助教学生">
          <el-select v-model="form.assistant_student_id" clearable placeholder="可选：从已选学生指定 1 名助教" style="width: 320px">
            <el-option
              v-for="item in allStudents.filter((s) => form.student_ids.includes(s.id))"
              :key="item.id"
              :label="`${item.username} (${item.identity_code})`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="教室设备展示">
          <el-table :data="selectedClassroomDevices" border style="width: 100%">
            <el-table-column prop="device_code" label="设备编号" min-width="180" />
            <el-table-column prop="status_label" label="状态" min-width="120" />
          </el-table>
        </el-form-item>

        <el-form-item label="授课时间">
          <el-date-picker
            v-model="form.start_time"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="开始时间"
            style="width: 240px; margin-right: 12px"
          />
          <el-date-picker
            v-model="form.end_time"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="结束时间"
            style="width: 240px"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveCourse">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="groupingDialogVisible" title="课程分组" width="960px">
      <div style="margin-bottom: 12px">课程编号：{{ groupingCourseCode }}</div>
      <div style="margin-bottom: 12px">
        <el-button type="primary" :loading="groupingSaving" @click="runRandomGrouping">随机分组</el-button>
      </div>
      <el-table :data="groupingStudents" border v-loading="groupingLoading">
        <el-table-column prop="identity_code" label="学号" min-width="120" />
        <el-table-column prop="username" label="姓名" min-width="120" />
        <el-table-column prop="major" label="专业" min-width="140" />
        <el-table-column prop="class_name" label="班级" min-width="140" />
        <el-table-column label="分配设备" min-width="220">
          <template #default="{ row }">
            <el-select v-model="row.device_id" placeholder="选择设备" style="width: 200px">
              <el-option v-for="d in groupingDevices" :key="d.id" :label="`${d.device_code}(${d.status_label})`" :value="d.id" />
            </el-select>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="groupingDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="groupingSaving" @click="saveGrouping">保存分组</el-button>
      </template>
    </el-dialog>
  </section>
</template>
