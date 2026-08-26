<script setup>
/**
 * 试卷管理页（选题规则 + 题目预览 + 发布）
 */
import { onMounted, ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import RuleForm from './RuleForm.vue'

const router = useRouter()
const route = useRoute()
const paperId = computed(() => route.params.id)

const paper = ref(null)
const loading = ref(false)
const showRuleForm = ref(false)

const EXAM_TYPE_MAP = {
  quick: '快速练习',
  standard: '标准考试',
  comprehensive: '综合考试',
  custom: '自定义考试',
}

const DIFFICULTY_MAP = {
  easy: '简单',
  medium: '中等',
  hard: '困难',
}

const QUESTION_TYPE_MAP = {
  single_choice: '单选',
  multiple_choice: '多选',
  fill_in_blank: '填空',
  true_false: '判断',
  subjective: '主观',
}

function typeDistributionEntries(distribution) {
  if (!distribution) return []
  return Object.entries(distribution).filter(([, count]) => Number(count) > 0)
}

function hasTypeDistribution(row) {
  return typeDistributionEntries(row.type_distribution).length > 0
}

function typeAvailable(row, type) {
  return Number(row.available_by_type?.[type] || 0)
}

async function loadPaper() {
  loading.value = true
  try {
    const { data } = await api.get(`/exam/papers/${paperId.value}`)
    paper.value = data
  } catch {
    ElMessage.error('加载试卷失败')
  } finally {
    loading.value = false
  }
}

async function addRule(ruleData) {
  try {
    await api.post(`/exam/papers/${paperId.value}/rules`, ruleData)
    ElMessage.success('规则添加成功')
    showRuleForm.value = false
    loadPaper()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '添加规则失败')
  }
}

async function deleteRule(ruleId) {
  try {
    await ElMessageBox.confirm('确定删除此规则？', '确认', { type: 'warning' })
    await api.delete(`/exam/papers/${paperId.value}/rules/${ruleId}`)
    ElMessage.success('删除成功')
    loadPaper()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err.response?.data?.error || '删除失败')
    }
  }
}

async function generateQuestions() {
  if (!paper.value?.rules?.length) {
    ElMessage.warning('请先添加选题规则')
    return
  }
  try {
    const { data } = await api.post(`/exam/papers/${paperId.value}/generate`)
    ElMessage.success(`生成成功：${data.total_questions} 题，总分 ${data.total_score}`)
    loadPaper()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '生成失败')
  }
}

async function togglePublish() {
  if (!paper.value) return
  try {
    if (paper.value.is_published) {
      await api.post(`/exam/papers/${paperId.value}/unpublish`)
      ElMessage.success('已取消发布')
    } else {
      await api.post(`/exam/papers/${paperId.value}/publish`)
      ElMessage.success('发布成功，学生现在可以参加此考试')
    }
    loadPaper()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '操作失败')
  }
}

function editBasicInfo() {
  router.push(`/exam/paper/${paperId.value}/edit`)
}

function goBack() {
  router.push('/exam/teacher')
}

onMounted(loadPaper)
</script>

