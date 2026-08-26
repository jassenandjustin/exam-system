<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import PracticeSetup from '@/components/PracticeSetup.vue'
import QuestionRunner from '@/components/QuestionRunner.vue'

const stage = ref('setup')   // setup | running
const questions = ref([])
const loading = ref(false)
const meta = ref({ subject_id: null, chapter_id: null })

async function onStart(cfg) {
  loading.value = true
  try {
    const params = { subject_id: cfg.subject_id, page: 1, per_page: 20 }
    if (cfg.chapter_id) params.chapter_id = cfg.chapter_id
    const { data } = await api.get('/practice/sequential', { params })
    if (!data.questions || data.questions.length === 0) {
      ElMessage.info('没有更多未练习的题目了，建议尝试其它模式')
      return
    }
    questions.value = data.questions
    meta.value = cfg
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
      :show-chapter="true"
      @start="onStart"
    />
    <QuestionRunner
      v-else
      title="顺序练习"
      :questions="questions"
      @finish="onFinish"
      @exit="onExit"
    />
  </div>
</template>
