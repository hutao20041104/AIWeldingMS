<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { API_BASE_URL } from '../../composables/useAuth'

// Types
type CourseOut = {
  id: number
  course_code: string
  classroom: string
  class_display: string
  status: string
  status_label: string
  start_time: string
  end_time: string
  created_at: string
  student_count: number
}

type GradeRecordOut = {
  student_id: string
  identity_code: string
  username: string
  ai_score: number | null
  teacher_score: number | null
  final_score: number | null
}

type StudentGradeHistoryOut = {
  course_id: int
  course_code: string
  classroom: string
  ai_score: number | null
  teacher_score: number | null
  final_score: number | null
  graded_at: string | null
}

// State
const viewMode = ref<'courses' | 'course_grades' | 'student_grades'>('courses')
const loading = ref(false)

// Mode 1: Courses
const courses = ref<CourseOut[]>([])
const courseKeyword = ref('')
const courseCurrentPage = ref(1)
const pageSize = 15

// Mode 2: Course Grades
const activeCourse = ref<CourseOut | null>(null)
const courseGrades = ref<GradeRecordOut[]>([])
const gradeKeyword = ref('')
const gradeCurrentPage = ref(1)

// Mode 3: Student History
const activeStudent = ref<{ id: string; name: string; code: string } | null>(null)
const studentHistory = ref<StudentGradeHistoryOut[]>([])

// Auth headers
function authHeaders() {
  const token = localStorage.getItem('access_token')
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

// Formatters
function formatTime(value?: string) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n: number) => `${n}`.padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function formatScore(score: number | null) {
  return score !== null ? score.toFixed(1) : '-'
}

// Computeds
const filteredCourses = computed(() => {
  const key = courseKeyword.value.trim().toLowerCase()
  if (!key) return courses.value
  return courses.value.filter(
    (c) =>
      c.course_code.toLowerCase().includes(key) ||
      c.class_display.toLowerCase().includes(key) ||
      c.classroom.toLowerCase().includes(key)
  )
})

const pagedCourses = computed(() => {
  const start = (courseCurrentPage.value - 1) * pageSize
  return filteredCourses.value.slice(start, start + pageSize)
})

const filteredGrades = computed(() => {
  const key = gradeKeyword.value.trim().toLowerCase()
  if (!key) return courseGrades.value
  return courseGrades.value.filter(
    (g) => g.identity_code.includes(key) || g.username.toLowerCase().includes(key)
  )
})

const pagedGrades = computed(() => {
  const start = (gradeCurrentPage.value - 1) * pageSize
  return filteredGrades.value.slice(start, start + pageSize)
})

// Actions: Courses
async function fetchCourses() {
  loading.value = true
  try {
    const res = await fetch(`${API_BASE_URL}/api/courses/`, { headers: { ...authHeaders() } })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '获取课程失败')
      return
    }
    courses.value = data
  } catch {
    ElMessage.error('网络异常，获取课程失败')
  } finally {
    loading.value = false
  }
}

// Actions: Course Grades
async function openCourseGrades(course: CourseOut) {
  activeCourse.value = course
  viewMode.value = 'course_grades'
  gradeKeyword.value = ''
  gradeCurrentPage.value = 1
  await fetchCourseGrades()
}

async function fetchCourseGrades() {
  if (!activeCourse.value) return
  loading.value = true
  try {
    const res = await fetch(`${API_BASE_URL}/api/courses/${activeCourse.value.id}/grades/`, {
      headers: { ...authHeaders() },
    })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '获取成绩单失败')
      return
    }
    courseGrades.value = data
  } catch {
    ElMessage.error('网络异常，获取成绩单失败')
  } finally {
    loading.value = false
  }
}

async function updateTeacherScore(row: GradeRecordOut) {
  if (row.teacher_score === null || row.teacher_score === undefined) return
  const val = Number(row.teacher_score)
  if (isNaN(val) || val < 0 || val > 100) {
    ElMessage.warning('教师评分必须在 0 - 100 之间')
    return
  }

  try {
    const res = await fetch(`${API_BASE_URL}/api/courses/${activeCourse.value!.id}/grades/${row.student_id}/`, {
      method: 'PUT',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ teacher_score: val }),
    })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '成绩更新失败')
      return
    }
    ElMessage.success('成绩已保存')
    row.final_score = data.final_score
  } catch {
    ElMessage.error('网络异常，成绩更新失败')
  }
}

// Actions: Student History
async function openStudentHistory(row: GradeRecordOut) {
  activeStudent.value = { id: row.student_id, name: row.username, code: row.identity_code }
  viewMode.value = 'student_grades'
  loading.value = true
  try {
    const res = await fetch(`${API_BASE_URL}/api/courses/students/${row.student_id}/grades/`, {
      headers: { ...authHeaders() },
    })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '获取学生历史成绩失败')
      return
    }
    studentHistory.value = data
  } catch {
    ElMessage.error('网络异常，获取学生历史成绩失败')
  } finally {
    loading.value = false
  }
}

function backToCourses() {
  viewMode.value = 'courses'
  activeCourse.value = null
  courseGrades.value = []
}

function backToCourseGrades() {
  viewMode.value = 'course_grades'
  activeStudent.value = null
  studentHistory.value = []
}

onMounted(() => {
  fetchCourses()
})
</script>

