<script setup lang="ts">
import { computed, ref } from 'vue'

const keyword = ref('')
const tableData = ref([
  { lab: '焊接实训A室', online: '在线', seatUsage: '7/10', warning: '无' },
  { lab: '焊接实训B室', online: '在线', seatUsage: '9/10', warning: '温度偏高' },
  { lab: '机器人焊接室', online: '维护中', seatUsage: '0/8', warning: '网络离线' },
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
        <el-button>查看告警</el-button>
        <el-input v-model="keyword" placeholder="搜索实验室名称" clearable class="module-search" />
        <div class="module-toolbar-actions">
          <el-button>刷新状态</el-button>
          <el-button type="primary">大屏模式</el-button>
        </div>
      </div>
      <div class="module-table-wrap">
        <el-table :data="pagedTableData" border>
          <el-table-column prop="lab" label="实验室" min-width="220" />
          <el-table-column prop="online" label="在线状态" width="120" />
          <el-table-column prop="seatUsage" label="工位占用" width="120" />
          <el-table-column prop="warning" label="告警信息" min-width="180" />
          <el-table-column label="操作" width="140">
            <template #default>
              <el-button link type="primary">查看</el-button>
              <el-button link type="primary">处理</el-button>
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
