<script setup>
/**
 * 考试报告页：
 *  - 顶部得分概览（得分 / 满分 / 正确率 / 用时）
 *  - 逐题回顾：用户答案 vs 正确答案 + 解析
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'

const route = useRoute()
const router = useRouter()
const examId = Number(route.params.id)

const exam = ref(null)
const loading = ref(false)
const filter = ref('all')   // all | wrong | right | unanswered

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

async function load() {
  loading.value = true
  try {
    const { data } = await api.get(`/exam/${examId}`)
    if (!data.submitted) {
      ElMessage.info('考试尚未提交，跳转到答题页')
      router.replace(`/exam/run/${examId}`)
      return
    }
    exam.value = {
      ...data,
      questions: sortQuestionsByType(data.questions || [])
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '加载报告失败')
    router.replace('/exam')
  } finally {
    loading.value = false
  }
}

function sortQuestionsByType(questions) {
  return [...questions].sort((a, b) => {
    const typeDiff = TYPE_ORDER.indexOf(a.question_type) - TYPE_ORDER.indexOf(b.question_type)
    if (typeDiff !== 0) return typeDiff
    return (a.order_num || 0) - (b.order_num || 0)
  })
}

function questionTypeNumber(list, index) {
  const q = list[index]
  if (!q) return 0
  return list.slice(0, index + 1).filter(item => item.question_type === q.question_type).length
}

function fmtAnswer(q, val) {
  if (val === null || val === undefined || val === '') return '（未作答）'
  if (q.question_type === 'multiple_choice') {
    return Array.isArray(val) ? val.join(' / ') : String(val)
  }
  if (q.question_type === 'true_false') {
    return val === true || val === 'true' ? '正确' : '错误'
  }
  return Array.isArray(val) ? val.join(' / ') : String(val)
}

const accuracy = computed(() => {
  if (!exam.value) return 0
  const t = exam.value.total_questions || 0
  return t > 0 ? Math.round(exam.value.correct_count / t * 100) : 0
})

const usedSec = computed(() => {
  if (!exam.value?.submitted_at) return 0
  return Math.floor(
    (new Date(exam.value.submitted_at).getTime() -
     new Date(exam.value.started_at).getTime()) / 1000
  )
})

function fmtDur(sec) {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m} 分 ${String(s).padStart(2, '0')} 秒`
}

const filtered = computed(() => {
  if (!exam.value) return []
  const list = exam.value.questions
  switch (filter.value) {
    case 'wrong':
      return list.filter(q => !q.is_correct && q.user_answer !== null)
    case 'right':
      return list.filter(q => q.is_correct)
    case 'unanswered':
      return list.filter(q => q.user_answer === null || q.user_answer === undefined || q.user_answer === '')
    default:
      return list
  }
})

const counts = computed(() => {
  if (!exam.value) return { right: 0, wrong: 0, unanswered: 0 }
  let right = 0, wrong = 0, unanswered = 0
  for (const q of exam.value.questions) {
    if (q.user_answer === null || q.user_answer === undefined || q.user_answer === '') unanswered++
    else if (q.is_correct) right++
    else wrong++
  }
  return { right, wrong, unanswered }
})

function isCorrectOption(q, opt) {
  if (q.question_type === 'single_choice') return q.correct_answer === opt
  if (q.question_type === 'multiple_choice') {
    return Array.isArray(q.correct_answer) && q.correct_answer.includes(opt)
  }
  return false
}
function isUserOption(q, opt) {
  if (q.question_type === 'single_choice') return q.user_answer === opt
  if (q.question_type === 'multiple_choice') {
    return Array.isArray(q.user_answer) && q.user_answer.includes(opt)
  }
  return false
}

onMounted(load)
</script>

<template>
  <div class="exam-result" v-loading="loading">
    <div v-if="exam">
      <!-- 概览 -->
      <el-card class="overview">
        <div class="overview-head">
          <h2>考试报告</h2>
          <el-button @click="router.push('/exam')">返回</el-button>
        </div>
        <el-row :gutter="16">
          <el-col :xs="12" :sm="6">
            <div class="metric">
              <div class="metric-label">得分</div>
              <div class="metric-value">
                {{ exam.obtained_score }}
                <span class="metric-suffix">/ {{ exam.total_score }}</span>
              </div>
            </div>
          </el-col>
          <el-col :xs="12" :sm="6">
            <div class="metric">
              <div class="metric-label">正确率</div>
              <div class="metric-value">{{ accuracy }} <span class="metric-suffix">%</span></div>
            </div>
          </el-col>
          <el-col :xs="12" :sm="6">
            <div class="metric">
              <div class="metric-label">答对 / 总题</div>
              <div class="metric-value">
                {{ exam.correct_count }} <span class="metric-suffix">/ {{ exam.total_questions }}</span>
              </div>
            </div>
          </el-col>
          <el-col :xs="12" :sm="6">
            <div class="metric">
              <div class="metric-label">用时</div>
              <div class="metric-value" style="font-size:18px">{{ fmtDur(usedSec) }}</div>
            </div>
          </el-col>
        </el-row>
      </el-card>

      <!-- 筛选 + 列表 -->
      <el-card class="block">
        <template #header>
          <div class="filter-row">
            <span>逐题回顾</span>
            <el-radio-group v-model="filter" size="small">
              <el-radio-button value="all">全部 ({{ exam.questions.length }})</el-radio-button>
              <el-radio-button value="right">答对 ({{ counts.right }})</el-radio-button>
              <el-radio-button value="wrong">答错 ({{ counts.wrong }})</el-radio-button>
              <el-radio-button value="unanswered">未答 ({{ counts.unanswered }})</el-radio-button>
            </el-radio-group>
          </div>
        </template>

        <el-empty v-if="!filtered.length" description="无符合条件的题目" />

        <div
          v-for="(q, i) in filtered"
          :key="q.id"
          class="qreview"
          :class="{
            right: q.is_correct,
            wrong: !q.is_correct && q.user_answer !== null,
            unanswered: q.user_answer === null || q.user_answer === undefined || q.user_answer === ''
          }"
        >
          <div class="qreview-head">
            <el-tag size="small">{{ TYPE_LABEL[q.question_type] }}</el-tag>
            <el-tag :type="DIFF_LABEL[q.difficulty]?.tag" effect="light" size="small">
              {{ DIFF_LABEL[q.difficulty]?.label || q.difficulty }}
            </el-tag>
            <el-tag size="small" type="info">{{ q.score }} 分</el-tag>
            <span class="status">
              <el-tag v-if="q.is_correct" type="success" size="small">答对 +{{ q.score_obtained }}</el-tag>
              <el-tag v-else-if="q.user_answer !== null && q.user_answer !== undefined && q.user_answer !== ''"
                      type="danger" size="small">答错</el-tag>
              <el-tag v-else type="warning" size="small">未作答</el-tag>
            </span>
          </div>
          <div class="qreview-title">
            {{ TYPE_LABEL[q.question_type] }}第 {{ questionTypeNumber(filtered, i) }} 题. {{ q.title }}
          </div>
          <div v-if="q.content" class="qreview-content">{{ q.content }}</div>

          <div v-if="['single_choice', 'multiple_choice'].includes(q.question_type)" class="opts-readonly">
            <div
              v-for="(opt, oi) in q.options"
              :key="oi"
              class="opt-line"
              :class="{
                'opt-correct': isCorrectOption(q, opt),
                'opt-user-wrong': isUserOption(q, opt) && !isCorrectOption(q, opt)
              }"
            >
              <span class="opt-letter">{{ String.fromCharCode(65 + oi) }}.</span>
              {{ opt }}
            </div>
          </div>

          <div class="answer-line">
            <span class="lbl">你的答案：</span>
            <span :class="q.is_correct ? 'ok' : 'bad'">{{ fmtAnswer(q, q.user_answer) }}</span>
          </div>
          <div class="answer-line">
            <span class="lbl">参考答案：</span>
            <span class="ok">{{ fmtAnswer(q, q.correct_answer) }}</span>
          </div>
          <div v-if="q.explanation" class="explanation">
            <strong>解析：</strong>{{ q.explanation }}
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script>
export default { name: 'ExamResult' }
</script>

<style scoped>
.exam-result {
  max-width: 1100px;
  margin: 0 auto;
}
.overview {
  margin-bottom: 16px;
}
.overview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.overview-head h2 {
  margin: 0;
}
.metric {
  text-align: center;
  padding: 8px 0;
}
.metric-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.metric-value {
  font-size: 28px;
  font-weight: 600;
  color: var(--el-color-primary);
}
.metric-suffix {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  font-weight: normal;
  margin-left: 4px;
}
.block {
  margin-bottom: 16px;
}
.filter-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.qreview {
  border-left: 3px solid var(--el-border-color);
  padding: 12px 16px;
  margin-bottom: 12px;
  background: var(--el-bg-color-page);
  border-radius: 4px;
}
.qreview.right { border-left-color: var(--el-color-success); }
.qreview.wrong { border-left-color: var(--el-color-danger); }
.qreview.unanswered { border-left-color: var(--el-color-warning); }
.qreview-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.qreview-head .status {
  margin-left: auto;
}
.qreview-title {
  font-weight: 600;
  margin-bottom: 10px;
  white-space: pre-wrap;
}
.qreview-content {
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
  white-space: pre-wrap;
}
.opts-readonly {
  margin: 18px 0 8px;
}
.opt-line {
  padding: 4px 8px;
  border-radius: 3px;
  margin-bottom: 4px;
}
.opt-line.opt-correct {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
}
.opt-line.opt-user-wrong {
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
  text-decoration: line-through;
}
.opt-letter {
  font-weight: 600;
  margin-right: 4px;
}
.answer-line {
  font-size: 14px;
  margin-top: 4px;
}
.answer-line .lbl {
  color: var(--el-text-color-secondary);
  margin-right: 4px;
}
.answer-line .ok { color: var(--el-color-success); }
.answer-line .bad { color: var(--el-color-danger); }
.explanation {
  margin-top: 6px;
  padding: 6px 10px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  font-size: 13px;
  white-space: pre-wrap;
}
</style>
