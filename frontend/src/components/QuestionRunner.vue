<script setup>
/**
 * 通用答题组件：拿到一组题目后，逐题作答 / 判题 / 显示解析 / 收藏 / 切题。
 *
 * Props:
 *  - questions:   后端返回的题目数组（需含 correct_answer / options / question_type / is_favorite）
 *  - title:       顶部标题（"顺序练习" / "随机练习"...）
 *  - showSubmit:  是否在最后一题后显示 "结束本次练习" 按钮，默认 true
 *
 * Emits:
 *  - finish:      用户在最后一题点击 "结束本次练习" 时触发，携带本次答题汇总
 *  - exit:        用户点击 "退出" 时触发，由父级决定回到哪里
 */
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const props = defineProps({
  questions: { type: Array, required: true },
  title: { type: String, default: '练习' },
  showSubmit: { type: Boolean, default: true }
})
const emit = defineEmits(['finish', 'exit'])

const TYPE_LABEL = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  true_false: '判断题',
  fill_in_blank: '填空题',
  subjective: '主观题'
}
const DIFF_LABEL = {
  easy: { label: '简单', tag: 'success' },
  medium: { label: '中等', tag: 'warning' },
  hard: { label: '困难', tag: 'danger' }
}

const idx = ref(0)
const total = computed(() => props.questions.length)
const current = computed(() => props.questions[idx.value])

// 每题在本次会话的本地状态：用户答案 / 是否已提交 / 是否答对 / 收藏状态
const answers = reactive({})
function ensureSlot(qid) {
  if (!answers[qid]) {
    const q = props.questions.find(x => x.id === qid)
    answers[qid] = {
      input: defaultInput(q),
      submitted: false,
      isCorrect: null,
      favorite: !!q?.is_favorite
    }
  }
  return answers[qid]
}
function defaultInput(q) {
  if (!q) return ''
  if (q.question_type === 'multiple_choice') return []
  if (q.question_type === 'true_false') return null
  return ''
}

// 当题切换或题目数据变化时初始化槽位
watch(
  () => current.value?.id,
  (qid) => { if (qid) ensureSlot(qid) },
  { immediate: true }
)

// 题目数组整体被替换时（错题回顾/收藏夹 reload），把指针拨回第一题
watch(
  () => props.questions,
  () => { idx.value = 0 }
)

const slot = computed(() => current.value ? ensureSlot(current.value.id) : null)

// ===== 统计 =====
const answeredCount = computed(() => Object.values(answers).filter(a => a.submitted).length)
const correctCount = computed(() => Object.values(answers).filter(a => a.isCorrect === true).length)
const accuracy = computed(() => answeredCount.value === 0 ? 0
  : Math.round(correctCount.value / answeredCount.value * 100))

// ===== 判题 =====
function compareAnswer(q, user) {
  if (q.question_type === 'single_choice') {
    return user === q.correct_answer
  }
  if (q.question_type === 'multiple_choice') {
    const a = Array.isArray(user) ? [...user].sort() : []
    const b = Array.isArray(q.correct_answer) ? [...q.correct_answer].sort() : []
    if (a.length !== b.length) return false
    return a.every((v, i) => v === b[i])
  }
  if (q.question_type === 'true_false') {
    const truth = q.correct_answer === true || q.correct_answer === 'true'
    return user === truth
  }
  if (q.question_type === 'fill_in_blank') {
    const norm = v => String(v ?? '').trim().toLowerCase()
    if (Array.isArray(q.correct_answer)) {
      return q.correct_answer.some(ans => norm(ans) === norm(user))
    }
    return norm(q.correct_answer) === norm(user)
  }
  // 主观题不在前端判对错
  return null
}

function isInputEmpty(q, input) {
  if (q.question_type === 'multiple_choice') return !Array.isArray(input) || input.length === 0
  if (q.question_type === 'true_false') return input === null || input === undefined
  return input === '' || input === null || input === undefined
}

