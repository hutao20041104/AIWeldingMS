<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, ChatDotRound, Cpu } from '@element-plus/icons-vue'
import { currentUser, API_BASE_URL } from '../../composables/useAuth'
import defaultTeacherAvatar from '../../assets/default_teacher.png'
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
  return defaultTeacherAvatar
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
      <div class="assistant-card history glass-card">
        <div class="history-header">
          <span>最近会话</span>
          <el-button type="primary" circle :icon="Plus" size="small" @click="createSession" title="新建会话" class="gradient-btn" />
        </div>
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
      </div>

      <!-- 右侧：对话面板 -->
      <div class="assistant-card chat glass-card" v-loading="!activeSessionId">
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
      </div>
      
    </div>
  </section>
</template>

<style scoped>
.module-page {
  padding: 16px;
  height: calc(100vh - 92px);
  box-sizing: border-box;
  overflow: hidden;
  background-color: #f8fafc;
  background-image: 
    radial-gradient(at 40% 20%, hsla(210,100%,93%,1) 0px, transparent 50%),
    radial-gradient(at 80% 0%, hsla(189,100%,96%,1) 0px, transparent 50%),
    radial-gradient(at 0% 50%, hsla(355,100%,93%,1) 0px, transparent 50%),
    radial-gradient(at 80% 50%, hsla(340,100%,96%,1) 0px, transparent 50%),
    radial-gradient(at 0% 100%, hsla(22,100%,92%,1) 0px, transparent 50%),
    radial-gradient(at 80% 100%, hsla(242,100%,96%,1) 0px, transparent 50%),
    radial-gradient(at 0% 0%, hsla(343,100%,96%,1) 0px, transparent 50%);
  background-size: 200% 200%;
  animation: mesh-movement 20s ease-in-out infinite alternate;
  border-radius: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04);
}

@keyframes mesh-movement {
  0% { background-position: 0% 0%; }
  100% { background-position: 100% 100%; }
}

@keyframes slideUpFade {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

.assistant-layout {
  display: flex;
  gap: 16px;
  height: 100%;
}

.glass-card {
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 24px;
  box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.05), inset 0 0 0 1px rgba(255,255,255,0.5);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  position: relative;
  animation: slideUpFade 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.glass-card::before {
  content: '';
  position: absolute;
  top: -50%; left: -50%; width: 200%; height: 200%;
  background: conic-gradient(transparent, transparent, transparent, rgba(79, 70, 229, 0.1), transparent);
  animation: rotate-glow 8s linear infinite;
  pointer-events: none;
  z-index: -1;
}

@keyframes rotate-glow {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
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
  padding: 14px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.5);
}
.history-header span {
  font-size: 15px;
  font-weight: 800;
  color: #0f172a;
}

.assistant-history {
  list-style: none;
  padding: 10px;
  margin: 0;
  overflow-y: auto;
  flex: 1;
}

.assistant-history li {
  padding: 10px 12px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  color: #475569;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid transparent;
}

.assistant-history li:hover {
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 4px 12px rgba(0,0,0,0.03);
  transform: translateY(-1px);
}

.assistant-history li.active {
  background: #ffffff;
  color: #4f46e5;
  font-weight: 600;
  border-color: rgba(79, 70, 229, 0.3);
  box-shadow: 0 4px 16px rgba(79, 70, 229, 0.1);
}

.session-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  font-size: 13px;
}

/* 聊天面板 */
.assistant-card.chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  animation-delay: 0.1s;
}

.assistant-messages {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 14px;
}

.message-row {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.message-row.user {
  justify-content: flex-end;
}

.message-avatar {
  flex-shrink: 0;
  border: 2px solid white;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  width: 36px;
  height: 36px;
}

.assistant-message {
  max-width: 75%;
  padding: 12px 16px;
  border-radius: 14px;
  line-height: 1.55;
  font-size: 14px;
  word-break: break-word;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.04);
}

/* Markdown Styles */
.markdown-body :deep(h1), .markdown-body :deep(h2), .markdown-body :deep(h3), .markdown-body :deep(h4) {
  margin-top: 10px;
  margin-bottom: 10px;
  font-weight: 700;
  color: #0f172a;
}
.markdown-body :deep(p) {
  margin-bottom: 10px;
}
.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}
.markdown-body :deep(ul), .markdown-body :deep(ol) {
  padding-left: 20px;
  margin-bottom: 10px;
}
.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 12px;
}
.markdown-body :deep(th), .markdown-body :deep(td) {
  border: 1px solid #e2e8f0;
  padding: 10px;
}
.markdown-body :deep(th) {
  background-color: #f8fafc;
}
.markdown-body :deep(blockquote) {
  margin: 0 0 12px 0;
  padding: 12px 16px;
  border-left: 4px solid #4f46e5;
  background-color: rgba(79, 70, 229, 0.05);
  color: #475569;
  border-radius: 0 8px 8px 0;
}
.markdown-body :deep(code) {
  background-color: rgba(15, 23, 42, 0.05);
  padding: 3px 6px;
  border-radius: 6px;
  font-family: monospace;
  color: #db2777;
}

.message-row.assistant .assistant-message, .message-row.system .assistant-message {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(12px);
  color: #334155;
  border-radius: 4px 20px 20px 20px;
  border: 1px solid rgba(255, 255, 255, 0.8);
}

.message-row.user .assistant-message {
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  color: white;
  border-radius: 20px 4px 20px 20px;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.25);
  white-space: pre-wrap;
}

/* 底部输入框 */
.assistant-input-area {
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.5);
  border-top: 1px solid rgba(255, 255, 255, 0.6);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

:deep(.assistant-input-area .el-textarea__inner) {
  border-radius: 12px;
  background-color: rgba(248, 250, 252, 0.8);
  box-shadow: 0 0 0 1px #cbd5e1 inset;
  padding: 10px 12px;
  font-size: 14px;
  min-height: 84px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  resize: none;
}

:deep(.assistant-input-area .el-textarea__inner:hover) {
  background-color: #ffffff;
  box-shadow: 0 0 0 1px #94a3b8 inset, 0 4px 12px rgba(0,0,0,0.02);
}

:deep(.assistant-input-area .el-textarea__inner:focus) {
  background-color: #ffffff;
  box-shadow: 0 0 0 2px #6366f1 inset, 0 8px 24px rgba(99, 102, 241, 0.15) !important;
}

.assistant-input-actions {
  display: flex;
  justify-content: flex-end;
}

.gradient-btn {
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  border: none;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.gradient-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.4);
}

.assistant-input-actions .el-button {
  padding: 0 20px;
  height: 36px;
  border-radius: 18px;
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.5px;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  border: none;
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.3);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  color: white;
}

.assistant-input-actions .el-button::before {
  content: '';
  position: absolute;
  top: 0; left: -100%; width: 50%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
  transform: skewX(-20deg);
  transition: all 0.5s;
}

.assistant-input-actions .el-button:not(.is-disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(99, 102, 241, 0.4);
}

.assistant-input-actions .el-button:not(.is-disabled):hover::before {
  left: 150%;
}
</style>
