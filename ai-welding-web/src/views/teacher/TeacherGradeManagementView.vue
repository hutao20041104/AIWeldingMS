<script setup lang="ts">
import { computed, ref } from 'vue'

const keyword = ref('')
const tableData = ref([
  { studentId: '2023001', studentName: '张三', course: 'MIG焊接工艺基础', score: 92, level: '优秀' },
  { studentId: '2023002', studentName: '李四', course: '机器人焊接编程', score: 76, level: '良好' },
  { studentId: '2023003', studentName: '王五', course: '焊接缺陷检测', score: 64, level: '及格' },
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
        <el-button type="primary">录入成绩</el-button>
        <el-input v-model="keyword" placeholder="搜索学号/姓名/课程" clearable class="module-search" />
        <div class="module-toolbar-actions">
          <el-button>导出成绩单</el-button>
          <el-button type="primary">成绩分析</el-button>
        </div>
      </div>
      <div class="module-table-wrap">
        <el-table :data="pagedTableData" border>
          <el-table-column prop="studentId" label="学号" width="130" />
          <el-table-column prop="studentName" label="姓名" width="120" />
          <el-table-column prop="course" label="课程" min-width="220" />
          <el-table-column prop="score" label="分数" width="100" />
          <el-table-column prop="level" label="等级" width="120" />
          <el-table-column label="操作" width="150">
            <template #default>
              <el-button link type="primary">修改</el-button>
              <el-button link type="primary">详情</el-button>
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