const submitting = ref(false)
async function submitAnswer() {
  const q = current.value
  const s = slot.value
  if (!q || !s) return
  if (s.submitted) return
  if (isInputEmpty(q, s.input)) {
    ElMessage.warning('请先作答')
    return
  }

  const correct = compareAnswer(q, s.input)
  s.isCorrect = correct
  s.submitted = true

  // 主观题暂不上报判题结果
  if (q.question_type === 'subjective') {
    ElMessage.info('主观题已记录，请对照参考答案自评')
    return
  }

  submitting.value = true
  try {
    await api.post('/practice/submit-answer', {
      question_id: q.id,
      answer: s.input,
      is_correct: !!correct
    })
  } catch (err) {
    // 不影响本地展示，只提示一下
    console.warn('submit-answer failed', err)
  } finally {
    submitting.value = false
  }
}

async function toggleFavorite() {
  const q = current.value
  const s = slot.value
  if (!q || !s) return
  try {
    if (s.favorite) {
      await api.delete(`/practice/favorites/${q.id}`)
      s.favorite = false
      q.is_favorite = false
      ElMessage.success('已取消收藏')
    } else {
      await api.post('/practice/favorites', { question_id: q.id })
      s.favorite = true
      q.is_favorite = true
      ElMessage.success('已加入收藏')
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '操作失败')
  }
}

function goPrev() {
  if (idx.value > 0) idx.value--
}
function goNext() {
  if (idx.value < total.value - 1) idx.value++
}
function jumpTo(i) {
  if (i >= 0 && i < total.value) idx.value = i
}

function finish() {
  emit('finish', {
    total: total.value,
    answered: answeredCount.value,
    correct: correctCount.value,
    accuracy: accuracy.value
  })
}

function formatRefAnswer(q) {
  if (q.question_type === 'true_false') {
    return (q.correct_answer === true || q.correct_answer === 'true') ? '正确' : '错误'
  }
  if (Array.isArray(q.correct_answer)) return q.correct_answer.join(' / ')
  return String(q.correct_answer ?? '')
}
</script>

