<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, type UploadRequestOptions } from 'element-plus'
import { API_BASE_URL, currentUser } from '../../composables/useAuth'

const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const form = ref({
  identity_code: '',
  role: '',
  username: '',
  email: '',
  tel: '',
  avatar: '',
})

function authHeaders() {
  const token = localStorage.getItem('access_token')
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

function avatarUrl() {
  if (form.value.avatar) {
    if (/^https?:\/\//i.test(form.value.avatar)) return form.value.avatar
    return `${API_BASE_URL}${form.value.avatar}`
  }
  return 'https://i.pravatar.cc/160?u=teacher-profile'
}

async function fetchProfile() {
  loading.value = true
  try {
    const res = await fetch(`${API_BASE_URL}/api/auth/whoami`, { headers: { ...authHeaders() } })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '获取个人信息失败')
      return
    }
    form.value = {
      identity_code: data.identity_code || '',
      role: data.role || '',
      username: data.username || '',
      email: data.email || '',
      tel: data.tel || '',
      avatar: data.avatar || '',
    }
    currentUser.value = data
  } catch {
    ElMessage.error('网络异常，获取个人信息失败')
  } finally {
    loading.value = false
  }
}

async function saveProfile() {
  if (!form.value.username.trim()) {
    ElMessage.warning('用户名不能为空')
    return
  }
  saving.value = true
  try {
    const res = await fetch(`${API_BASE_URL}/api/auth/profile`, {
      method: 'PUT',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: form.value.username.trim(),
        email: form.value.email.trim(),
        tel: form.value.tel.trim(),
      }),
    })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '保存失败')
      return
    }
    ElMessage.success('个人信息已更新')
    form.value.username = data.username || form.value.username
    form.value.email = data.email || ''
    form.value.tel = data.tel || ''
    currentUser.value = data
  } catch {
    ElMessage.error('网络异常，保存失败')
  } finally {
    saving.value = false
  }
}

async function uploadAvatar(options: UploadRequestOptions) {
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('avatar', options.file)
    const res = await fetch(`${API_BASE_URL}/api/auth/profile/avatar`, {
      method: 'POST',
      headers: { ...authHeaders() },
      body: fd,
    })
    const data = await res.json()
    if (!res.ok) {
      ElMessage.error(data.message || '上传头像失败')
      return
    }
    form.value.avatar = data.avatar || ''
    currentUser.value = data
    ElMessage.success('头像已更新')
  } catch {
    ElMessage.error('网络异常，上传头像失败')
  } finally {
    uploading.value = false
  }
}

onMounted(() => {
  fetchProfile()
})
</script>

<template>
  <section class="module-page" v-loading="loading">
    <div class="profile-layout">
      <el-card class="profile-side" shadow="hover">
        <div class="hero">
          <el-avatar :size="112" :src="avatarUrl()" />
          <h3>{{ form.username || '教师账号' }}</h3>
          <p>{{ form.email || '未设置邮箱' }}</p>
        </div>
        <el-upload :show-file-list="false" :http-request="uploadAvatar" accept=".jpg,.jpeg,.png,.webp" class="upload-btn">
          <el-button :loading="uploading" round>更换头像</el-button>
        </el-upload>
        <div class="meta-list">
          <div><span>身份编号</span><b>{{ form.identity_code }}</b></div>
          <div><span>角色</span><b>{{ form.role === 'teacher' ? '教师' : form.role }}</b></div>
        </div>
      </el-card>

      <el-card class="profile-main" shadow="hover">
        <div class="form-title">个人信息维护</div>
        <el-form label-width="90px" class="profile-form">
          <el-form-item label="用户名">
            <el-input v-model="form.username" placeholder="请输入用户名" />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="form.email" placeholder="请输入邮箱" />
          </el-form-item>
          <el-form-item label="手机号">
            <el-input v-model="form.tel" placeholder="请输入手机号" maxlength="11" />
          </el-form-item>
        </el-form>
        <div class="actions">
          <el-button type="primary" :loading="saving" @click="saveProfile" round>保存修改</el-button>
        </div>
      </el-card>
    </div>
  </section>
</template>

<style scoped>
.profile-layout {
  max-width: 980px;
  margin: 24px auto;
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
}
.profile-side {
  border-radius: 18px;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.95), rgba(240, 248, 255, 0.92));
}
.hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 8px;
  padding: 10px 0 14px;
}
.hero h3 {
  margin: 8px 0 0;
  font-size: 22px;
}
.hero p {
  margin: 0;
  color: #64748b;
}
.upload-btn {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}
.meta-list {
  display: grid;
  gap: 10px;
}
.meta-list > div {
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(59, 130, 246, 0.08);
  display: flex;
  justify-content: space-between;
}
.meta-list span {
  color: #64748b;
}
.profile-main {
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.98);
}
.form-title {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 16px;
}
.profile-form {
  padding-top: 8px;
}
.actions {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}
@media (max-width: 920px) {
  .profile-layout {
    grid-template-columns: 1fr;
  }
}
</style>
