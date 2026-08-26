<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import QuestionRunner from '@/components/QuestionRunner.vue'

const questions = ref([])
const loading = ref(false)
const loaded = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/practice/favorites', { params: { page: 1, per_page: 30 } })
    questions.value = data.questions || []
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '加载收藏失败')
  } finally {
    loading.value = false
    loaded.value = true
  }
}

async function onFinish(summary) {
  await ElMessageBox.alert(
    `本次练习共 ${summary.total} 题，已答 ${summary.answered} 题，正确 ${summary.correct} 题，正确率 ${summary.accuracy}%`,
    '练习结束',
    { confirmButtonText: '好的' }
  ).catch(() => {})
  load()
}
function onExit() {
  load()
}

onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <QuestionRunner
      v-if="questions.length > 0"
      title="收藏夹"
      :questions="questions"
      @finish="onFinish"
      @exit="onExit"
    />
    <el-empty
      v-else-if="loaded"
      description="还没有收藏的题目，去其它模式刷题时点击 ⭐ 即可收藏"
    >
      <el-button type="primary" @click="$router.push('/practice/sequential')">去刷题</el-button>
    </el-empty>
  </div>
</template>
