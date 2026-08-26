import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { setUnauthorizedHandler } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || '{}'))

  // 计算属性
  const isLoggedIn = computed(() => !!token.value)
  const userRole = computed(() => user.value.role || '')
  const userId = computed(() => user.value.id || null)
  const isTeacherOrAdmin = computed(() => ['teacher', 'admin'].includes(user.value.role))

  // 401 时自动登出
  setUnauthorizedHandler(() => logout())

  // 登录
  async function login(username, password) {
    try {
      const response = await api.post('/users/login', { username, password })
      const { token: newToken, user: userData } = response.data

      token.value = newToken
      user.value = userData

      localStorage.setItem('token', newToken)
      localStorage.setItem('user', JSON.stringify(userData))

      return { success: true }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || '登录失败'
      }
    }
  }

  // 注册
  async function register(userData) {
    try {
      const response = await api.post('/users/register', userData)
      const { token: newToken, user: newUser } = response.data

      // 后端 register 当前不返回 token；这里做兼容
      if (newToken) {
        token.value = newToken
        user.value = newUser
        localStorage.setItem('token', newToken)
        localStorage.setItem('user', JSON.stringify(newUser))
      }

      return { success: true }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || '注册失败'
      }
    }
  }

  // 获取当前用户信息
  async function getCurrentUser() {
    if (!isLoggedIn.value) return null

    try {
      const response = await api.get('/users/me')
      user.value = response.data
      localStorage.setItem('user', JSON.stringify(response.data))
      return response.data
    } catch (error) {
      logout()
      return null
    }
  }

  // 登出
  function logout() {
    token.value = ''
    user.value = {}
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  // 更新用户信息
  async function updateUserInfo(userData) {
    try {
      const response = await api.put('/users/me', userData)
      user.value = response.data
      localStorage.setItem('user', JSON.stringify(response.data))
      return { success: true }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || '更新失败'
      }
    }
  }

  return {
    token,
    user,
    isLoggedIn,
    userRole,
    userId,
    isTeacherOrAdmin,
    login,
    register,
    logout,
    getCurrentUser,
    updateUserInfo
  }
})
