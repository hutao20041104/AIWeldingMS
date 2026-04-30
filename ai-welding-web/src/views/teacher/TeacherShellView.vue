<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  Collection,
  Connection,
  Cpu,
  DataAnalysis,
  Monitor,
  Setting,
  User,
  UserFilled,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { API_BASE_URL, currentUser, useAuth } from '../../composables/useAuth'
import logo from '../../assets/logo.png'

const route = useRoute()
const router = useRouter()
const { logout } = useAuth()

const menus = [
  { index: '/teacher/courses', title: '课程管理', icon: Collection },
  { index: '/teacher/students', title: '学生管理', icon: User },
  { index: '/teacher/grades', title: '成绩管理', icon: DataAnalysis },
  { index: '/teacher/labs', title: '实验监控', icon: Connection },
  { index: '/teacher/devices', title: '设备管理', icon: Monitor },
  { index: '/teacher/accounts', title: '账号管理', icon: Setting },
  { index: '/teacher/assistant', title: 'AI教学助手', icon: Cpu },
]

const activeMenu = computed(() => route.path)
const userAvatarSrc = computed(() => {
  const raw = currentUser.value?.avatar || ''
  if (raw) {
    if (/^https?:\/\//i.test(raw)) return raw
    return `${API_BASE_URL}${raw}`
  }
  const seed = currentUser.value?.identity_code || currentUser.value?.username || 'teacher'
  return `https://i.pravatar.cc/96?u=${encodeURIComponent(seed)}`
})

async function handleMenuSelect(index: string) {
  await router.push(index)
}

async function handleCommand(command: string) {
  if (command === 'settings') {
    ElMessage.info('设置功能将在后续细化')
    return
  }

  if (command === 'logout') {
    await logout()
    await router.replace({ name: 'login' })
  }
}
</script>

<template>
  <el-container class="layout-container-demo teacher-layout">
    <el-aside width="220px" class="teacher-sidebar">
      <div class="teacher-brand-inline">
        <img :src="logo" alt="logo" class="teacher-brand-logo" />
      </div>
      <div class="teacher-menu-wrap-vertical">
        <el-menu
          :default-active="activeMenu"
          class="teacher-menu-vertical"
          @select="handleMenuSelect"
        >
          <el-menu-item v-for="item in menus" :key="item.index" :index="item.index">
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.title }}</span>
          </el-menu-item>
        </el-menu>
      </div>
    </el-aside>

    <el-container>
      <el-header class="teacher-topbar">
        <div class="teacher-top-left"></div>
        <h2 class="teacher-top-center-title">AI焊接教学数字化管理平台</h2>

        <div class="teacher-userbar">
          <el-avatar :src="userAvatarSrc" :size="36" />
          <div class="teacher-usermeta">
            <strong>{{ currentUser?.username }}</strong>
            <span>{{ currentUser?.identity_code }}</span>
          </div>
          <el-dropdown @command="handleCommand">
            <span class="teacher-user-actions">
              <el-icon><Setting /></el-icon>
              <span>设置</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="settings">系统设置</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="teacher-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>
