<script setup lang="ts">
import { reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import type { Role } from '../composables/useAuth'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const { login, loading } = useAuth()

const role = ref<Role>('student')

const loginForm = reactive({
  identity_code: '',
  password: '',
})

async function onSubmit() {
  const ok = await login(
    {
      identity_code: loginForm.identity_code,
      password: loginForm.password,
    },
    role.value,
  )
  if (ok) await router.replace({ name: 'teacher-courses' })
}
</script>

<template>
  <div>
    <div class="role-picker">
      <span>登录身份</span>
      <label><input v-model="role" type="radio" value="student" /> 学生</label>
      <label><input v-model="role" type="radio" value="teacher" /> 教师</label>
    </div>

      <form class="form" @submit.prevent="onSubmit">
        <h2>账号登录</h2>
        <input v-model.trim="loginForm.identity_code" type="text" placeholder="身份编号" autocomplete="username" />
        <input v-model="loginForm.password" type="password" placeholder="密码" autocomplete="current-password" />
        <button class="primary" type="submit" :disabled="loading">{{ loading ? '登录中…' : '登录' }}</button>

        <p class="auth-footer">
          <span>我是教师，还没有账号？</span>
          <RouterLink class="auth-link" to="/register">前往教师注册</RouterLink>
        </p>
      </form>
  </div>
</template>
