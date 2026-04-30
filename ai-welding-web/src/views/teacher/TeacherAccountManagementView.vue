<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, type UploadRequestOptions } from 'element-plus'
import { User, Message, Iphone, Camera, Postcard, Key, Loading } from '@element-plus/icons-vue'
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
      <!-- 左侧：个人信息展示卡片 -->
      <div class="profile-side glass-card">
        <div class="profile-banner"></div>
        <div class="hero">
          <div class="avatar-wrapper">
            <el-avatar :size="120" :src="avatarUrl()" class="user-avatar" />
            <el-upload 
              :show-file-list="false" 
              :http-request="uploadAvatar" 
              accept=".jpg,.jpeg,.png,.webp" 
              class="avatar-uploader"
              :disabled="uploading"
            >
              <div class="avatar-overlay">
                <el-icon :size="24" class="is-loading" v-if="uploading"><Loading /></el-icon>
                <el-icon :size="24" v-else><Camera /></el-icon>
              </div>
            </el-upload>
          </div>
          <h3>{{ form.username || '未知用户' }}</h3>
          <p>{{ form.email || '未设置邮箱' }}</p>
          
          <div class="badges">
            <el-tag effect="light" round class="badge-role">
              {{ form.role === 'teacher' ? '教师' : form.role || '用户' }}
            </el-tag>
          </div>
        </div>
        
        <div class="meta-list">
          <div class="meta-item">
            <div class="meta-icon"><el-icon><Postcard /></el-icon></div>
            <div class="meta-content">
              <span class="meta-label">身份编号</span>
              <span class="meta-val">{{ form.identity_code || '暂无' }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：表单维护卡片 -->
      <div class="profile-main glass-card">
        <div class="form-header">
          <h2>个人资料设置</h2>
          <p>管理您的基本信息和联系方式</p>
        </div>
        
        <el-form label-position="top" class="custom-form">
          <div class="form-row">
            <el-form-item label="登录账号(工号)">
              <el-input :model-value="form.identity_code" disabled size="large">
                <template #prefix><el-icon><Key /></el-icon></template>
              </el-input>
              <div class="form-help">不可修改</div>
            </el-form-item>
          </div>

          <div class="form-row">
            <el-form-item label="姓名/显示名称">
              <el-input v-model="form.username" placeholder="请输入显示名称" size="large">
                <template #prefix><el-icon><User /></el-icon></template>
              </el-input>
            </el-form-item>
          </div>
          
          <div class="form-row">
            <el-form-item label="邮箱地址">
              <el-input v-model="form.email" placeholder="请输入电子邮箱" size="large">
                <template #prefix><el-icon><Message /></el-icon></template>
              </el-input>
            </el-form-item>
          </div>
          
          <div class="form-row">
            <el-form-item label="联系电话">
              <el-input v-model="form.tel" placeholder="请输入手机号" maxlength="11" size="large">
                <template #prefix><el-icon><Iphone /></el-icon></template>
              </el-input>
            </el-form-item>
          </div>
        </el-form>
        
        <div class="actions">
          <el-button type="primary" size="large" :loading="saving" @click="saveProfile" class="save-btn">
            保存更改
          </el-button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.profile-layout {
  max-width: 1000px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 24px;
  padding-top: 20px;
}

.glass-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 20px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.04);
  overflow: hidden;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.glass-card:hover {
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.06);
}

/* 左侧样式 */
.profile-side {
  display: flex;
  flex-direction: column;
}

.profile-banner {
  height: 120px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  position: relative;
}

.hero {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 24px 24px;
  margin-top: -60px;
  text-align: center;
}

.avatar-wrapper {
  position: relative;
  border-radius: 50%;
  padding: 4px;
  background: #fff;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  margin-bottom: 16px;
}

.user-avatar {
  display: block;
}

.avatar-overlay {
  position: absolute;
  inset: 4px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s;
  cursor: pointer;
}

.avatar-uploader {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  overflow: hidden;
}

.avatar-uploader:hover .avatar-overlay {
  opacity: 1;
}

.hero h3 {
  margin: 0 0 4px;
  font-size: 22px;
  color: #1e293b;
  font-weight: 700;
}

.hero p {
  margin: 0 0 16px;
  color: #64748b;
  font-size: 14px;
}

.badges {
  margin-bottom: 20px;
}

.badge-role {
  padding: 0 16px;
  height: 28px;
  font-weight: 600;
  border: none;
  background-color: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.meta-list {
  padding: 0 24px 24px;
}

.meta-item {
  display: flex;
  align-items: center;
  padding: 16px;
  background: #f8fafc;
  border-radius: 16px;
  gap: 16px;
}

.meta-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: #fff;
  color: #3b82f6;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.meta-content {
  display: flex;
  flex-direction: column;
}

.meta-label {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 2px;
}

.meta-val {
  font-size: 15px;
  color: #334155;
  font-weight: 600;
  font-family: 'Courier New', monospace;
}

/* 右侧样式 */
.profile-main {
  padding: 32px 40px;
}

.form-header {
  margin-bottom: 30px;
}

.form-header h2 {
  margin: 0 0 8px;
  font-size: 24px;
  color: #0f172a;
}

.form-header p {
  margin: 0;
  color: #64748b;
  font-size: 14px;
}

/* 覆盖 Element Plus 表单样式 */
:deep(.custom-form .el-form-item__label) {
  font-weight: 600;
  color: #475569;
  padding-bottom: 6px;
}

:deep(.custom-form .el-input__wrapper) {
  border-radius: 10px;
  box-shadow: 0 0 0 1px #e2e8f0 inset;
  background-color: #f8fafc;
  padding: 0 16px;
  transition: all 0.3s;
}

:deep(.custom-form .el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #cbd5e1 inset;
}

:deep(.custom-form .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #3b82f6 inset, 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
  background-color: #fff;
}

.form-row {
  margin-bottom: 20px;
}

.form-help {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
  line-height: 1.2;
}

.actions {
  margin-top: 40px;
  display: flex;
  justify-content: flex-end;
}

.save-btn {
  padding: 0 36px;
  border-radius: 12px;
  font-weight: 600;
  letter-spacing: 1px;
  box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4);
  transition: all 0.3s;
}

.save-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5);
}

@media (max-width: 920px) {
  .profile-layout {
    grid-template-columns: 1fr;
  }
  .profile-main {
    padding: 24px;
  }
}
</style>
