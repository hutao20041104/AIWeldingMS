<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, ChatDotRound, Cpu } from '@element-plus/icons-vue'
import { currentUser, API_BASE_URL } from '../../composables/useAuth'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import aiAvatarSrc from '../../assets/robot.png'

type ChatSession = {
  id: string
  title: string
  created_at: string
}

type ChatMessage = {
  id?: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at?: string
}

// State
const sessions = ref<ChatSession[]>([])
const activeSessionId = ref<string | null>(null)
const messages = ref<ChatMessage[]>([])
const inputValue = ref('')
const loading = ref(false)
const msgContainer = ref<HTMLElement | null>(null)

const userAvatarSrc = computed(() => {
  const avatar = currentUser.value?.avatar
  if (avatar) {
    if (/^https?:\/\//i.test(avatar)) return avatar
    return `${API_BASE_URL}${avatar}`
  }
  return `https://api.dicebear.com/7.x/adventurer/svg?seed=${currentUser.value?.username || 'user'}`
})


// Auth headers
function authHeaders() {
  const token = localStorage.getItem('access_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json'
  }
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

// Markdown parser
function parseMarkdown(rawContent: string) {
  if (!rawContent) return ''
  const html = marked.parse(rawContent) as string
  return DOMPurify.sanitize(html)
}

// API Calls
async function fetchSessions() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/assistant/sessions/`, { headers: authHeaders() })
    if (res.ok) {
      sessions.value = await res.json()
      if (sessions.value.length > 0 && !activeSessionId.value) {
        selectSession(sessions.value[0].id)
      } else if (sessions.value.length === 0) {
        await createSession()
      }
    }
  } catch (err) {
    ElMessage.error('无法获取历史会话')
  }
}

async function createSession() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/assistant/sessions/`, {
      method: 'POST',
      headers: authHeaders()
    })
    if (res.ok) {
      const data = await res.json()
      sessions.value.unshift(data)
      selectSession(data.id)
    }
  } catch (err) {
    ElMessage.error('创建会话失败')
  }
}

async function selectSession(id: string) {
  activeSessionId.value = id
  messages.value = []
  try {
    const res = await fetch(`${API_BASE_URL}/api/assistant/sessions/${id}/messages/`, { headers: authHeaders() })
    if (res.ok) {
      const data = await res.json()
      // Fallback greeting if no messages
      if (data.length === 0) {
        messages.value = [{ role: 'assistant', content: '您好，我是 AI 焊接教学助手。您可以让我帮您生成焊接课程教案、解答焊接工艺问题、或者进行课堂总结。' }]
      } else {
        messages.value = data
      }
      scrollToBottom()
    }
  } catch (err) {
    ElMessage.error('加载历史记录失败')
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (msgContainer.value) {
      msgContainer.value.scrollTop = msgContainer.value.scrollHeight
    }
  })
}

// Streaming logic
async function sendMessage() {
  const text = inputValue.value.trim()
  if (!text || !activeSessionId.value || loading.value) return

  const sessionId = activeSessionId.value
  
  // 1. Add user message
  messages.value.push({ role: 'user', content: text })
  inputValue.value = ''
  loading.value = true
  scrollToBottom()

  // 2. Add empty assistant message for streaming
  messages.value.push({ role: 'assistant', content: '' })
  const assistantMsgIndex = messages.value.length - 1

  try {
    const res = await fetch(`${API_BASE_URL}/api/assistant/sessions/${sessionId}/chat/`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ message: text })
    })

    if (!res.ok) {
      ElMessage.error('调用大模型失败，请检查后端配置')
      messages.value[assistantMsgIndex].content = '对不起，系统出现错误。'
      loading.value = false
      return
    }

    if (!res.body) {
      loading.value = false
      return
    }

    // Parse SSE stream
    const reader = res.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || '' // keep the last incomplete part in buffer

      for (const part of parts) {
        if (part.startsWith('data: ')) {
          const dataStr = part.replace('data: ', '')
          if (dataStr === '[DONE]') {
            break
          }
          try {
            const parsed = JSON.parse(dataStr)
            if (parsed.error) {
              ElMessage.error(parsed.error)
            } else if (parsed.content) {
              messages.value[assistantMsgIndex].content += parsed.content
              scrollToBottom()
            } else if (parsed.tool_call) {
              messages.value[assistantMsgIndex].content += parsed.tool_call
              scrollToBottom()
            }
          } catch (e) {
            console.error('Failed to parse SSE data', e)
          }
        }
      }
    }
    
    // Refresh sessions to get updated title if it was a new session
    fetchSessions()

  } catch (err) {
    ElMessage.error('网络连接断开')
    messages.value[assistantMsgIndex].content += '\n[网络连接异常]'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchSessions()
})
</script>

