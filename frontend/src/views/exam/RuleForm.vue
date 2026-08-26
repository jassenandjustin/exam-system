<script setup>
/**
 * 选题规则表单组件：
 *  - 选择学科、章节（可选）、难度（可选）、抽取题数
 *  - 可选按题型分配题数
 *  - 实时显示可用题目数
 */
import { ref, watch, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const props = defineProps({
  subjectId: { type: Number, default: null },
  chapterId: { type: Number, default: null },
  difficulty: { type: String, default: '' },
  questionCount: { type: Number, default: 5 },
  orderNum: { type: Number, default: 0 },
})

const emit = defineEmits(['submit', 'cancel'])

const subjects = ref([])
const chapters = ref([])
const availableCount = ref(null)
const availableByType = ref({})
const chapterStats = ref(null)

const form = reactive({
  subject_id: props.subjectId,
  chapter_id: props.chapterId,
  difficulty: props.difficulty,
  question_count: props.questionCount,
  order_num: props.orderNum,
  use_type_distribution: false,
  type_distribution: {
    single_choice: 0,
    multiple_choice: 0,
    fill_in_blank: 0,
    true_false: 0,
    subjective: 0,
  },
})

const DIFF_OPTIONS = [
  { value: '', label: '不限' },
  { value: 'easy', label: '简单' },
  { value: 'medium', label: '中等' },
  { value: 'hard', label: '困难' },
]

const QUESTION_TYPE_OPTIONS = [
  { value: 'single_choice', label: '单选题' },
  { value: 'multiple_choice', label: '多选题' },
  { value: 'fill_in_blank', label: '填空题' },
  { value: 'true_false', label: '判断题' },
  { value: 'subjective', label: '主观题' },
]

const distributionTotal = computed(() => {
  return QUESTION_TYPE_OPTIONS.reduce((sum, item) => {
    return sum + Number(form.type_distribution[item.value] || 0)
  }, 0)
})

const distributionMatched = computed(() => distributionTotal.value === Number(form.question_count || 0))

async function loadSubjects() {
  try {
    const { data } = await api.get('/taxonomy/subjects')
    subjects.value = data
  } catch { /* silent */ }
}

async function loadChapters(subjectId) {
  if (!subjectId) {
    chapters.value = []
    return
  }
  try {
    const { data } = await api.get('/taxonomy/chapters', { params: { subject_id: subjectId } })
    chapters.value = data
  } catch { /* silent */ }
}

function emptyTypeCounts() {
  return QUESTION_TYPE_OPTIONS.reduce((acc, item) => {
    acc[item.value] = 0
    return acc
  }, {})
}

function updateAvailableFromStats() {
  const data = chapterStats.value
  if (!data) {
    availableCount.value = null
    availableByType.value = emptyTypeCounts()
    return
  }

  let total = data.subject_total || 0
  let byType = data.subject_by_type || emptyTypeCounts()
  let byDifficultyType = data.subject_by_difficulty_type || {}

  if (form.chapter_id) {
    const ch = data.chapters.find(c => c.id === form.chapter_id)
    if (ch) {
      total = ch.total
      byType = ch.by_type || emptyTypeCounts()
      byDifficultyType = ch.by_difficulty_type || {}
      if (form.difficulty) {
        total = ch[form.difficulty] || 0
      }
    }
  } else if (form.difficulty) {
    total = 0
    for (const ch of data.chapters) {
      total += ch[form.difficulty] || 0
    }
  }

  if (form.difficulty) {
    byType = byDifficultyType[form.difficulty] || emptyTypeCounts()
  }

  availableCount.value = total
  availableByType.value = { ...emptyTypeCounts(), ...byType }
}

async function loadChapterStats(subjectId) {
  if (!subjectId) {
    chapterStats.value = null
    updateAvailableFromStats()
    return
  }
  try {
    const { data } = await api.get(`/exam/subjects/${subjectId}/chapter-stats`)
    chapterStats.value = data
    updateAvailableFromStats()
  } catch { /* silent */ }
}

function onSubjectChange(val) {
  form.chapter_id = null
  chapters.value = []
  chapterStats.value = null
  if (val) {
    loadChapters(val)
    loadChapterStats(val)
  } else {
    updateAvailableFromStats()
  }
}

function onChapterChange() {
  updateAvailableFromStats()
}

function onDifficultyChange() {
  updateAvailableFromStats()
}

function buildTypeDistribution() {
  const result = {}
  for (const item of QUESTION_TYPE_OPTIONS) {
    const count = Number(form.type_distribution[item.value] || 0)
    if (count > 0) {
      result[item.value] = count
    }
  }
  return result
}

async function handleSubmit() {
  if (!form.subject_id) {
    ElMessage.warning('请选择学科')
    return
  }
  if (!form.question_count || form.question_count <= 0) {
    ElMessage.warning('请输入有效的抽取题数')
    return
  }
  if (form.use_type_distribution) {
    if (distributionTotal.value <= 0) {
      ElMessage.warning('请至少设置一种题型的抽取数量')
      return
    }
    if (!distributionMatched.value) {
      ElMessage.warning('各题型数量之和必须等于抽取题数')
      return
    }
    for (const item of QUESTION_TYPE_OPTIONS) {
      const count = Number(form.type_distribution[item.value] || 0)
      const available = Number(availableByType.value[item.value] || 0)
      if (count > available) {
        ElMessage.warning(`${item.label}可用题目不足，当前仅有 ${available} 题`)
        return
      }
    }
  }

  const payload = {
    subject_id: form.subject_id,
    chapter_id: form.chapter_id,
    difficulty: form.difficulty,
    question_count: form.question_count,
    order_num: form.order_num,
  }
  if (form.use_type_distribution) {
    payload.type_distribution = buildTypeDistribution()
  }
  emit('submit', payload)
}

function handleCancel() {
  emit('cancel')
}

watch(() => form.question_count, (value) => {
  if (value < 1) form.question_count = 1
})

onMounted(() => {
  availableByType.value = emptyTypeCounts()
  loadSubjects()
  if (form.subject_id) {
    loadChapters(form.subject_id)
    loadChapterStats(form.subject_id)
  }
})
</script>

<template>
  <div class="rule-form">
    <el-form :model="form" label-width="80px" class="rule-inline-form">
      <el-form-item label="学科" required>
        <el-select v-model="form.subject_id" placeholder="选择学科" style="width:140px" @change="onSubjectChange">
          <el-option v-for="s in subjects" :key="s.id" :value="s.id" :label="s.name" />
        </el-select>
      </el-form-item>

      <el-form-item label="章节">
        <el-select v-model="form.chapter_id" placeholder="全部章节" clearable style="width:160px" @change="onChapterChange">
          <el-option v-for="c in chapters" :key="c.id" :value="c.id" :label="c.name" />
        </el-select>
      </el-form-item>

      <el-form-item label="难度">
        <el-select v-model="form.difficulty" style="width:100px" @change="onDifficultyChange">
          <el-option v-for="d in DIFF_OPTIONS" :key="d.value" :value="d.value" :label="d.label" />
        </el-select>
      </el-form-item>

      <el-form-item label="抽取题数" required>
        <el-input-number v-model="form.question_count" :min="1" :max="200" style="width:120px" />
      </el-form-item>

      <el-form-item>
        <span v-if="availableCount !== null" class="available-hint">
          可用: <strong>{{ availableCount }}</strong> 题
        </span>
      </el-form-item>

      <el-form-item label="题型分配">
        <el-switch
          v-model="form.use_type_distribution"
          active-text="开启"
          inactive-text="不开启"
        />
      </el-form-item>

      <div v-if="form.use_type_distribution" class="type-distribution-panel">
        <div class="type-distribution-header">
          <span>按题型设置抽取数量</span>
          <span :class="['distribution-summary', { 'warn-text': !distributionMatched }]">
            已分配 {{ distributionTotal }} / {{ form.question_count }} 题
          </span>
        </div>
        <div class="type-grid">
          <div v-for="item in QUESTION_TYPE_OPTIONS" :key="item.value" class="type-item">
            <span class="type-label">{{ item.label }}</span>
            <el-input-number
              v-model="form.type_distribution[item.value]"
              :min="0"
              :max="200"
              size="small"
              controls-position="right"
              style="width:110px"
            />
            <span
              :class="[
                'type-available',
                { 'warn-text': Number(form.type_distribution[item.value] || 0) > Number(availableByType[item.value] || 0) }
              ]"
            >
              可用 {{ availableByType[item.value] || 0 }}
            </span>
          </div>
        </div>
        <div v-if="!distributionMatched" class="distribution-error">
          各题型数量之和必须等于抽取题数
        </div>
      </div>

      <el-form-item class="action-row">
        <el-button type="primary" size="small" @click="handleSubmit">添加规则</el-button>
        <el-button size="small" @click="handleCancel">取消</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<style scoped>
.rule-form {
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  margin-bottom: 12px;
}
.rule-inline-form {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 0;
}
.available-hint {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}
.available-hint strong {
  color: var(--el-color-primary);
}
.type-distribution-panel {
  width: 100%;
  padding: 10px 12px;
  margin-bottom: 8px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
}
.type-distribution-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--el-text-color-regular);
}
.distribution-summary {
  color: var(--el-color-primary);
  font-weight: 600;
}
.type-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 8px 12px;
}
.type-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.type-label {
  width: 58px;
  font-size: 13px;
  color: var(--el-text-color-regular);
}
.type-available {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}
.distribution-error,
.warn-text {
  color: var(--el-color-danger);
  font-weight: 600;
}
.distribution-error {
  margin-top: 8px;
  font-size: 12px;
}
.action-row {
  margin-left: auto;
}
</style>
