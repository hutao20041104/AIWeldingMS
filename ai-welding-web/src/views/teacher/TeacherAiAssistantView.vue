<script setup lang="ts">
import { ref } from 'vue'

const inputValue = ref('')
const messages = ref([
  { role: 'assistant', text: '您好，我是 AI 教学助手。您可以让我帮您生成焊接课程教案、实验指导和课堂总结。' },
  { role: 'user', text: '请给我一份《MIG 焊接工艺》90 分钟课堂教学提纲。' },
  { role: 'assistant', text: '已为您生成提纲草稿：教学目标、知识讲授、实操演示、分组训练、课堂反馈。' },
])
</script>

<template>
  <section class="module-page">
    <div class="assistant-layout">
      <el-card class="assistant-card history" shadow="never">
        <template #header>最近会话</template>
        <ul class="assistant-history">
          <li class="active">MIG焊接工艺教案生成</li>
          <li>实训评分标准优化建议</li>
          <li>课堂总结自动生成</li>
          <li>学生常见问题答疑模板</li>
        </ul>
      </el-card>

      <el-card class="assistant-card chat" shadow="never">
        <template #header>AI 对话面板</template>
        <div class="assistant-messages">
          <div
            v-for="(item, idx) in messages"
            :key="idx"
            :class="['assistant-message', item.role]"
          >
            {{ item.text }}
          </div>
        </div>
        <div class="assistant-input">
          <el-input
            v-model="inputValue"
            type="textarea"
            :rows="3"
            placeholder="输入你要让 AI 教学助手完成的任务..."
          />
          <div class="assistant-input-actions">
            <el-button type="primary" plain>新建会话</el-button>
            <el-button>清空</el-button>
            <el-button type="primary">发送</el-button>
          </div>
        </div>
      </el-card>
    </div>
  </section>
</template>