<template>
  <section class="module-page">
    <div class="assistant-layout">
      
      <!-- 左侧：历史会话列表 -->
      <el-card class="assistant-card history" shadow="never">
        <template #header>
          <div class="history-header">
            <span>最近会话</span>
            <el-button type="primary" circle :icon="Plus" size="small" @click="createSession" title="新建会话" />
          </div>
        </template>
        <ul class="assistant-history">
          <li 
            v-for="session in sessions" 
            :key="session.id"
            :class="{ active: session.id === activeSessionId }"
            @click="selectSession(session.id)"
          >
            <el-icon><ChatDotRound /></el-icon>
            <span class="session-title">{{ session.title }}</span>
          </li>
        </ul>
      </el-card>

      <!-- 右侧：对话面板 -->
      <el-card class="assistant-card chat" shadow="never" v-loading="!activeSessionId">
        <div class="assistant-messages" ref="msgContainer">
          <div
            v-for="(item, idx) in messages"
            :key="idx"
            :class="['message-row', item.role]"
          >
            <el-avatar 
              v-if="item.role === 'assistant' || item.role === 'system'" 
              :src="aiAvatarSrc" 
              class="message-avatar" 
            />
            <div v-if="item.role === 'user'" class="assistant-message user-message">{{ item.content }}</div>
            <div v-else class="assistant-message markdown-body ai-message" v-html="parseMarkdown(item.content)"></div>
            <el-avatar 
              v-if="item.role === 'user'" 
              :src="userAvatarSrc" 
              class="message-avatar" 
            />
          </div>
        </div>
        <div class="assistant-input-area">
          <el-input
            v-model="inputValue"
            type="textarea"
            :rows="3"
            placeholder="输入你要让 AI 教学助手完成的任务..."
            @keydown.enter.prevent="sendMessage"
          />
          <div class="assistant-input-actions">
            <el-button type="primary" @click="sendMessage" :loading="loading" :disabled="!inputValue.trim()">
              发送 (Enter)
            </el-button>
          </div>
        </div>
      </el-card>
      
    </div>
  </section>
</template>

<style scoped>
.assistant-layout {
  display: flex;
  gap: 20px;
  height: calc(100vh - 100px);
}

.assistant-card.history {
  width: 280px;
  display: flex;
  flex-direction: column;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

:deep(.assistant-card.history .el-card__body) {
  padding: 10px;
  overflow-y: auto;
  flex: 1;
}

.assistant-history {
  list-style: none;
  padding: 0;
  margin: 0;
}

.assistant-history li {
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  color: var(--el-text-color-regular);
  margin-bottom: 8px;
  background: transparent;
  display: flex;
  align-items: center;
  gap: 8px;
}

.assistant-history li:hover {
  background: var(--el-fill-color-light);
}

.assistant-history li.active {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-weight: 500;
}

.session-icon {
  width: 20px;
  height: 20px;
}

.session-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

/* 聊天面板 */
.assistant-card.chat {
  flex: 1;
  display: flex;
  flex-direction: column;
}

:deep(.assistant-card.chat .el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0; /* Remove padding to handle areas separately */
  overflow: hidden;
}

.assistant-messages {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
}

.message-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.message-row.user {
  justify-content: flex-end;
}

.message-avatar {
  flex-shrink: 0;
  border: 2px solid white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  background-color: var(--el-bg-color);
  width: 40px;
  height: 40px;
}



.assistant-message {
  max-width: 80%;
  padding: 16px 20px;
  border-radius: 16px;
  line-height: 1.6;
  font-size: 14px;
  word-break: break-word;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

/* Markdown Styles */
.markdown-body :deep(h1), .markdown-body :deep(h2), .markdown-body :deep(h3), .markdown-body :deep(h4) {
  margin-top: 10px;
  margin-bottom: 10px;
  font-weight: 600;
}
.markdown-body :deep(p) {
  margin-bottom: 8px;
}
.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}
.markdown-body :deep(ul), .markdown-body :deep(ol) {
  padding-left: 20px;
  margin-bottom: 8px;
}
.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 10px;
}
.markdown-body :deep(th), .markdown-body :deep(td) {
  border: 1px solid var(--el-border-color-lighter);
  padding: 8px;
}
.markdown-body :deep(th) {
  background-color: rgba(0,0,0,0.02);
}
.markdown-body :deep(blockquote) {
  margin: 0 0 10px 0;
  padding: 10px 15px;
  border-left: 4px solid var(--el-color-primary);
  background-color: rgba(64, 158, 255, 0.1);
  color: var(--el-text-color-regular);
}
.markdown-body :deep(code) {
  background-color: rgba(0,0,0,0.04);
  padding: 2px 4px;
  border-radius: 4px;
  font-family: monospace;
}

.message-row.assistant .assistant-message, .message-row.system .assistant-message {
  background: #ffffff;
  color: var(--el-text-color-primary);
  border-radius: 4px 16px 16px 16px;
  border: 1px solid var(--el-border-color-lighter);
}

.message-row.user .assistant-message {
  background: var(--el-color-primary);
  color: white;
  border-radius: 16px 4px 16px 16px;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.25);
  white-space: pre-wrap;
}

/* 底部输入框 */
.assistant-input-area {
  padding: 16px 20px;
  background: var(--el-bg-color);
  border-top: 1px solid var(--el-border-color-lighter);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.assistant-input-actions {
  display: flex;
  justify-content: flex-end;
}
</style>
