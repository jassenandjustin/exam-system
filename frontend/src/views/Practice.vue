<script setup>
import { useRouter, useRoute } from 'vue-router'
import { computed } from 'vue'

const router = useRouter()
const route = useRoute()

const modes = [
  { path: '/practice/sequential', label: '顺序练习', icon: 'EditPen' },
  { path: '/practice/random', label: '随机练习', icon: 'Refresh' },
  { path: '/practice/chapter', label: '章节练习', icon: 'Notebook' },
  { path: '/practice/error-review', label: '错题回顾', icon: 'Warning' },
  { path: '/practice/favorites', label: '收藏夹', icon: 'Star' }
]

const showHub = computed(() => route.path === '/practice')
</script>

<template>
  <div class="practice-page">
    <h2>刷题练习</h2>
    <el-tabs v-if="!showHub" :model-value="route.path" @tab-change="(p) => router.push(p)">
      <el-tab-pane v-for="m in modes" :key="m.path" :name="m.path" :label="m.label" />
    </el-tabs>

    <div v-if="showHub" class="hub">
      <el-row :gutter="16">
        <el-col v-for="m in modes" :key="m.path" :xs="24" :sm="12" :md="8">
          <el-card class="mode-card" shadow="hover" @click="router.push(m.path)">
            <el-icon :size="28"><component :is="m.icon" /></el-icon>
            <h3>{{ m.label }}</h3>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <router-view />
  </div>
</template>

<style scoped>
.practice-page {
  max-width: 1100px;
  margin: 0 auto;
}
.hub {
  margin-top: 16px;
}
.mode-card {
  margin-bottom: 16px;
  text-align: center;
  cursor: pointer;
  padding: 12px 0;
}
.mode-card h3 {
  margin: 8px 0 0;
  font-size: 16px;
}
</style>
