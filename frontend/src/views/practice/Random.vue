<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import PracticeSetup from '@/components/PracticeSetup.vue'
import QuestionRunner from '@/components/QuestionRunner.vue'

const stage = ref('setup')
const questions = ref([])
const loading = ref(false)

async function onStart(cfg) {
  loading.value = true
  try {
    const { data } = await api.get('/practice/random', {
      params: { subject_id: cfg.subject_id, count: cfg.count }
    })
    if (!data.questions || data.questions.length === 0) {
      ElMessage.info('该学科下暂无题目')
      return
    }
    questions.value = data.questions
    stage.value = 'running'
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '加载题目失败')
  } finally {
    loading.value = false
  }
}

async function onFinish(summary) {
  await ElMessageBox.alert(
    `本次练习共 ${summary.total} 题，已答 ${summary.answered} 题，正确 ${summary.correct} 题，正确率 ${summary.accuracy}%`,
    '练习结束',
    { confirmButtonText: '好的' }
  ).catch(() => {})
  stage.value = 'setup'
  questions.value = []
}
function onExit() {
  stage.value = 'setup'
  questions.value = []
}
</script>

<template>
  <div v-loading="loading">
    <PracticeSetup
      v-if="stage === 'setup'"
      :show-chapter="false"
      :show-count="true"
      @start="onStart"
    />
    <QuestionRunner
      v-else
      title="随机练习"
      :questions="questions"
      @finish="onFinish"
      @exit="onExit"
    />
  </div>
</template>
