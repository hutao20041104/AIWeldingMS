import { createRouter, createWebHistory } from 'vue-router'
import { currentUser } from '../composables/useAuth'
import HomeView from '../views/HomeView.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import TeacherShellView from '../views/teacher/TeacherShellView.vue'
import TeacherCourseManagementView from '../views/teacher/TeacherCourseManagementView.vue'
import TeacherStudentManagementView from '../views/teacher/TeacherStudentManagementView.vue'
import TeacherGradeManagementView from '../views/teacher/TeacherGradeManagementView.vue'
import TeacherLabMonitorView from '../views/teacher/TeacherLabMonitorView.vue'
import TeacherDeviceManagementView from '../views/teacher/TeacherDeviceManagementView.vue'
import TeacherAccountManagementView from '../views/teacher/TeacherAccountManagementView.vue'
import TeacherAiAssistantView from '../views/teacher/TeacherAiAssistantView.vue'

function hasStoredToken() {
  return !!(
    localStorage.getItem('access_token') || localStorage.getItem('refresh_token')
  )
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { requiresAuth: true, layout: 'dashboard' },
    },
    {
      path: '/teacher',
      component: TeacherShellView,
      meta: { requiresAuth: true, roles: ['teacher'], layout: 'dashboard' },
      children: [
        {
          path: '',
          redirect: { name: 'teacher-courses' },
        },
        {
          path: 'courses',
          name: 'teacher-courses',
          component: TeacherCourseManagementView,
          meta: { requiresAuth: true, roles: ['teacher'], layout: 'dashboard', title: '课程管理' },
        },
        {
          path: 'students',
          name: 'teacher-students',
          component: TeacherStudentManagementView,
          meta: { requiresAuth: true, roles: ['teacher'], layout: 'dashboard', title: '学生管理' },
        },
        {
          path: 'grades',
          name: 'teacher-grades',
          component: TeacherGradeManagementView,
          meta: { requiresAuth: true, roles: ['teacher'], layout: 'dashboard', title: '成绩管理' },
        },
        {
          path: 'labs',
          name: 'teacher-labs',
          component: TeacherLabMonitorView,
          meta: { requiresAuth: true, roles: ['teacher'], layout: 'dashboard', title: '实验监控' },
        },
        {
          path: 'devices',
          name: 'teacher-devices',
          component: TeacherDeviceManagementView,
          meta: { requiresAuth: true, roles: ['teacher'], layout: 'dashboard', title: '设备管理' },
        },
        {
          path: 'accounts',
          name: 'teacher-accounts',
          component: TeacherAccountManagementView,
          meta: { requiresAuth: true, roles: ['teacher'], layout: 'dashboard', title: '账号管理' },
        },
        {
          path: 'assistant',
          name: 'teacher-assistant',
          component: TeacherAiAssistantView,
          meta: { requiresAuth: true, roles: ['teacher'], layout: 'dashboard', title: 'AI教学助手' },
        },
      ],
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { guestOnly: true, layout: 'auth' },
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterView,
      meta: { guestOnly: true, layout: 'auth' },
    },
    { path: '/:pathMatch(.*)*', redirect: { name: 'login' } },
  ],
})

router.beforeEach((to) => {
  if (to.meta.guestOnly && currentUser.value) {
    if (currentUser.value.role === 'teacher') {
      return { name: 'teacher-courses' }
    }
    return { name: 'home' }
  }
  if (to.meta.requiresAuth && !hasStoredToken()) {
    return { name: 'login' }
  }
  const allowedRoles = Array.isArray(to.meta.roles) ? (to.meta.roles as string[]) : []
  if (allowedRoles.length > 0 && currentUser.value && !allowedRoles.includes(currentUser.value.role)) {
    if (currentUser.value.role === 'teacher') {
      return { name: 'teacher-courses' }
    }
    return { name: 'home' }
  }
})

export default router
