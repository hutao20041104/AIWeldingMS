<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, type UploadRequestOptions } from 'element-plus'
import { User, Message, Iphone, Camera, Postcard, Key, Loading } from '@element-plus/icons-vue'
import { API_BASE_URL, currentUser } from '../../composables/useAuth'
import defaultTeacherAvatar from '../../assets/default_teacher.png'

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
  return defaultTeacherAvatar
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
.module-page {
  min-height: calc(100vh - 92px);
  padding: 32px;
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
  box-sizing: border-box;
  overflow-y: auto;
  border-radius: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04);
}

@keyframes mesh-movement {
  0% { background-position: 0% 0%; }
  100% { background-position: 100% 100%; }
}

.profile-layout {
  max-width: 1080px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 32px;
}

.glass-card {
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 24px;
  box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.05), inset 0 0 0 1px rgba(255,255,255,0.5);
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
.glass-card:hover {
  box-shadow: 0 16px 48px 0 rgba(31, 38, 135, 0.08), inset 0 0 0 1px rgba(255,255,255,0.8);
  transform: translateY(-2px);
}

/* 左侧样式 */
.profile-side {
  display: flex;
  flex-direction: column;
}

.profile-banner {
  height: 140px;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  position: relative;
  overflow: hidden;
}
.profile-banner::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background-image: radial-gradient(circle at 20% 50%, rgba(255,255,255,0.2) 0%, transparent 50%),
                    radial-gradient(circle at 80% 90%, rgba(255,255,255,0.2) 0%, transparent 50%);
  opacity: 0.8;
}

.hero {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 32px 32px;
  margin-top: -60px;
  text-align: center;
}

.avatar-wrapper {
  position: relative;
  border-radius: 50%;
  padding: 6px;
  background: linear-gradient(135deg, #ffffff, #f8fafc);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  margin-bottom: 20px;
  transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.4s ease;
}
.avatar-wrapper:hover {
  transform: scale(1.05) translateY(-4px);
  box-shadow: 0 16px 40px rgba(79, 70, 229, 0.25);
}

.user-avatar {
  display: block;
}

.avatar-overlay {
  position: absolute;
  inset: 6px;
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(2px);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: all 0.3s ease;
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
  margin: 0 0 6px;
  font-size: 24px;
  color: #0f172a;
  font-weight: 800;
  letter-spacing: 0.5px;
}

.hero p {
  margin: 0 0 20px;
  color: #64748b;
  font-size: 15px;
}

.badges {
  margin-bottom: 24px;
}

.badge-role {
  padding: 0 20px;
  height: 32px;
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 1px;
  border: none;
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.1), rgba(124, 58, 237, 0.1));
  color: #6366f1;
  box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.2);
}

.meta-list {
  padding: 0 32px 32px;
}

.meta-item {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 16px;
  gap: 16px;
  transition: all 0.3s;
}
.meta-item:hover {
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 4px 12px rgba(0,0,0,0.02);
}

.meta-icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.meta-content {
  display: flex;
  flex-direction: column;
}

.meta-label {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 2px;
}

.meta-val {
  font-size: 16px;
  color: #1e293b;
  font-weight: 700;
  font-family: 'Courier New', monospace;
  letter-spacing: 0.5px;
}

/* 右侧样式 */
.profile-main {
  padding: 40px 48px;
}

.form-header {
  margin-bottom: 36px;
  position: relative;
}

.form-header h2 {
  margin: 0 0 10px;
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.5px;
  background: linear-gradient(135deg, #0f172a 0%, #4f46e5 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  display: inline-block;
}

.form-header p {
  margin: 0;
  color: #64748b;
  font-size: 15px;
}

/* 进场动画 */
@keyframes slideUpFade {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

.profile-side {
  display: flex;
  flex-direction: column;
  animation: slideUpFade 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.profile-main {
  padding: 40px 48px;
  animation: slideUpFade 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
  animation-delay: 0.15s;
}

/* 动态边框流光效果 */
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

/* 覆盖 Element Plus 表单样式 */
:deep(.custom-form .el-form-item) {
  margin-bottom: 28px;
}

:deep(.custom-form .el-form-item__label) {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
  padding-bottom: 8px;
  letter-spacing: 0.5px;
}

:deep(.custom-form .el-input__wrapper) {
  border-radius: 12px;
  background-color: rgba(248, 250, 252, 0.6);
  box-shadow: 0 0 0 1px #cbd5e1 inset;
  padding: 4px 16px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.custom-form .el-input__wrapper:hover) {
  background-color: #ffffff;
  box-shadow: 0 0 0 1px #94a3b8 inset, 0 4px 12px rgba(0,0,0,0.02);
}

:deep(.custom-form .el-input__wrapper.is-focus) {
  background-color: #ffffff;
  box-shadow: 0 0 0 2px #6366f1 inset, 0 8px 24px rgba(99, 102, 241, 0.15) !important;
  transform: translateY(-1px);
}

.form-help {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 6px;
  line-height: 1.4;
}

.actions {
  margin-top: 48px;
  display: flex;
  justify-content: flex-end;
}

.save-btn {
  padding: 0 48px;
  height: 48px;
  border-radius: 24px;
  font-weight: 600;
  font-size: 16px;
  letter-spacing: 1px;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  border: none;
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.3);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.save-btn::before {
  content: '';
  position: absolute;
  top: 0; left: -100%; width: 50%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
  transform: skewX(-20deg);
  transition: all 0.5s;
}

.save-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 28px rgba(99, 102, 241, 0.4);
}

.save-btn:hover::before {
  left: 150%;
}

@media (max-width: 960px) {
  .profile-layout {
    grid-template-columns: 1fr;
  }
  .profile-main {
    padding: 32px;
  }
}
</style>
