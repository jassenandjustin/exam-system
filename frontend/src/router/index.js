import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// 路由配置
const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/practice',
    name: 'Practice',
    component: () => import('@/views/Practice.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: 'sequential',
        name: 'SequentialPractice',
        component: () => import('@/views/practice/Sequential.vue')
      },
      {
        path: 'random',
        name: 'RandomPractice',
        component: () => import('@/views/practice/Random.vue')
      },
      {
        path: 'error-review',
        name: 'ErrorReview',
        component: () => import('@/views/practice/ErrorReview.vue')
      },
      {
        path: 'favorites',
        name: 'Favorites',
        component: () => import('@/views/practice/Favorites.vue')
      },
      {
        path: 'chapter',
        name: 'ChapterPractice',
        component: () => import('@/views/practice/Chapter.vue')
      }
    ]
  },
  {
    path: '/exam',
    name: 'Exam',
    component: () => import('@/views/Exam.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/exam/run/:id',
    name: 'ExamRun',
    component: () => import('@/views/ExamRun.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/exam/result/:id',
    name: 'ExamResult',
    component: () => import('@/views/ExamResult.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/exam/teacher',
    name: 'ExamTeacher',
    component: () => import('@/views/exam/TeacherDashboard.vue'),
    meta: { requiresAuth: true, requiresTeacher: true }
  },
  {
    path: '/exam/paper/create',
    name: 'ExamPaperCreate',
    component: () => import('@/views/exam/PaperForm.vue'),
    meta: { requiresAuth: true, requiresTeacher: true }
  },
  {
    path: '/exam/paper/:id/edit',
    name: 'ExamPaperEdit',
    component: () => import('@/views/exam/PaperForm.vue'),
    meta: { requiresAuth: true, requiresTeacher: true }
  },
  {
    path: '/exam/paper/:id/manage',
    name: 'ExamPaperManage',
    component: () => import('@/views/exam/PaperManage.vue'),
    meta: { requiresAuth: true, requiresTeacher: true }
  },
  {
    path: '/analysis',
    name: 'Analysis',
    component: () => import('@/views/Analysis.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/Profile.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('@/views/Admin.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  // 检查是否需要登录
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    next('/login')
    return
  }

  // 检查是否需要管理员权限
  if (to.meta.requiresAdmin && authStore.userRole !== 'admin') {
    next('/')
    return
  }

  // 检查是否需要教师/管理员权限
  if (to.meta.requiresTeacher && !authStore.isTeacherOrAdmin) {
    next('/')
    return
  }

  // 已登录用户不能访问登录和注册页面
  if (authStore.isLoggedIn && (to.path === '/login' || to.path === '/register')) {
    next('/')
    return
  }

  next()
})

export default router
