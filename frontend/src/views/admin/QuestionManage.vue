<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

// ===== 元数据：学科/章节/标签 =====
const subjects = ref([])
const chapters = ref([])
const tags = ref([])

// ===== 题目列表 =====
const questions = ref([])
const total = ref(0)
const tableLoading = ref(false)

const query = reactive({
  page: 1,
  per_page: 10,
  subject_id: null,
  chapter_id: null,
  question_type: '',
  difficulty: '',
  search: ''
})

const QUESTION_TYPES = [
  { value: 'single_choice', label: '单选题' },
  { value: 'multiple_choice', label: '多选题' },
  { value: 'true_false', label: '判断题' },
  { value: 'fill_in_blank', label: '填空题' },
  { value: 'subjective', label: '主观题' }
]
const DIFFICULTIES = [
  { value: 'easy', label: '简单', tag: 'success' },
  { value: 'medium', label: '中等', tag: 'warning' },
  { value: 'hard', label: '困难', tag: 'danger' }
]

const typeMap = Object.fromEntries(QUESTION_TYPES.map(t => [t.value, t.label]))
const diffMap = Object.fromEntries(DIFFICULTIES.map(d => [d.value, d]))

const filteredChapters = computed(() =>
  query.subject_id ? chapters.value.filter(c => c.subject_id === query.subject_id) : chapters.value
)

async function loadMeta() {
  try {
    const [s, c, t] = await Promise.all([
      api.get('/taxonomy/subjects'),
      api.get('/taxonomy/chapters'),
      api.get('/taxonomy/tags')
    ])
    subjects.value = s.data
    chapters.value = c.data
    tags.value = t.data
  } catch (err) {
    ElMessage.error('加载元数据失败')
  }
}

async function loadQuestions() {
  tableLoading.value = true
  try {
    const params = { page: query.page, per_page: query.per_page }
    if (query.subject_id) params.subject_id = query.subject_id
    if (query.chapter_id) params.chapter_id = query.chapter_id
    if (query.question_type) params.question_type = query.question_type
    if (query.difficulty) params.difficulty = query.difficulty
    if (query.search) params.search = query.search
    const { data } = await api.get('/questions', { params })
    questions.value = data.questions
    total.value = data.total
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '加载题目失败')
  } finally {
    tableLoading.value = false
  }
}

function onSearch() {
  query.page = 1
  loadQuestions()
}
function onSubjectChange() {
  query.chapter_id = null
  onSearch()
}
function onPageChange(p) {
  query.page = p
  loadQuestions()
}
function resetFilter() {
  Object.assign(query, {
    page: 1, subject_id: null, chapter_id: null, question_type: '', difficulty: '', search: ''
  })
  loadQuestions()
}

// ===== 编辑对话框 =====
const dlgVisible = ref(false)
const dlgMode = ref('create') // 'create' | 'edit'
const dlgLoading = ref(false)
const formRef = ref(null)

const blankForm = () => ({
  id: null,
  subject_id: null,
  chapter_id: null,
  question_type: 'single_choice',
  title: '',
  content: '',
  options: ['', ''],
  correct_answer: '',
  correct_answers: [],   // for multiple_choice
  correct_bool: true,    // for true_false
  explanation: '',
  difficulty: 'medium',
  score: 2,
  tag_ids: []
})
const form = reactive(blankForm())

const formRules = {
  subject_id: [{ required: true, message: '请选择学科', trigger: 'change' }],
  question_type: [{ required: true, message: '请选择题型', trigger: 'change' }],
  title: [{ required: true, message: '请输入题干', trigger: 'blur' }],
  difficulty: [{ required: true, message: '请选择难度', trigger: 'change' }]
}

const formChapters = computed(() =>
  form.subject_id ? chapters.value.filter(c => c.subject_id === form.subject_id) : []
)

function resetForm() {
  Object.assign(form, blankForm())
  formRef.value?.clearValidate()
}

function openCreate() {
  if (subjects.value.length === 0) {
    ElMessage.warning('请先创建学科')
    return
  }
  dlgMode.value = 'create'
  resetForm()
  dlgVisible.value = true
}

