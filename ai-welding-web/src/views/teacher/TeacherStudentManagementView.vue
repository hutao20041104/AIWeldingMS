<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { API_BASE_URL } from '../../composables/useAuth'

type StudentRow = {
  id: string
  identity_code: string
  username: string
  major: string
  major_code: string
  class_code: string
  class_name: string
  created_at: string
}

const activeTab = ref('student-info')
const loading = ref(false)
const importing = ref(false)
const tableData = ref<StudentRow[]>([])
const importDialogVisible = ref(false)
const importReviewTab = ref('valid')
const importSummary = ref('')
const importSessionId = ref('')
const validRows = ref<Record<string, string>[]>([])
const invalidRows = ref<Record<string, string>[]>([])
const importStats = ref({
  total_rows: 0,
  valid_count: 0,
  invalid_count: 0,
})
const currentPage = ref(1)
const pageSize = 25

const filters = ref({
  identity_code: '',
  major_code: '',
  class_code: '',
  class_name: '',
})

const hasFilters = computed(
  () =>
    !!filters.value.identity_code ||
    !!filters.value.major_code ||
    !!filters.value.class_code ||
    !!filters.value.class_name,
)

function authHeaders() {
  const token = localStorage.getItem('access_token')
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

const canCommit = computed(() => importStats.value.valid_count > 0)
const hasInvalidRows = computed(() => importStats.value.invalid_count > 0)
const allInvalid = computed(
  () => importStats.value.total_rows > 0 && importStats.value.valid_count === 0,
)
const allValid = computed(
  () =>
    importStats.value.total_rows > 0 &&
    importStats.value.valid_count === importStats.value.total_rows,
)
const pagedTableData = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return tableData.value.slice(start, start + pageSize)
})

async function fetchStudents() {
  loading.value = true
  try {
    const query = new URLSearchParams()
    if (filters.value.identity_code) query.set('identity_code', filters.value.identity_code.trim())
    if (filters.value.major_code) query.set('major_code', filters.value.major_code.trim())
    if (filters.value.class_code) query.set('class_code', filters.value.class_code.trim())
    if (filters.value.class_name) query.set('class_name', filters.value.class_name.trim())

    const suffix = query.toString() ? `?${query}` : ''
    const res = await fetch(`${API_BASE_URL}/api/students${suffix}`, {
      headers: { ...authHeaders() },
    })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '获取学生信息失败')
      return
    }
    tableData.value = data
    currentPage.value = 1
  } catch {
    ElMessage.error('网络异常，无法获取学生信息')
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.value = {
    identity_code: '',
    major_code: '',
    class_code: '',
    class_name: '',
  }
  fetchStudents()
}

async function handleImportStudents(uploadFile: { raw?: File }) {
  const rawFile = uploadFile.raw
  if (!rawFile) return
  if (!rawFile.name.endsWith('.xlsx')) {
    ElMessage.warning('请上传 .xlsx 文件')
    return
  }

  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', rawFile)

    const res = await fetch(`${API_BASE_URL}/api/students/import/validate`, {
      method: 'POST',
      headers: { ...authHeaders() },
      body: formData,
    })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '导入失败')
      return
    }

    importSessionId.value = data.import_id || ''
    importSummary.value = data.message || '导入校验完成'
    importStats.value = {
      total_rows: data.total_rows || 0,
      valid_count: data.valid_count || 0,
      invalid_count: data.invalid_count || 0,
    }
    validRows.value = Array.isArray(data.valid_rows) ? data.valid_rows : []
    invalidRows.value = Array.isArray(data.invalid_rows) ? data.invalid_rows : []
    importReviewTab.value = invalidRows.value.length > 0 ? 'invalid' : 'valid'
    importDialogVisible.value = true
  } catch {
    ElMessage.error('网络异常，导入失败')
  } finally {
    importing.value = false
  }
}

async function commitImport(ignoreInvalid: boolean) {
  if (!importSessionId.value) {
    ElMessage.warning('导入会话已失效，请重新上传')
    return
  }
  if (!canCommit.value) {
    ElMessage.warning('数据有误，请先修正')
    return
  }

  importing.value = true
  try {
    const res = await fetch(`${API_BASE_URL}/api/students/import/commit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({
        import_id: importSessionId.value,
        ignore_invalid: ignoreInvalid,
      }),
    })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '导入失败')
      return
    }

    ElMessage.success(
      `导入完成：新增 ${data.imported_count}，已存在跳过 ${data.skipped_existing_count}，异常 ${data.invalid_count}`,
    )
    importDialogVisible.value = false
    await fetchStudents()
  } catch {
    ElMessage.error('网络异常，导入失败')
  } finally {
    importing.value = false
  }
}

async function downloadInvalidTemplate() {
  if (!importSessionId.value) {
    ElMessage.warning('导入会话已失效，请重新上传')
    return
  }
  try {
    const res = await fetch(`${API_BASE_URL}/api/students/import/${importSessionId.value}/invalid-template`, {
      headers: { ...authHeaders() },
    })
    if (!res.ok) {
      const data = await res.json()
      ElMessage.error(data.message || '下载异常模板失败')
      return
    }
    const blob = await res.blob()
    const url = window.URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'student_invalid_rows.xlsx'
    anchor.click()
    window.URL.revokeObjectURL(url)
  } catch {
    ElMessage.error('网络异常，下载异常模板失败')
  }
}

async function downloadTemplate() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/students/template`, {
      headers: { ...authHeaders() },
    })
    if (!res.ok) {
      ElMessage.error('模板下载失败')
      return
    }
    const blob = await res.blob()
    const url = window.URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'student_import_template.xlsx'
    anchor.click()
    window.URL.revokeObjectURL(url)
  } catch {
    ElMessage.error('网络异常，模板下载失败')
  }
}

