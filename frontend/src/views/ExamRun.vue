<script setup>
/**
 * 模拟考试进行页：
 *  - 顶部固定倒计时；归零自动交卷
 *  - 左侧当前题（5 种题型），右侧题号网格导航
 *  - 自动 30s 暂存一次答案，避免刷新丢失
 */
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

const route = useRoute()
const router = useRouter()
const examId = Number(route.params.id)

const TYPE_LABEL = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  true_false: '判断题',
  fill_in_blank: '填空题',
  subjective: '主观题'
}
const TYPE_ORDER = ['single_choice', 'multiple_choice', 'true_false', 'fill_in_blank', 'subjective']
const DIFF_LABEL = {
  easy: { label: '简单', tag: 'success' },
  medium: { label: '中等', tag: 'warning' },
  hard: { label: '困难', tag: 'danger' }
}

const exam = ref(null)
const idx = ref(0)
const answers = reactive({})    // { qid: 用户答案 }
const loading = ref(false)
const submitting = ref(false)
const remaining = ref(0)         // 秒
let tickHandle = null
let saveHandle = null

const current = computed(() => exam.value?.questions?.[idx.value])
const total = computed(() => exam.value?.questions?.length || 0)
const answeredCount = computed(() =>
  Object.values(answers).filter(v => !isEmpty(v)).length)
const currentTypeNumber = computed(() => {
  if (!exam.value || !current.value) return 0
  return exam.value.questions
    .slice(0, idx.value + 1)
    .filter(q => q.question_type === current.value.question_type)
    .length
})

function sortQuestionsByType(questions) {
  return [...questions].sort((a, b) => {
    const typeDiff = TYPE_ORDER.indexOf(a.question_type) - TYPE_ORDER.indexOf(b.question_type)
    if (typeDiff !== 0) return typeDiff
    return (a.order_num || 0) - (b.order_num || 0)
  })
}

function isEmpty(v) {
  if (v === null || v === undefined || v === '') return true
  if (Array.isArray(v) && v.length === 0) return true
  return false
}

function defaultInput(q) {
  if (!q) return ''
  if (q.question_type === 'multiple_choice') return []
  if (q.question_type === 'true_false') return null
  return ''
}

async function loadExam() {
  loading.value = true
  try {
    const { data } = await api.get(`/exam/${examId}`)
    if (data.submitted) {
      ElMessage.info('该考试已提交，跳转到报告')
      router.replace(`/exam/result/${examId}`)
      return
    }
    exam.value = {
      ...data,
      questions: sortQuestionsByType(data.questions || [])
    }
    // 恢复已暂存的答案
    for (const q of exam.value.questions) {
      if (q.user_answer !== null && q.user_answer !== undefined) {
        answers[q.id] = q.user_answer
      } else {
        answers[q.id] = defaultInput(q)
      }
    }
    startTimer(data.deadline)
    startAutoSave()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '加载考试失败')
    router.replace('/exam')
  } finally {
    loading.value = false
  }
}

function startTimer(deadlineISO) {
  const update = () => {
    const left = Math.max(0, Math.floor((new Date(deadlineISO).getTime() - Date.now()) / 1000))
    remaining.value = left
    if (left === 0) {
      stopTimer()
      ElMessage.warning('考试时间到，自动交卷')
      submit(true)
    }
  }
  update()
  tickHandle = setInterval(update, 1000)
}
function stopTimer() {
  if (tickHandle) { clearInterval(tickHandle); tickHandle = null }
}

function startAutoSave() {
  // 30 秒暂存一次（不打扰用户）
  saveHandle = setInterval(() => { saveProgress(true) }, 30000)
}
function stopAutoSave() {
  if (saveHandle) { clearInterval(saveHandle); saveHandle = null }
}

function answerPayload() {
  return Object.entries(answers)
    .filter(([_, v]) => !isEmpty(v))
    .map(([qid, v]) => ({ question_id: Number(qid), user_answer: v }))
}

async function saveProgress(silent = false) {
  if (!exam.value || exam.value.submitted) return
  try {
    await api.post(`/exam/${examId}/save`, { answers: answerPayload() })
    if (!silent) ElMessage.success('已保存')
  } catch (err) {
    if (!silent) ElMessage.error('保存失败')
  }
}