async function openEdit(row) {
  dlgMode.value = 'edit'
  dlgVisible.value = true
  dlgLoading.value = true
  try {
    const { data } = await api.get(`/questions/${row.id}`)
    Object.assign(form, blankForm())
    form.id = data.id
    form.subject_id = data.subject_id
    form.chapter_id = data.chapter_id
    form.question_type = data.question_type
    form.title = data.title
    form.content = data.content || ''
    form.explanation = data.explanation || ''
    form.difficulty = data.difficulty
    form.score = data.score
    form.tag_ids = (data.tags || []).map(t => t.id)

    // 选项 / 答案处理
    if (data.question_type === 'single_choice' || data.question_type === 'multiple_choice') {
      form.options = Array.isArray(data.options) ? [...data.options] : ['', '']
    }
    if (data.question_type === 'multiple_choice') {
      form.correct_answers = Array.isArray(data.correct_answer) ? data.correct_answer : []
    } else if (data.question_type === 'true_false') {
      form.correct_bool = data.correct_answer === true || data.correct_answer === 'true'
    } else {
      form.correct_answer = typeof data.correct_answer === 'string'
        ? data.correct_answer
        : JSON.stringify(data.correct_answer ?? '')
    }
  } catch (err) {
    ElMessage.error('加载题目详情失败')
    dlgVisible.value = false
  } finally {
    dlgLoading.value = false
  }
}

function addOption() {
  form.options.push('')
}
function removeOption(idx) {
  if (form.options.length <= 2) {
    ElMessage.warning('至少保留 2 个选项')
    return
  }
  const removed = form.options[idx]
  form.options.splice(idx, 1)
  // 同步清理已选中的正确答案
  if (form.question_type === 'multiple_choice') {
    form.correct_answers = form.correct_answers.filter(x => x !== removed)
  } else if (form.correct_answer === removed) {
    form.correct_answer = ''
  }
}

function buildPayload() {
  const payload = {
    subject_id: form.subject_id,
    chapter_id: form.chapter_id || null,
    question_type: form.question_type,
    title: form.title,
    content: form.content || null,
    explanation: form.explanation || null,
    difficulty: form.difficulty,
    score: Number(form.score) || 0,
    tag_ids: form.tag_ids
  }
  if (form.question_type === 'single_choice') {
    payload.options = form.options.filter(o => o !== '')
    payload.correct_answer = form.correct_answer
  } else if (form.question_type === 'multiple_choice') {
    payload.options = form.options.filter(o => o !== '')
    payload.correct_answer = form.correct_answers
  } else if (form.question_type === 'true_false') {
    payload.options = null
    payload.correct_answer = form.correct_bool
  } else {
    payload.options = null
    payload.correct_answer = form.correct_answer
  }
  return payload
}

async function onSubmit() {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return

    // 选择题校验答案非空
    if (form.question_type === 'single_choice' && !form.correct_answer) {
      ElMessage.error('请指定正确答案')
      return
    }
    if (form.question_type === 'multiple_choice' && form.correct_answers.length === 0) {
      ElMessage.error('请至少勾选一个正确答案')
      return
    }
    if ((form.question_type === 'fill_in_blank' || form.question_type === 'subjective') && !form.correct_answer) {
      ElMessage.error('请填写参考答案')
      return
    }

    const payload = buildPayload()
    dlgLoading.value = true
    try {
      if (dlgMode.value === 'create') {
        await api.post('/questions', payload)
        ElMessage.success('已创建')
      } else {
        await api.put(`/questions/${form.id}`, payload)
        ElMessage.success('已更新')
      }
      dlgVisible.value = false
      loadQuestions()
    } catch (err) {
      ElMessage.error(err.response?.data?.error || '保存失败')
    } finally {
      dlgLoading.value = false
    }
  })
}