<template>
  <div v-if="total > 0" class="runner">
    <div class="runner-head">
      <div class="left">
        <h3>{{ title }}</h3>
        <el-tag size="small">{{ idx + 1 }} / {{ total }}</el-tag>
        <el-tag size="small" type="info">已答 {{ answeredCount }}</el-tag>
        <el-tag size="small" type="success">正确 {{ correctCount }}</el-tag>
        <el-tag size="small" type="warning">正确率 {{ accuracy }}%</el-tag>
      </div>
      <div class="right">
        <el-button text @click="emit('exit')">退出</el-button>
      </div>
    </div>

    <el-card v-if="current" class="qcard">
      <div class="qhead">
        <el-tag size="small">{{ TYPE_LABEL[current.question_type] || current.question_type }}</el-tag>
        <el-tag :type="DIFF_LABEL[current.difficulty]?.tag" size="small" effect="light">
          {{ DIFF_LABEL[current.difficulty]?.label || current.difficulty }}
        </el-tag>
        <span class="score">{{ current.score }} 分</span>
        <el-button
          link
          :type="slot?.favorite ? 'warning' : 'default'"
          @click="toggleFavorite"
        >
          <el-icon><component :is="slot?.favorite ? 'StarFilled' : 'Star'" /></el-icon>
          {{ slot?.favorite ? '已收藏' : '收藏' }}
        </el-button>
      </div>

      <div class="qtitle">{{ idx + 1 }}. {{ current.title }}</div>
      <div v-if="current.content" class="qcontent">{{ current.content }}</div>

      <!-- 单选 -->
      <template v-if="current.question_type === 'single_choice'">
        <el-radio-group v-model="slot.input" :disabled="slot.submitted" class="opts">
          <el-radio
            v-for="(opt, i) in current.options"
            :key="i"
            :value="opt"
            class="opt-row"
          >
            <span class="opt-letter">{{ String.fromCharCode(65 + i) }}.</span> {{ opt }}
          </el-radio>
        </el-radio-group>
      </template>

      <!-- 多选 -->
      <template v-else-if="current.question_type === 'multiple_choice'">
        <el-checkbox-group v-model="slot.input" :disabled="slot.submitted" class="opts">
          <el-checkbox
            v-for="(opt, i) in current.options"
            :key="i"
            :value="opt"
            class="opt-row"
          >
            <span class="opt-letter">{{ String.fromCharCode(65 + i) }}.</span> {{ opt }}
          </el-checkbox>
        </el-checkbox-group>
      </template>

      <!-- 判断 -->
      <template v-else-if="current.question_type === 'true_false'">
        <el-radio-group v-model="slot.input" :disabled="slot.submitted" class="answer-area">
          <el-radio :value="true">正确</el-radio>
          <el-radio :value="false">错误</el-radio>
        </el-radio-group>
      </template>

      <!-- 填空 -->
      <template v-else-if="current.question_type === 'fill_in_blank'">
        <el-input
          v-model="slot.input"
          :disabled="slot.submitted"
          class="answer-area"
          placeholder="请输入答案"
        />
      </template>

      <!-- 主观题 -->
      <template v-else>
        <el-input
          v-model="slot.input"
          type="textarea"
          :rows="4"
          :disabled="slot.submitted"
          class="answer-area"
          placeholder="请作答"
        />
      </template>

      <!-- 判题反馈 / 解析 -->
      <div v-if="slot?.submitted" class="feedback">
        <el-alert
          v-if="current.question_type === 'subjective'"
          type="info"
          :closable="false"
          title="主观题需自评"
        >
          请对照参考答案自评：{{ formatRefAnswer(current) }}
        </el-alert>
        <el-alert
          v-else-if="slot.isCorrect"
          type="success"
          :closable="false"
          title="回答正确"
        />
        <el-alert
          v-else
          type="error"
          :closable="false"
          :title="`回答错误，参考答案：${formatRefAnswer(current)}`"
        />
        <div v-if="current.explanation" class="explanation">
          <strong>解析：</strong>{{ current.explanation }}
        </div>
      </div>

      <div class="actions">
        <el-button :disabled="idx === 0" @click="goPrev">上一题</el-button>
        <el-button
          v-if="!slot?.submitted"
          type="primary"
          :loading="submitting"
          @click="submitAnswer"
        >
          提交答案
        </el-button>
        <el-button
          v-else-if="idx < total - 1"
          type="primary"
          @click="goNext"
        >
          下一题
        </el-button>
        <el-button
          v-else-if="showSubmit"
          type="success"
          @click="finish"
        >
          结束本次练习
        </el-button>
      </div>
    </el-card>

    <!-- 题号导航 -->
    <el-card class="navbar">
      <div class="nav-title">题号导航</div>
      <div class="nav-grid">
        <span
          v-for="(q, i) in questions"
          :key="q.id"
          class="nav-cell"
          :class="{
            active: i === idx,
            correct: answers[q.id]?.isCorrect === true,
            wrong: answers[q.id]?.isCorrect === false,
            answered: answers[q.id]?.submitted
          }"
          @click="jumpTo(i)"
        >{{ i + 1 }}</span>
      </div>
    </el-card>
  </div>

  <el-empty v-else description="暂无题目" />
</template>

<style scoped>
.runner-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.runner-head .left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.runner-head h3 {
  margin: 0 8px 0 0;
}
.qcard {
  margin-bottom: 12px;
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
  margin-bottom: 6px;
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
.answer-area {
  margin-top: 18px;
}
/* element-plus 的 radio/checkbox 默认 inline-flex 且竖排在 group 里仍可能被居中容器影响；
   这里强制每行整行、左对齐、内容可换行 */
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
.opt-row {
  display: flex;
  align-items: flex-start;
  white-space: normal;
  line-height: 1.5;
  width: 100%;
}
.opt-letter {
  margin-right: 4px;
  font-weight: 600;
}
.feedback {
  margin-top: 16px;
}
.explanation {
  margin-top: 8px;
  padding: 8px 12px;
  background: var(--el-bg-color-page);
  border-radius: 4px;
  font-size: 14px;
  white-space: pre-wrap;
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
  background: var(--el-color-info-light-9);
}
.nav-cell.correct {
  background: var(--el-color-success-light-8);
  border-color: var(--el-color-success);
  color: var(--el-color-success);
}
.nav-cell.wrong {
  background: var(--el-color-danger-light-8);
  border-color: var(--el-color-danger);
  color: var(--el-color-danger);
}
.nav-cell.active {
  outline: 2px solid var(--el-color-primary);
}
</style>
