<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { currentUser, useAuth } from './composables/useAuth'

const route = useRoute()
const router = useRouter()
const { isLoggedIn, restoreSession, message, isError, logout, loading } = useAuth()

const booting = ref(true)

onMounted(async () => {
  await restoreSession()
  booting.value = false
  if (currentUser.value && (route.name === 'login' || route.name === 'register')) {
    if (currentUser.value.role === 'teacher') {
      await router.replace({ name: 'teacher-courses' })
    } else {
      await router.replace({ name: 'home' })
    }
  }
  if (!currentUser.value && route.meta.requiresAuth) {
    await router.replace({ name: 'login' })
  }
})

async function handleLogout() {
  await logout()
  await router.replace({ name: 'login' })
}
</script>

<template>
  <template v-if="route.meta.layout === 'dashboard'">
    <p v-if="booting" class="dashboard-booting">正在加载系统页面…</p>
    <router-view v-else />
  </template>

  <main v-else class="platform-auth">
    <section class="hero">
      <h1>AI焊接数字化教学管理平台</h1>
      <p class="hero-sub">智能教学、课程协同、实训评估与产教融合的统一入口</p>
    </section>

    <section class="auth-card">
      <p v-if="booting" class="auth-booting">正在校验登录状态…</p>

      <template v-else-if="isLoggedIn">
        <div class="welcome">
          <h2>欢迎回来，{{ currentUser?.username }}</h2>
          <p>身份编号：{{ currentUser?.identity_code }}</p>
          <p>
            当前身份：
            {{ currentUser?.role === 'teacher' ? '教师' : '学生' }}
            <span v-if="currentUser?.role === 'teacher'">
              （{{ currentUser?.is_approved ? '已审核' : '待审核' }}）
            </span>
          </p>
          <button class="primary" type="button" :disabled="loading" @click="handleLogout">
            {{ loading ? '退出中…' : '退出登录' }}
          </button>
        </div>
      </template>

      <router-view v-else v-slot="{ Component }">
        <transition name="fade-slide" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>

      <p v-if="message" :class="['feedback', { error: isError }]">{{ message }}</p>
    </section>
  </main>
</template>