onMounted(() => {
  fetchStudents()
})
</script>

<template>
  <section class="student-management-page">
    <el-card class="glass-card module-table-card" shadow="never">
      <el-tabs v-model="activeTab" class="custom-tabs">
        <el-tab-pane label="学生信息" name="student-info">
          <div class="module-toolbar">
            <div class="toolbar-left">
              <el-input v-model="filters.identity_code" placeholder="按学号筛选" clearable class="module-search search-input" />
              <el-input v-model="filters.major_code" placeholder="按专业code筛选" clearable class="module-search search-input" />
              <el-input v-model="filters.class_code" placeholder="按班级code筛选" clearable class="module-search search-input" />
              <el-input v-model="filters.class_name" placeholder="按班级筛选" clearable class="module-search search-input" />
              <el-button @click="resetFilters" :disabled="!hasFilters" plain>重置</el-button>
              <el-button type="primary" @click="fetchStudents" class="gradient-btn">查询</el-button>
            </div>
            <div class="toolbar-right">
              <el-upload :show-file-list="false" :auto-upload="false" :on-change="handleImportStudents" style="display: inline-block;">
                <el-button :loading="importing" type="primary" plain>导入学生</el-button>
              </el-upload>
              <el-button @click="downloadTemplate" plain>下载模板</el-button>
            </div>
          </div>

          <div class="module-table-wrap">
            <el-table :data="pagedTableData" border v-loading="loading" class="custom-table" header-cell-class-name="custom-table-header">
              <el-table-column prop="identity_code" label="学号" width="140" />
              <el-table-column prop="username" label="姓名" width="140" />
              <el-table-column prop="major" label="专业" min-width="180" />
              <el-table-column prop="major_code" label="专业code" width="140" />
              <el-table-column prop="class_name" label="班级" min-width="160" />
              <el-table-column prop="class_code" label="班级code" width="140" />
            </el-table>
          </div>
          <div class="module-pagination">
            <el-pagination
              v-model:current-page="currentPage"
              :page-size="pageSize"
              layout="total, prev, pager, next"
              :total="tableData.length"
              background
            />
          </div>
        </el-tab-pane>

        <el-tab-pane label="学生账号信息管理" name="account-management">
          <el-empty description="学生账号信息管理子模块后续实现" />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog
      v-model="importDialogVisible"
      title="学生导入校验结果"
      width="980px"
      top="8vh"
      destroy-on-close
    >
      <p style="margin-top: 0; color: #475569">{{ importSummary }}</p>
      <el-alert
        :type="allInvalid ? 'error' : hasInvalidRows ? 'warning' : 'success'"
        :closable="false"
        show-icon
        style="margin-bottom: 12px"
        :title="`总计 ${importStats.total_rows} 行；正确 ${importStats.valid_count} 行；异常 ${importStats.invalid_count} 行`"
      />
      <el-tabs v-model="importReviewTab">
        <el-tab-pane :label="`正确数据(${importStats.valid_count})`" name="valid">
          <el-scrollbar max-height="360px">
            <el-table :data="validRows" border>
              <el-table-column prop="identity_code" label="学号" width="140" />
              <el-table-column prop="username" label="姓名" width="140" />
              <el-table-column prop="major" label="专业" min-width="160" />
              <el-table-column prop="major_code" label="专业code" width="140" />
              <el-table-column prop="class_code" label="班级code" width="140" />
              <el-table-column prop="class_name" label="班级" min-width="140" />
            </el-table>
          </el-scrollbar>
        </el-tab-pane>
        <el-tab-pane :label="`异常数据(${importStats.invalid_count})`" name="invalid">
          <el-scrollbar max-height="360px">
            <el-table :data="invalidRows" border>
              <el-table-column prop="identity_code" label="学号" width="140" />
              <el-table-column prop="username" label="姓名" width="120" />
              <el-table-column prop="major" label="专业" width="140" />
              <el-table-column prop="class_code" label="班级code" width="120" />
              <el-table-column prop="error_message" label="异常信息" min-width="340" />
            </el-table>
          </el-scrollbar>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="importDialogVisible = false">关闭</el-button>
        <el-button v-if="hasInvalidRows" @click="downloadInvalidTemplate">下载异常数据模板</el-button>
        <el-button
          v-if="allValid"
          type="primary"
          :loading="importing"
          @click="commitImport(false)"
        >
          继续导入
        </el-button>
        <el-button
          v-else-if="hasInvalidRows && canCommit"
          type="warning"
          :loading="importing"
          @click="commitImport(true)"
        >
          忽视异常数据，继续导入
        </el-button>
        <el-button v-else-if="allInvalid" type="danger" disabled>
          数据有误，请先修正
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.student-management-page {
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

.module-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.toolbar-left {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}
.toolbar-right {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-shrink: 0;
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
:deep(.el-table) {
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

.module-pagination {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