async function submit(auto = false) {
  if (submitting.value) return
  if (!auto) {
    const unanswered = total.value - answeredCount.value
    try {
      await ElMessageBox.confirm(
        unanswered > 0
          ? `还有 ${unanswered} 道题未作答，确定交卷？`
          : '所有题目已作答，确定交卷？',
        '交卷',
        { confirmButtonText: '交卷', cancelButtonText: '再检查一下', type: 'warning' }
      )
    } catch { return }
  }

  submitting.value = true
  try {
    await api.post(`/exam/${examId}/submit`, { answers: answerPayload() })
    stopTimer()
    stopAutoSave()
    // 离开拦截会拿不到最新 submitted 状态，先把 exam 置为已提交
    if (exam.value) exam.value.submitted = true
    router.replace(`/exam/result/${examId}`)
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '交卷失败')
  } finally {
    submitting.value = false
  }
}

function jumpTo(i) { if (i >= 0 && i < total.value) idx.value = i }
function goPrev()   { if (idx.value > 0) idx.value-- }
function goNext()   { if (idx.value < total.value - 1) idx.value++ }

const remainingText = computed(() => {
  const s = remaining.value
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const ss = s % 60
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(ss).padStart(2, '0')}`
  return `${String(m).padStart(2, '0')}:${String(ss).padStart(2, '0')}`
})

const remainingClass = computed(() => {
  if (remaining.value <= 60) return 'danger'
  if (remaining.value <= 300) return 'warning'
  return ''
})

onBeforeRouteLeave(async (to, _from, next) => {
  if (!exam.value || exam.value.submitted) return next()
  try {
    await ElMessageBox.confirm(
      '考试还在进行中，离开页面将自动暂存答案但不会交卷，确定离开？',
      '提示',
      { confirmButtonText: '离开', cancelButtonText: '继续作答', type: 'warning' }
    )
    saveProgress(true)
    next()
  } catch {
    next(false)
  }
})

onMounted(loadExam)
onBeforeUnmount(() => {
  stopTimer()
  stopAutoSave()
})
</script>

<template>
  <div class="exam-run" v-loading="loading">
    <div v-if="exam" class="layout">
      <!-- 顶部条 -->
      <el-card class="topbar" shadow="never">
        <div class="topbar-left">
          <h3>{{ exam.exam_name || '模拟考试' }}</h3>
          <el-tag size="small">{{ exam.exam_type }}</el-tag>
          <el-tag size="small" type="info">共 {{ total }} 题</el-tag>
          <el-tag size="small" type="success">已答 {{ answeredCount }}</el-tag>
        </div>
        <div class="topbar-center" :class="['countdown', remainingClass]">
          <el-icon><Clock /></el-icon>
          <span>{{ remainingText }}</span>
        </div>
        <div class="topbar-right">
          <el-button :icon="'DocumentChecked'" @click="saveProgress(false)">保存进度</el-button>
          <el-button type="primary" :icon="'Promotion'" :loading="submitting" @click="submit(false)">
            交卷
          </el-button>
        </div>
      </el-card>

      <div class="body">
        <!-- 答题区 -->
        <el-card class="qcard">
          <div v-if="current" class="qhead">
            <el-tag size="small">{{ TYPE_LABEL[current.question_type] }}</el-tag>
            <el-tag :type="DIFF_LABEL[current.difficulty]?.tag" effect="light" size="small">
              {{ DIFF_LABEL[current.difficulty]?.label || current.difficulty }}
            </el-tag>
            <span class="score">{{ current.score }} 分</span>
          </div>
          <div v-if="current" class="qtitle">
            {{ TYPE_LABEL[current.question_type] }}第 {{ currentTypeNumber }} 题. {{ current.title }}
          </div>
          <div v-if="current?.content" class="qcontent">{{ current.content }}</div>

          <template v-if="current">
            <el-radio-group
              v-if="current.question_type === 'single_choice'"
              v-model="answers[current.id]"
              class="opts"
            >
              <el-radio
                v-for="(opt, i) in current.options"
                :key="i"
                :value="opt"
              >
                <span class="opt-letter">{{ String.fromCharCode(65 + i) }}.</span> {{ opt }}
              </el-radio>
            </el-radio-group>

            <el-checkbox-group
              v-else-if="current.question_type === 'multiple_choice'"
              v-model="answers[current.id]"
              class="opts"
            >
              <el-checkbox
                v-for="(opt, i) in current.options"
                :key="i"
                :value="opt"
              >
                <span class="opt-letter">{{ String.fromCharCode(65 + i) }}.</span> {{ opt }}
              </el-checkbox>
            </el-checkbox-group>

            <el-radio-group v-else-if="current.question_type === 'true_false'" v-model="answers[current.id]">
              <el-radio :value="true">正确</el-radio>
              <el-radio :value="false">错误</el-radio>
            </el-radio-group>

            <el-input
              v-else-if="current.question_type === 'fill_in_blank'"
              v-model="answers[current.id]"
              placeholder="请输入答案"
            />
            <el-input
              v-else
              v-model="answers[current.id]"
              type="textarea"
              :rows="5"
              placeholder="请作答"
            />
          </template>

          <div class="actions">
            <el-button :disabled="idx === 0" @click="goPrev">上一题</el-button>
            <el-button v-if="idx < total - 1" type="primary" @click="goNext">下一题</el-button>
            <el-button v-else type="success" :loading="submitting" @click="submit(false)">交卷</el-button>
          </div>
        </el-card>

        <!-- 题号导航 -->
        <el-card class="navbar">
          <div class="nav-title">题号</div>
          <div class="nav-groups">
            <div v-for="type in TYPE_ORDER" :key="type" class="nav-group">
              <div v-if="exam.questions.some(q => q.question_type === type)" class="nav-type-title">
                {{ TYPE_LABEL[type] }}
              </div>
              <div class="nav-grid">
                <span
                  v-for="(q, i) in exam.questions"
                  v-show="q.question_type === type"
                  :key="q.id"
                  class="nav-cell"
                  :class="{
                    active: i === idx,
                    answered: !isEmpty(answers[q.id])
                  }"
                  @click="jumpTo(i)"
                >{{ exam.questions.slice(0, i + 1).filter(x => x.question_type === q.question_type).length }}</span>
              </div>
            </div>
          </div>
          <div class="nav-legend">
            <span><i class="dot answered"></i> 已答</span>
            <span><i class="dot"></i> 未答</span>
            <span><i class="dot active"></i> 当前</span>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<style scoped>
.exam-run {
  max-width: 1200px;
  margin: 0 auto;
}
.topbar {
  display: block;
  margin-bottom: 12px;
}
.topbar :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 12px;
}
.topbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}
.topbar-left h3 {
  margin: 0 8px 0 0;
}
.topbar-center {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 22px;
  font-weight: 600;
  color: var(--el-color-primary);
  font-variant-numeric: tabular-nums;
}
.topbar-center.warning { color: var(--el-color-warning); }
.topbar-center.danger {
  color: var(--el-color-danger);
  animation: blink 1s infinite;
}
@keyframes blink {
  50% { opacity: 0.55; }
}
.topbar-right {
  display: flex;
  gap: 8px;
}
.body {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 16px;
}
.qcard {
  text-align: left;
}
.qhead {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  color: var(--el-text-color-secondary);
}
.qhead .score {
  margin-left: auto;
  font-size: 13px;
}
.qtitle {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  white-space: pre-wrap;
}
.qcontent {
  color: var(--el-text-color-secondary);
  margin-bottom: 12px;
  white-space: pre-wrap;
}
.opts {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  width: 100%;
  margin-top: 18px;
}
.opts :deep(.el-radio),
.opts :deep(.el-checkbox) {
  display: flex;
  align-items: flex-start;
  width: 100%;
  margin: 0;
  text-align: left;
  white-space: normal;
}
.opts :deep(.el-radio__label),
.opts :deep(.el-checkbox__label) {
  white-space: normal;
  word-break: break-word;
  flex: 1;
}
.opt-letter {
  font-weight: 600;
  margin-right: 4px;
}
.actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.navbar .nav-title {
  font-weight: 600;
  margin-bottom: 8px;
}
.nav-groups {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.nav-type-title {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}
.nav-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.nav-cell {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  border: 1px solid var(--el-border-color);
  cursor: pointer;
  font-size: 13px;
  user-select: none;
}
.nav-cell.answered {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}
.nav-cell.active {
  outline: 2px solid var(--el-color-primary);
}
.nav-legend {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 12px;
}
.nav-legend .dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
  border: 1px solid var(--el-border-color);
  margin-right: 4px;
  vertical-align: middle;
}
.nav-legend .dot.answered {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);
}
.nav-legend .dot.active {
  outline: 2px solid var(--el-color-primary);
}
@media (max-width: 768px) {
  .body { grid-template-columns: 1fr; }
}
</style>
