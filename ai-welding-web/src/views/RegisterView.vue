<script setup lang="ts">
import { reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const { registerTeacher, loading } = useAuth()

const registerForm = reactive({
  identity_code: '',
  username: '',
  password: '',
  password_confirm: '',
})

const localError = ref('')

async function onSubmit() {
  localError.value = ''
  if (
    !registerForm.identity_code ||
    !registerForm.username ||
    !registerForm.password
  ) {
    localError.value = '请填写完整的注册信息'
    return
  }
  if (registerForm.password !== registerForm.password_confirm) {
    localError.value = '两次输入的密码不一致'
    return
  }

  const ok = await registerTeacher({
    identity_code: registerForm.identity_code,
    username: registerForm.username,
    password: registerForm.password,
  })
  if (ok) await router.replace({ name: 'login' })
}
</script>

<template>
  <div>
      <form class="form" @submit.prevent="onSubmit">
        <h2>教师注册</h2>
        <p class="tip register-lead">学生账号由管理员统一开通，无需在此注册。</p>
        <input v-model.trim="registerForm.identity_code" type="text" placeholder="教师身份编号" autocomplete="username" />
        <input v-model.trim="registerForm.username" type="text" placeholder="用户名" />
        <input v-model="registerForm.password" type="password" placeholder="登录密码" autocomplete="new-password" />
        <input v-model="registerForm.password_confirm" type="password" placeholder="确认密码" autocomplete="new-password" />

        <p v-if="localError" class="feedback error">{{ localError }}</p>

        <button class="primary" type="submit" :disabled="loading">{{ loading ? '提交中…' : '提交注册' }}</button>

        <p class="tip">提交后需管理员在 Django Admin 审核通过后方可登录。</p>

        <p class="auth-footer">
          <span>已有账号？</span>
          <RouterLink class="auth-link" to="/login">返回登录</RouterLink>
        </p>
      </form>
  </div>
</template>