<template>
  <section class="module-page">
    
    <!-- Level 1: Course List -->
    <el-card class="module-table-card" shadow="never" v-if="viewMode === 'courses'">
      <div class="module-toolbar">
        <div class="header-title">课程列表 (选择课程进行成绩录入)</div>
        <el-input v-model="courseKeyword" placeholder="搜索课程编号/地点/班级" clearable class="module-search" />
      </div>
      <div class="module-table-wrap">
        <el-table :data="pagedCourses" border v-loading="loading">
          <el-table-column prop="course_code" label="课程编号" min-width="160" />
          <el-table-column prop="class_display" label="参与班级/专业" min-width="200" />
          <el-table-column prop="classroom" label="地点" min-width="140" />
          <el-table-column prop="status_label" label="状态" width="100" />
          <el-table-column label="选课人数" width="100" align="center">
            <template #default="{ row }">{{ row.student_count }} 人</template>
          </el-table-column>
          <el-table-column label="开课时间" min-width="160">
            <template #default="{ row }">{{ formatTime(row.start_time) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openCourseGrades(row)">查看/录入成绩</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div class="module-pagination">
        <el-pagination
          v-model:current-page="courseCurrentPage"
          :page-size="pageSize"
          layout="total, prev, pager, next"
          :total="filteredCourses.length"
        />
      </div>
    </el-card>

    <!-- Level 2: Course Grades -->
    <el-card class="module-table-card" shadow="never" v-else-if="viewMode === 'course_grades'">
      <div class="module-toolbar">
        <div class="header-back" @click="backToCourses">
          <el-icon><ArrowLeft /></el-icon>
          返回课程列表
        </div>
        <div class="header-title">
          《{{ activeCourse?.course_code }}》成绩单 
          <el-tag size="small" type="info">{{ activeCourse?.class_display }}</el-tag>
        </div>
        <div style="flex: 1"></div>
        <el-input v-model="gradeKeyword" placeholder="搜索学号/姓名" clearable class="module-search" />
      </div>
      
      <el-alert 
        title="成绩计算规则：最终评分 = AI智能评分 × 30% + 教师评分 × 70%。若其中一项未评分，则暂无最终成绩。" 
        type="info" 
        show-icon 
        :closable="false"
        style="margin-bottom: 16px;" 
      />

      <div class="module-table-wrap">
        <el-table :data="pagedGrades" border v-loading="loading">
          <el-table-column prop="identity_code" label="学号" min-width="140" />
          <el-table-column label="姓名" min-width="140">
            <template #default="{ row }">
              <el-button link type="primary" @click="openStudentHistory(row)">
                {{ row.username }}
              </el-button>
            </template>
          </el-table-column>
          <el-table-column label="AI评分 (30%)" width="140" align="center">
            <template #default="{ row }">
              <el-tag :type="row.ai_score ? 'success' : 'info'" effect="plain">
                {{ formatScore(row.ai_score) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="教师评分 (70%)" width="200" align="center">
            <template #default="{ row }">
              <el-input-number 
                v-model="row.teacher_score" 
                :min="0" 
                :max="100" 
                :precision="1" 
                :step="1"
                placeholder="录入"
                @change="updateTeacherScore(row)"
              />
            </template>
          </el-table-column>
          <el-table-column label="最终评分" width="140" align="center">
            <template #default="{ row }">
              <strong :style="{ color: row.final_score ? 'var(--el-color-primary)' : 'var(--el-text-color-placeholder)' }">
                {{ formatScore(row.final_score) }}
              </strong>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div class="module-pagination">
        <el-pagination
          v-model:current-page="gradeCurrentPage"
          :page-size="pageSize"
          layout="total, prev, pager, next"
          :total="filteredGrades.length"
        />
      </div>
    </el-card>

    <!-- Level 3: Student History -->
    <el-card class="module-table-card" shadow="never" v-else-if="viewMode === 'student_grades'">
      <div class="module-toolbar">
        <div class="header-back" @click="backToCourseGrades">
          <el-icon><ArrowLeft /></el-icon>
          返回成绩单
        </div>
        <div class="header-title">
          {{ activeStudent?.name }} ({{ activeStudent?.code }}) 的历史成绩
        </div>
      </div>
      
      <div class="module-table-wrap">
        <el-table :data="studentHistory" border v-loading="loading">
          <el-table-column prop="course_code" label="课程编号" min-width="160" />
          <el-table-column prop="classroom" label="授课地点" min-width="140" />
          <el-table-column label="AI评分" width="120" align="center">
            <template #default="{ row }">{{ formatScore(row.ai_score) }}</template>
          </el-table-column>
          <el-table-column label="教师评分" width="120" align="center">
            <template #default="{ row }">{{ formatScore(row.teacher_score) }}</template>
          </el-table-column>
          <el-table-column label="最终评分" width="140" align="center">
            <template #default="{ row }">
              <strong style="color: var(--el-color-primary)">{{ formatScore(row.final_score) }}</strong>
            </template>
          </el-table-column>
          <el-table-column label="最后更新时间" min-width="160">
            <template #default="{ row }">{{ formatTime(row.graded_at) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

  </section>
</template>

<style scoped>
.header-title {
  font-size: 16px;
  font-weight: bold;
  color: var(--el-text-color-primary);
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-back {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  color: var(--el-color-primary);
  font-size: 14px;
  font-weight: 500;
  margin-right: 20px;
  transition: opacity 0.3s;
}

.header-back:hover {
  opacity: 0.8;
}

:deep(.el-input-number .el-input__inner) {
  text-align: center;
}
</style>
