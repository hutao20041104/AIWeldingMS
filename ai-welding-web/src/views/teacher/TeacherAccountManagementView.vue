<script setup lang="ts">
import { computed, ref } from 'vue'

const keyword = ref('')
const tableData = ref([
  { identity: 'T202401', username: '刘老师', role: '教师', status: '已启用' },
  { identity: 'T202402', username: '周老师', role: '教师', status: '待审核' },
  { identity: 'T202403', username: '陈老师', role: '教师', status: '已停用' },
])
const currentPage = ref(1)
const pageSize = 25
const pagedTableData = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return tableData.value.slice(start, start + pageSize)
})
</script>

<template>
  <section class="module-page">
    <el-card class="module-table-card" shadow="never">
      <div class="module-toolbar">
        <el-button type="primary" plain>新增账号</el-button>
        <el-input v-model="keyword" placeholder="搜索身份编号/用户名" clearable class="module-search" />
        <div class="module-toolbar-actions">
          <el-button>同步审核状态</el-button>
          <el-button type="primary">批量启用</el-button>
        </div>
      </div>
      <div class="module-table-wrap">
        <el-table :data="pagedTableData" border>
          <el-table-column prop="identity" label="身份编号" width="140" />
          <el-table-column prop="username" label="用户名" width="140" />
          <el-table-column prop="role" label="角色" width="120" />
          <el-table-column prop="status" label="账号状态" width="120" />
          <el-table-column label="操作" width="160">
            <template #default>
              <el-button link type="primary">编辑</el-button>
              <el-button link type="primary">授权</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div class="module-pagination">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          layout="total, prev, pager, next"
          :total="tableData.length"
        />
      </div>
    </el-card>
  </section>
</template>
