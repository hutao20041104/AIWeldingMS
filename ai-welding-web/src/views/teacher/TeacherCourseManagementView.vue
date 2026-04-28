<script setup lang="ts">
import { computed, ref } from 'vue'

const keyword = ref('')
const tableData = ref([
  { code: 'WELD-101', name: 'MIG焊接工艺基础', className: '焊接231', progress: '进行中' },
  { code: 'WELD-203', name: '机器人焊接编程', className: '焊接232', progress: '未开始' },
  { code: 'WELD-306', name: '焊接缺陷检测', className: '焊接231', progress: '已完成' },
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
        <el-button type="primary">新建课程</el-button>
        <el-input v-model="keyword" placeholder="搜索课程名称/编码" clearable class="module-search" />
        <div class="module-toolbar-actions">
          <el-button>导出</el-button>
          <el-button type="primary">批量发布</el-button>
        </div>
      </div>
      <div class="module-table-wrap">
        <el-table :data="pagedTableData" border>
          <el-table-column prop="code" label="课程编码" width="140" />
          <el-table-column prop="name" label="课程名称" min-width="220" />
          <el-table-column prop="className" label="班级" width="140" />
          <el-table-column prop="progress" label="进度状态" width="120" />
          <el-table-column label="操作" width="160">
            <template #default>
              <el-button link type="primary">查看</el-button>
              <el-button link type="primary">编辑</el-button>
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