async function deleteQuestion(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除题目「${row.title}」？`,
      '删除题目',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch { return }
  try {
    await api.delete(`/questions/${row.id}`)
    ElMessage.success('已删除')
    loadQuestions()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '删除失败')
  }
}

function subjectName(id) {
  return subjects.value.find(s => s.id === id)?.name || '—'
}
function chapterName(id) {
  return chapters.value.find(c => c.id === id)?.name || '—'
}
function formatAnswer(row) {
  if (row.question_type === 'multiple_choice') {
    return Array.isArray(row.correct_answer) ? row.correct_answer.join(' / ') : ''
  }
  if (row.question_type === 'true_false') {
    return row.correct_answer === true || row.correct_answer === 'true' ? '正确' : '错误'
  }
  return typeof row.correct_answer === 'string' ? row.correct_answer : JSON.stringify(row.correct_answer)
}

// ===== 批量导入 =====
const importVisible = ref(false)
const importMode = ref('json')          // 'json' | 'csv'
const importJsonText = ref('')
const importCsvText = ref('')
const importLoading = ref(false)
const importResult = ref(null)          // { imported_count, failed_count, errors }

const VALID_TYPES = new Set(['single_choice', 'multiple_choice', 'true_false', 'fill_in_blank', 'subjective'])
const VALID_DIFFS = new Set(['easy', 'medium', 'hard'])

function openImport() {
  importMode.value = 'json'
  importJsonText.value = ''
  importCsvText.value = ''
  importResult.value = null
  importVisible.value = true
}

// 简单 CSV 解析：支持双引号包裹、引号转义（""）、字段内换行
function parseCSV(text) {
  const rows = []
  let cur = ['']
  let i = 0
  let inQuotes = false
  while (i < text.length) {
    const ch = text[i]
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') { cur[cur.length - 1] += '"'; i += 2; continue }
        inQuotes = false; i++; continue
      }
      cur[cur.length - 1] += ch; i++; continue
    }
    if (ch === '"') { inQuotes = true; i++; continue }
    if (ch === ',') { cur.push(''); i++; continue }
    if (ch === '\r') { i++; continue }
    if (ch === '\n') {
      rows.push(cur)
      cur = ['']; i++; continue
    }
    cur[cur.length - 1] += ch; i++
  }
  // 最后一行
  if (cur.length > 1 || cur[0] !== '') rows.push(cur)
  return rows
}

// 把"按名字"的导入对象规范化为后端需要的 payload，缺数据则抛错
function normalizeImportItem(item, idx) {
  const errors = []

  // 学科：subject_id 优先；否则 subject 名字
  let subject_id = item.subject_id
  if (!subject_id && item.subject) {
    const s = subjects.value.find(x => x.name === String(item.subject).trim())
    if (!s) errors.push(`学科「${item.subject}」未找到`)
    else subject_id = s.id
  }
  if (!subject_id) errors.push('缺少学科 (subject 或 subject_id)')

  // 章节：可选
  let chapter_id = item.chapter_id || null
  if (!chapter_id && item.chapter) {
    const c = chapters.value.find(x =>
      x.name === String(item.chapter).trim() &&
      (!subject_id || x.subject_id === subject_id)
    )
    if (!c) errors.push(`章节「${item.chapter}」未找到`)
    else chapter_id = c.id
  }

  // 题型
  const question_type = String(item.question_type || '').trim()
  if (!VALID_TYPES.has(question_type)) {
    errors.push(`题型「${item.question_type}」无效`)
  }

  // 题干
  const title = String(item.title || '').trim()
  if (!title) errors.push('缺少题干 (title)')

  // 难度
  const difficulty = String(item.difficulty || 'medium').trim()
  if (!VALID_DIFFS.has(difficulty)) errors.push(`难度「${item.difficulty}」无效`)

  // 选项
  let options = item.options
  if (typeof options === 'string') {
    options = options.split('|').map(s => s.trim()).filter(s => s !== '')
  }
  if ((question_type === 'single_choice' || question_type === 'multiple_choice')) {
    if (!Array.isArray(options) || options.length < 2) {
      errors.push('选择题选项不足 2 个')
    }
  } else {
    options = null
  }

  // 答案
  let correct_answer = item.correct_answer
  if (question_type === 'multiple_choice') {
    if (typeof correct_answer === 'string') {
      correct_answer = correct_answer.split('|').map(s => s.trim()).filter(s => s !== '')
    }
    if (!Array.isArray(correct_answer) || correct_answer.length === 0) {
      errors.push('多选题需要数组形式答案')
    }
  } else if (question_type === 'true_false') {
    if (typeof correct_answer === 'string') {
      const v = correct_answer.trim().toLowerCase()
      if (v === 'true' || v === '正确' || v === '1' || v === 't') correct_answer = true
      else if (v === 'false' || v === '错误' || v === '0' || v === 'f') correct_answer = false
      else errors.push('判断题答案应为 true/false')
    } else if (typeof correct_answer !== 'boolean') {
      errors.push('判断题答案应为 true/false')
    }
  } else {
    if (correct_answer === undefined || correct_answer === null || String(correct_answer).trim() === '') {
      errors.push('缺少答案 (correct_answer)')
    } else {
      correct_answer = String(correct_answer)
    }
  }

  // 标签
  let tag_ids = item.tag_ids
  if (!tag_ids && item.tags) {
    let names = item.tags
    if (typeof names === 'string') {
      names = names.split('|').map(s => s.trim()).filter(s => s !== '')
    }
    tag_ids = []
    for (const name of names) {
      const t = tags.value.find(x => x.name === name)
      if (t) tag_ids.push(t.id)
      else errors.push(`标签「${name}」未找到`)
    }
  }

  if (errors.length) {
    const err = new Error(errors.join('；'))
    err._row = idx
    throw err
  }

  return {
    subject_id,
    chapter_id,
    question_type,
    title,
    content: item.content ? String(item.content) : null,
    options,
    correct_answer,
    explanation: item.explanation ? String(item.explanation) : null,
    difficulty,
    score: Number(item.score) || 2,
    tag_ids: tag_ids || []
  }
}

const CSV_HEADERS = [
  'subject', 'chapter', 'question_type', 'title', 'content',
  'options', 'correct_answer', 'explanation', 'difficulty', 'score', 'tags'
]

function buildItemsFromJson(text) {
  let raw
  try {
    raw = JSON.parse(text)
  } catch (e) {
    throw new Error('JSON 格式错误：' + e.message)
  }
  if (!Array.isArray(raw)) throw new Error('JSON 顶层应为数组')
  return raw
}

function buildItemsFromCsv(text) {
  // 去掉 UTF-8 BOM，避免首列名变成 ﻿subject
  const cleaned = text.replace(/^﻿/, '')
  const rows = parseCSV(cleaned).filter(r => r.length > 0 && !(r.length === 1 && r[0] === ''))
  if (rows.length < 2) throw new Error('CSV 至少需要表头 + 1 行数据')
  const headers = rows[0].map(h => h.trim())
  // 校验关键列
  for (const must of ['subject', 'question_type', 'title', 'correct_answer']) {
    if (!headers.includes(must)) throw new Error(`CSV 缺少必需列：${must}`)
  }
  return rows.slice(1).map(cells => {
    const obj = {}
    headers.forEach((h, i) => {
      const v = cells[i] !== undefined ? String(cells[i]).trim() : ''
      obj[h] = v
    })
    return obj
  })
}

async function doImport() {
  importLoading.value = true
  importResult.value = null
  try {
    const rawItems = importMode.value === 'json'
      ? buildItemsFromJson(importJsonText.value)
      : buildItemsFromCsv(importCsvText.value)

    if (!rawItems.length) {
      ElMessage.warning('没有可导入的数据')
      return
    }

    // 前端先做归一化与校验
    const payload = []
    const localErrors = []
    rawItems.forEach((item, i) => {
      try {
        payload.push(normalizeImportItem(item, i))
      } catch (e) {
        localErrors.push({ index: i, error: e.message })
      }
    })

    if (payload.length === 0) {
      importResult.value = { imported_count: 0, failed_count: localErrors.length, errors: localErrors }
      ElMessage.error('全部数据校验失败，未提交')
      return
    }

    const { data } = await api.post('/questions/batch-import', { questions: payload })
    importResult.value = {
      imported_count: data.imported_count,
      failed_count: data.failed_count + localErrors.length,
      errors: [...localErrors, ...(data.errors || [])]
    }
    if (data.imported_count > 0) {
      ElMessage.success(`成功导入 ${data.imported_count} 题`)
      // 重新加载题目列表 + 学科章节计数
      await loadMeta()
      await loadQuestions()
    } else {
      ElMessage.warning('未导入任何题目')
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.error || err.message || '导入失败')
  } finally {
    importLoading.value = false
  }
}

// 读取上传文件文本：优先 UTF-8，失败回退 GB18030（兼容 Excel 默认存的 CSV）
function readFileAsText(rawFile) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.onload = e => {
      const buf = e.target.result
      // 严格 UTF-8 解码：遇到非法序列直接抛错
      try {
        const text = new TextDecoder('utf-8', { fatal: true }).decode(buf)
        resolve(text)
      } catch {
        try {
          const text = new TextDecoder('gb18030').decode(buf)
          resolve(text)
        } catch (err) {
          reject(err)
        }
      }
    }
    reader.readAsArrayBuffer(rawFile)
  })
}

async function onCsvFileChange(rawFile) {
  // el-upload before-upload 直接传 File 对象本身
  if (!rawFile) return false
  try {
    importCsvText.value = await readFileAsText(rawFile)
  } catch {
    ElMessage.error('文件读取失败')
  }
  return false   // 阻止自动上传
}

async function onJsonFileChange(rawFile) {
  if (!rawFile) return false
  try {
    importJsonText.value = await readFileAsText(rawFile)
  } catch {
    ElMessage.error('文件读取失败')
  }
  return false
}

function downloadTemplate(kind) {
  const sample = [
    {
      subject: '数学', chapter: '第一章',
      question_type: 'single_choice',
      title: '1 + 1 等于？', content: '',
      options: ['1', '2', '3', '4'],
      correct_answer: '2',
      explanation: '简单加法',
      difficulty: 'easy', score: 2,
      tags: ['基础']
    },
    {
      subject: '数学', chapter: '第一章',
      question_type: 'multiple_choice',
      title: '哪些是质数？', content: '',
      options: ['2', '3', '4', '6'],
      correct_answer: ['2', '3'],
      explanation: '',
      difficulty: 'medium', score: 3,
      tags: []
    },
    {
      subject: '数学', chapter: '',
      question_type: 'true_false',
      title: '0 是自然数', content: '',
      options: '', correct_answer: true,
      explanation: '', difficulty: 'easy', score: 1, tags: []
    }
  ]

  let blob, filename
  if (kind === 'json') {
    blob = new Blob([JSON.stringify(sample, null, 2)], { type: 'application/json' })
    filename = 'questions_template.json'
  } else {
    const lines = [CSV_HEADERS.join(',')]
    for (const s of sample) {
      const row = CSV_HEADERS.map(h => {
        let v = s[h]
        if (Array.isArray(v)) v = v.join('|')
        if (v === undefined || v === null) v = ''
        v = String(v)
        if (v.includes(',') || v.includes('"') || v.includes('\n')) {
          v = '"' + v.replace(/"/g, '""') + '"'
        }
        return v
      })
      lines.push(row.join(','))
    }
    // BOM 让 Excel 正常识别中文
    blob = new Blob(['﻿' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
    filename = 'questions_template.csv'
  }
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  await loadMeta()
  await loadQuestions()
})
</script>

<template>
  <div>
    <el-card>
      <template #header>
        <div class="header">
          <span>题库管理</span>
          <div class="filters">
            <el-select
              v-model="query.subject_id"
              placeholder="学科"
              clearable
              style="width: 140px"
              @change="onSubjectChange"
            >
              <el-option v-for="s in subjects" :key="s.id" :value="s.id" :label="s.name" />
            </el-select>
            <el-select
              v-model="query.chapter_id"
              placeholder="章节"
              clearable
              style="width: 140px"
              :disabled="!query.subject_id"
              @change="onSearch"
            >
              <el-option v-for="c in filteredChapters" :key="c.id" :value="c.id" :label="c.name" />
            </el-select>
            <el-select
              v-model="query.question_type"
              placeholder="题型"
              clearable
              style="width: 130px"
              @change="onSearch"
            >
              <el-option v-for="t in QUESTION_TYPES" :key="t.value" :value="t.value" :label="t.label" />
            </el-select>
            <el-select
              v-model="query.difficulty"
              placeholder="难度"
              clearable
              style="width: 110px"
              @change="onSearch"
            >
              <el-option v-for="d in DIFFICULTIES" :key="d.value" :value="d.value" :label="d.label" />
            </el-select>
            <el-input
              v-model="query.search"
              placeholder="搜索题干"
              clearable
              style="width: 180px"
              @keyup.enter="onSearch"
              @clear="onSearch"
            />
            <el-button @click="resetFilter">重置</el-button>
            <el-button type="primary" @click="onSearch">查询</el-button>
            <el-button :icon="'Upload'" @click="openImport">批量导入</el-button>
            <el-button type="success" :icon="'Plus'" @click="openCreate">新增题目</el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="tableLoading" :data="questions" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="学科" width="120">
          <template #default="{ row }">{{ subjectName(row.subject_id) }}</template>
        </el-table-column>
        <el-table-column label="章节" width="140">
          <template #default="{ row }">{{ chapterName(row.chapter_id) }}</template>
        </el-table-column>
        <el-table-column label="题型" width="100">
          <template #default="{ row }">
            <el-tag>{{ typeMap[row.question_type] || row.question_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="难度" width="80">
          <template #default="{ row }">
            <el-tag :type="diffMap[row.difficulty]?.tag" effect="light">
              {{ diffMap[row.difficulty]?.label || row.difficulty }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="题干" min-width="280" show-overflow-tooltip />
        <el-table-column label="标签" width="180">
          <template #default="{ row }">
            <el-tag
              v-for="t in row.tags"
              :key="t.id"
              size="small"
              effect="plain"
              style="margin-right:4px"
            >{{ t.name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="score" label="分值" width="70" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteQuestion(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pager"
        background
        layout="total, prev, pager, next"
        :total="total"
        :page-size="query.per_page"
        :current-page="query.page"
        @current-change="onPageChange"
      />
    </el-card>

    <el-dialog
      v-model="dlgVisible"
      :title="dlgMode === 'create' ? '新增题目' : '编辑题目'"
      width="720px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="84px"
        v-loading="dlgLoading"
      >
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="学科" prop="subject_id">
              <el-select v-model="form.subject_id" placeholder="选择学科" style="width:100%" @change="form.chapter_id = null">
                <el-option v-for="s in subjects" :key="s.id" :value="s.id" :label="s.name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="章节">
              <el-select v-model="form.chapter_id" placeholder="选填" clearable style="width:100%" :disabled="!form.subject_id">
                <el-option v-for="c in formChapters" :key="c.id" :value="c.id" :label="c.name" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="题型" prop="question_type">
              <el-select v-model="form.question_type" style="width:100%">
                <el-option v-for="t in QUESTION_TYPES" :key="t.value" :value="t.value" :label="t.label" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="难度" prop="difficulty">
              <el-select v-model="form.difficulty" style="width:100%">
                <el-option v-for="d in DIFFICULTIES" :key="d.value" :value="d.value" :label="d.label" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="分值">
              <el-input-number v-model="form.score" :min="0" :step="0.5" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="题干" prop="title">
          <el-input v-model="form.title" type="textarea" :rows="2" placeholder="一句话题干" />
        </el-form-item>

        <el-form-item label="题目详情">
          <el-input v-model="form.content" type="textarea" :rows="2" placeholder="选填，补充说明 / 题干详情" />
        </el-form-item>

        <!-- 单选 / 多选选项 -->
        <template v-if="form.question_type === 'single_choice' || form.question_type === 'multiple_choice'">
          <el-form-item label="选项">
            <div class="options-edit">
              <div v-for="(opt, idx) in form.options" :key="idx" class="option-row">
                <template v-if="form.question_type === 'single_choice'">
                  <el-radio v-model="form.correct_answer" :value="opt" :disabled="!opt">
                    {{ String.fromCharCode(65 + idx) }}
                  </el-radio>
                </template>
                <template v-else>
                  <el-checkbox
                    :model-value="form.correct_answers.includes(opt)"
                    :disabled="!opt"
                    @change="(checked) => {
                      if (checked) form.correct_answers.push(opt)
                      else form.correct_answers = form.correct_answers.filter(x => x !== opt)
                    }"
                  >
                    {{ String.fromCharCode(65 + idx) }}
                  </el-checkbox>
                </template>
                <el-input v-model="form.options[idx]" placeholder="选项内容" style="flex:1" />
                <el-button :icon="'Delete'" link type="danger" @click="removeOption(idx)" />
              </div>
              <el-button :icon="'Plus'" link @click="addOption">添加选项</el-button>
            </div>
          </el-form-item>
        </template>

        <!-- 判断题 -->
        <template v-else-if="form.question_type === 'true_false'">
          <el-form-item label="正确答案">
            <el-radio-group v-model="form.correct_bool">
              <el-radio :value="true">正确</el-radio>
              <el-radio :value="false">错误</el-radio>
            </el-radio-group>
          </el-form-item>
        </template>

        <!-- 填空 / 主观 -->
        <template v-else>
          <el-form-item label="参考答案">
            <el-input v-model="form.correct_answer" type="textarea" :rows="2" placeholder="填空 / 主观题的参考答案" />
          </el-form-item>
        </template>

        <el-form-item label="解析">
          <el-input v-model="form.explanation" type="textarea" :rows="2" placeholder="选填" />
        </el-form-item>

        <el-form-item label="标签">
          <el-select v-model="form.tag_ids" multiple filterable placeholder="选填" style="width:100%">
            <el-option v-for="t in tags" :key="t.id" :value="t.id" :label="`${t.name}（${t.category}）`" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dlgVisible = false">取消</el-button>
        <el-button type="primary" :loading="dlgLoading" @click="onSubmit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <el-dialog
      v-model="importVisible"
      title="批量导入题目"
      width="720px"
      :close-on-click-modal="false"
    >
      <el-tabs v-model="importMode">
        <el-tab-pane label="JSON 数组" name="json">
          <div class="hint">
            顶层为数组，每个元素是一道题。学科 / 章节 / 标签可用名称（subject / chapter / tags），
            前端会自动转成 ID。点
            <el-link type="primary" @click="downloadTemplate('json')">下载 JSON 模板</el-link>
            查看示例。
          </div>
          <el-upload
            class="upload-line"
            accept=".json,application/json"
            :show-file-list="false"
            :before-upload="onJsonFileChange"
          >
            <el-button :icon="'Upload'">从文件读取</el-button>
          </el-upload>
          <el-input
            v-model="importJsonText"
            type="textarea"
            :rows="12"
            placeholder='[{"subject": "数学", "question_type": "single_choice", "title": "...", "options": ["1","2"], "correct_answer": "1", "difficulty": "easy"}]'
          />
        </el-tab-pane>

        <el-tab-pane label="CSV 表格" name="csv">
          <div class="hint">
            首行为表头，列：<code>{{ CSV_HEADERS.join(', ') }}</code>。
            其中 <code>options</code> / <code>tags</code> 用 <code>|</code> 分隔多值，
            多选题的 <code>correct_answer</code> 也用 <code>|</code> 分隔。点
            <el-link type="primary" @click="downloadTemplate('csv')">下载 CSV 模板</el-link>
            。
          </div>
          <el-upload
            class="upload-line"
            accept=".csv,text/csv"
            :show-file-list="false"
            :before-upload="onCsvFileChange"
          >
            <el-button :icon="'Upload'">从文件读取</el-button>
          </el-upload>
          <el-input
            v-model="importCsvText"
            type="textarea"
            :rows="12"
            placeholder="subject,chapter,question_type,title,...&#10;数学,第一章,single_choice,1+1=?,..."
          />
        </el-tab-pane>
      </el-tabs>

      <!-- 导入结果 -->
      <el-alert
        v-if="importResult"
        class="result"
        :type="importResult.failed_count === 0 ? 'success' : (importResult.imported_count > 0 ? 'warning' : 'error')"
        :title="`成功 ${importResult.imported_count} 条，失败 ${importResult.failed_count} 条`"
        :closable="false"
        show-icon
      />
      <el-table
        v-if="importResult?.errors?.length"
        :data="importResult.errors"
        size="small"
        max-height="200"
        class="result"
      >
        <el-table-column prop="index" label="行号" width="80">
          <template #default="{ row }">第 {{ row.index + 1 }} 条</template>
        </el-table-column>
        <el-table-column prop="error" label="错误信息" />
      </el-table>

      <template #footer>
        <el-button @click="importVisible = false">关闭</el-button>
        <el-button
          type="primary"
          :loading="importLoading"
          :disabled="importMode === 'json' ? !importJsonText.trim() : !importCsvText.trim()"
          @click="doImport"
        >开始导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  flex-wrap: wrap;
  gap: 8px;
}
.filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
.options-edit {
  width: 100%;
}
.option-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.hint {
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}
.hint code {
  background: var(--el-bg-color-page);
  padding: 0 4px;
  border-radius: 3px;
}
.upload-line {
  margin-bottom: 8px;
}
.result {
  margin-top: 12px;
}
</style>
