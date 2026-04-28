<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { currentUser } from '../composables/useAuth'

const router = useRouter()

onMounted(async () => {
  if (currentUser.value?.role === 'teacher') {
    await router.replace({ name: 'teacher-courses' })
  }
})
</script>

<template>
  <div class="dashboard-empty-state">
    正在进入系统主页...
  </div>
</template>