<template>
  <div class="paper-manage" v-loading="loading">
    <div class="page-header">
      <el-button text @click="goBack"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
      <h2>管理试卷</h2>
    </div>

    <template v-if="paper">
      <!-- 基本信息 -->
      <el-card class="block">
        <template #header>
          <div class="card-title-row">
            <span>试卷信息</span>
            <el-button size="small" @click="editBasicInfo">编辑基本信息</el-button>
          </div>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="名称">{{ paper.name }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ EXAM_TYPE_MAP[paper.exam_type] || paper.exam_type }}</el-descriptions-item>
          <el-descriptions-item label="时长">{{ paper.duration_minutes }} 分钟</el-descriptions-item>
          <el-descriptions-item label="及格分">{{ paper.passing_score }}</el-descriptions-item>
          <el-descriptions-item label="总题数">{{ paper.total_questions || 0 }}</el-descriptions-item>
          <el-descriptions-item label="总分">{{ paper.total_score || 0 }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag v-if="paper.is_published" type="success" size="small">已发布</el-tag>
            <el-tag v-else type="info" size="small">未发布</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="描述">{{ paper.description || '—' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 选题规则 -->
      <el-card class="block">
        <template #header>
          <div class="card-title-row">
            <span>选题规则</span>
            <el-button
              v-if="!paper.is_published"
              type="primary"
              size="small"
              @click="showRuleForm = !showRuleForm"
            >
              {{ showRuleForm ? '收起' : '添加规则' }}
            </el-button>
          </div>
        </template>

        <RuleForm
          v-if="showRuleForm && !paper.is_published"
          @submit="addRule"
          @cancel="showRuleForm = false"
        />

        <el-empty v-if="!paper.rules?.length" description="还没有选题规则，点击上方添加" />

        <el-table v-else :data="paper.rules" stripe>
          <el-table-column prop="order_num" label="序号" width="60" />
          <el-table-column prop="subject_name" label="学科" width="120" />
          <el-table-column prop="chapter_name" label="章节" width="160" />
          <el-table-column label="难度" width="80">
            <template #default="{ row }">
              {{ row.difficulty ? DIFFICULTY_MAP[row.difficulty] || row.difficulty : '不限' }}
            </template>
          </el-table-column>
          <el-table-column label="抽取题数" min-width="180">
            <template #default="{ row }">
              <div class="rule-count-cell">
                <span>{{ row.question_count }} 题</span>
                <div v-if="hasTypeDistribution(row)" class="type-tags">
                  <el-tag
                    v-for="([type, count]) in typeDistributionEntries(row.type_distribution)"
                    :key="type"
                    size="small"
                    effect="plain"
                  >
                    {{ QUESTION_TYPE_MAP[type] || type }} {{ count }}
                  </el-tag>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="可用题数" min-width="170">
            <template #default="{ row }">
              <div class="rule-count-cell">
                <span :class="{ 'warn-text': row.available_count < row.question_count }">
                  {{ row.available_count }}
                </span>
                <div v-if="hasTypeDistribution(row)" class="type-tags">
                  <el-tag
                    v-for="([type, count]) in typeDistributionEntries(row.type_distribution)"
                    :key="type"
                    :type="typeAvailable(row, type) < count ? 'danger' : 'info'"
                    size="small"
                    effect="plain"
                  >
                    {{ QUESTION_TYPE_MAP[type] || type }}可用 {{ typeAvailable(row, type) }}
                  </el-tag>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column v-if="!paper.is_published" label="操作" width="80">
            <template #default="{ row }">
              <el-button type="danger" size="small" text @click="deleteRule(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 题目预览 -->
      <el-card class="block">
        <template #header>
          <div class="card-title-row">
            <span>题目列表 ({{ paper.questions?.length || 0 }} 题)</span>
            <el-button
              v-if="!paper.is_published && paper.rules?.length"
              type="success"
              size="small"
              @click="generateQuestions"
            >
              生成题目
            </el-button>
          </div>
        </template>

        <el-empty v-if="!paper.questions?.length" description="暂无题目，请先添加规则并生成" />

        <el-table v-else :data="paper.questions" stripe max-height="500">
          <el-table-column prop="order_num" label="序号" width="60" />
          <el-table-column label="题型" width="100">
            <template #default="{ row }">
              {{ { single_choice: '单选', multiple_choice: '多选', true_false: '判断', fill_in_blank: '填空', subjective: '主观' }[row.question_type] || row.question_type }}
            </template>
          </el-table-column>
          <el-table-column prop="title" label="题干" show-overflow-tooltip />
          <el-table-column prop="score" label="分值" width="70" />
          <el-table-column label="难度" width="70">
            <template #default="{ row }">{{ DIFFICULTY_MAP[row.difficulty] || row.difficulty }}</template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 底部操作 -->
      <div class="bottom-actions">
        <el-button
          v-if="!paper.is_published && paper.questions?.length"
          type="success"
          size="large"
          @click="togglePublish"
        >
          发布试卷
        </el-button>
        <el-button
          v-if="paper.is_published"
          type="warning"
          size="large"
          @click="togglePublish"
        >
          取消发布
        </el-button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.paper-manage {
  max-width: 1100px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.block {
  margin-bottom: 16px;
}
.card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.warn-text {
  color: var(--el-color-danger);
  font-weight: 600;
}
.rule-count-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.type-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.bottom-actions {
  display: flex;
  justify-content: center;
  padding: 16px 0;
}
</style>
