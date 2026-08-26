<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const isLoggedIn = computed(() => auth.isLoggedIn)

const features = [
  {
    icon: 'EditPen',
    title: '顺序练习',
    desc: '按章节顺序刷题，巩固基础知识点',
    path: '/practice/sequential'
  },
  {
    icon: 'Refresh',
    title: '随机练习',
    desc: '随机出题，全方位检测掌握情况',
    path: '/practice/random'
  },
  {
    icon: 'Warning',
    title: '错题回顾',
    desc: '专门重做错过的题目，针对性提升',
    path: '/practice/error-review'
  },
  {
    icon: 'Star',
    title: '收藏夹',
    desc: '收藏的精选题目，随时回看',
    path: '/practice/favorites'
  },
  {
    icon: 'Document',
    title: '模拟考试',
    desc: '限时考试，真实模考体验',
    path: '/exam'
  },
  {
    icon: 'DataAnalysis',
    title: '学习分析',
    desc: '数据可视化，找出薄弱知识点',
    path: '/analysis'
  }
]

function go(path) {
  if (!isLoggedIn.value) {
    router.push('/login')
    return
  }
  router.push(path)
}
</script>

<template>
  <div class="home">
    <section class="hero">
      <h1>智能刷题，让学习更高效</h1>
      <p class="tagline">多题型支持 · 智能推荐 · 学习分析 · 错题回顾</p>
      <div class="cta">
        <el-button v-if="!isLoggedIn" type="primary" size="large" @click="router.push('/register')">
          立即开始
        </el-button>
        <el-button v-if="!isLoggedIn" size="large" @click="router.push('/login')">登录</el-button>
        <el-button v-else type="primary" size="large" @click="router.push('/practice/sequential')">
          开始刷题
        </el-button>
      </div>
    </section>

    <section class="features">
      <el-row :gutter="20">
        <el-col v-for="f in features" :key="f.title" :xs="24" :sm="12" :md="8">
          <el-card class="feature-card" shadow="hover" @click="go(f.path)">
            <el-icon :size="32" class="feature-icon"><component :is="f.icon" /></el-icon>
            <h3>{{ f.title }}</h3>
            <p>{{ f.desc }}</p>
          </el-card>
        </el-col>
      </el-row>
    </section>
  </div>
</template>

<style scoped>
.home {
  max-width: 1100px;
  margin: 0 auto;
}
.hero {
  text-align: center;
  padding: 48px 16px 56px;
}
.hero h1 {
  font-size: 36px;
  margin: 0 0 12px;
  color: var(--el-text-color-primary);
}
.tagline {
  font-size: 16px;
  color: var(--el-text-color-secondary);
  margin: 0 0 28px;
}
.cta {
  display: flex;
  gap: 12px;
  justify-content: center;
}
.features {
  margin-top: 16px;
}
.feature-card {
  margin-bottom: 20px;
  cursor: pointer;
  transition: transform 0.15s ease;
  text-align: center;
}
.feature-card:hover {
  transform: translateY(-2px);
}
.feature-icon {
  color: var(--el-color-primary);
  margin-bottom: 8px;
}
.feature-card h3 {
  margin: 8px 0 6px;
  font-size: 17px;
}
.feature-card p {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}
</style>
