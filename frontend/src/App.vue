<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const isLoggedIn = computed(() => auth.isLoggedIn)
const username = computed(() => auth.user.username || '')

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <el-container class="app-shell">
    <el-header class="app-header">
      <div class="brand" @click="router.push('/')">
        <el-icon :size="22"><Reading /></el-icon>
        <span>智能刷题系统</span>
      </div>

      <el-menu
        mode="horizontal"
        :ellipsis="false"
        :default-active="route.path"
        router
        class="app-nav"
      >
        <el-menu-item index="/">首页</el-menu-item>
        <el-menu-item v-if="isLoggedIn" index="/practice">刷题</el-menu-item>
        <el-menu-item v-if="isLoggedIn" index="/exam">模拟考试</el-menu-item>
        <el-menu-item v-if="isLoggedIn && auth.isTeacherOrAdmin" index="/exam/teacher">试卷管理</el-menu-item>
        <el-menu-item v-if="isLoggedIn" index="/analysis">学习分析</el-menu-item>
        <el-menu-item v-if="auth.isTeacherOrAdmin" index="/admin">管理</el-menu-item>
      </el-menu>

      <div class="app-user">
        <template v-if="isLoggedIn">
          <el-dropdown>
            <span class="user-trigger">
              <el-icon><User /></el-icon>
              {{ username }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="router.push('/profile')">
                  <el-icon><UserFilled /></el-icon> 个人中心
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <template v-else>
          <el-button text @click="router.push('/login')">登录</el-button>
          <el-button type="primary" @click="router.push('/register')">注册</el-button>
        </template>
      </div>
    </el-header>

    <el-main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </el-main>

    <el-footer class="app-footer">
      <span>© 2026 智能刷题系统 · Vue 3 + Flask</span>
    </el-footer>
  </el-container>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
}
.app-header {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 0 24px;
  border-bottom: 1px solid var(--el-border-color-light);
  background: var(--el-bg-color);
}
.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  cursor: pointer;
  color: var(--el-color-primary);
  white-space: nowrap;
}
.app-nav {
  flex: 1;
  border-bottom: none !important;
}
.app-user {
  display: flex;
  align-items: center;
  gap: 8px;
}
.user-trigger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  color: var(--el-text-color-primary);
  outline: none;
}
.app-main {
  padding: 24px;
  background: var(--el-bg-color-page);
  min-height: calc(100vh - 60px - 50px);
}
.app-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  border-top: 1px solid var(--el-border-color-light);
  background: var(--el-bg-color);
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
