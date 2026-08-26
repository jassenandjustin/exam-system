<script setup>
/**
 * 学生模拟考试页：
 *  - 可参加的考试列表（教师发布的试卷）
 *  - 进行中考试提示
 *  - 考试历史
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const availableExams = ref([])
const inProgress = ref(null)
const history = ref([])
const historyTotal = ref(0)
const historyPage = ref(1)
const loading = ref(false)

const EXAM_TYPE_MAP = {
  quick: { label: '快速练习', color: '#67c23a' },
  standard: { label: '标准考试', color: '#409eff' },
  comprehensive: { label: '综合考试', color: '#e6a23c' },
  custom: { label: '自定义考试', color: '#909399' },
}

async function loadAvailable() {
  try {
    const { data } = await api.get('/exam/available')
    availableExams.value = data.items || []
  } catch {
    ElMessage.error('加载可用考试失败')
  }
}

async function loadInProgress() {
  try {
    const { data } = await api.get('/exam/in-progress')
    inProgress.value = data.in_progress ? data : null
  } catch {
    inProgress.value = null
  }
}

async function loadHistory(page = historyPage.value) {
  try {
    const { data } = await api.get('/exam/history', { params: { page, per_page: 10 } })
    history.value = data.items
    historyTotal.value = data.total
    historyPage.value = data.current_page
  } catch {
    ElMessage.error('加载历史失败')
  }
}

async function reloadAll() {
  loading.value = true
  await Promise.all([loadAvailable(), loadInProgress(), loadHistory(1)])
  loading.value = false
}

async function startExam(paperId) {
  loading.value = true
  try {
    const { data } = await api.post(`/exam/start/${paperId}`)
    ElMessage.success('已开考，祝你好运！')
    router.push(`/exam/run/${data.exam_id}`)
  } catch (err) {
    if (err.response?.status === 409 && err.response.data?.exam_id) {
      try {
        await ElMessageBox.confirm(
          '你还有一场考试未提交，是否继续作答？',
          '存在进行中的考试',
          { confirmButtonText: '去继续', cancelButtonText: '取消', type: 'warning' }
        )
        router.push(`/exam/run/${err.response.data.exam_id}`)
      } catch { /* user cancel */ }
    } else {
      ElMessage.error(err.response?.data?.error || '开始考试失败')
    }
  } finally {
    loading.value = false
  }
}

function continueExam() {
  if (inProgress.value?.exam_id) {
    router.push(`/exam/run/${inProgress.value.exam_id}`)
  }
}

function viewResult(row) {
  router.push(`/exam/result/${row.exam_id}`)
}

function formatDuration(sec) {
  if (!sec && sec !== 0) return '—'
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}分${s.toString().padStart(2, '0')}秒`
}

function fmtDate(s) {
  if (!s) return '—'
  return new Date(s).toLocaleString()
}

const accuracyTagType = (acc) => {
  if (acc === null || acc === undefined) return 'info'
  if (acc >= 80) return 'success'
  if (acc >= 60) return 'warning'
  return 'danger'
}

onMounted(reloadAll)
</script>

<template>
  <div class="exam-page" v-loading="loading">
    <h2>模拟考试</h2>

    <!-- 进行中提示 -->
    <el-alert
      v-if="inProgress"
      type="warning"
      :closable="false"
      show-icon
      class="alert"
    >
      <template #title>
        <span>你有一场未提交的考试（{{ inProgress.exam_name || inProgress.exam_type }}），截止时间 {{ fmtDate(inProgress.deadline) }}</span>
        <el-button type="primary" size="small" class="alert-btn" @click="continueExam">继续作答</el-button>
      </template>
    </el-alert>

    <!-- 可参加的考试 -->
    <el-card class="block">
      <template #header>可参加的考试</template>

      <el-empty v-if="!availableExams.length" description="暂无可参加的考试，请等待教师发布" />

      <el-row v-else :gutter="16">
        <el-col v-for="exam in availableExams" :key="exam.id" :xs="24" :sm="12" :md="8">
          <el-card class="exam-card" shadow="hover">
            <div class="exam-card-header">
              <span class="exam-name">{{ exam.name }}</span>
              <el-tag
                :color="EXAM_TYPE_MAP[exam.exam_type]?.color"
                effect="dark"
                size="small"
              >
                {{ EXAM_TYPE_MAP[exam.exam_type]?.label || exam.exam_type }}
              </el-tag>
            </div>
            <p class="exam-desc">{{ exam.description || '暂无描述' }}</p>
            <div class="exam-meta">
              <span><el-icon><Clock /></el-icon> {{ exam.duration_minutes }} 分钟</span>
              <span><el-icon><Document /></el-icon> {{ exam.total_questions }} 题</span>
              <span><el-icon><Trophy /></el-icon> {{ exam.total_score }} 分</span>
            </div>
            <div class="exam-creator">出题人: {{ exam.creator }}</div>
            <div class="exam-action">
              <el-button
                v-if="exam.has_taken"
                type="info"
                disabled
                size="small"
              >已参加过</el-button>
              <el-button
                v-else
                type="primary"
                size="small"
                @click="startExam(exam.id)"
              >开始考试</el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- 历史 -->
    <el-card class="block">
      <template #header>考试历史</template>
      <el-table :data="history" stripe>
        <el-table-column prop="exam_id" label="ID" width="60" />
        <el-table-column label="考试名称" width="160">
          <template #default="{ row }">{{ row.exam_name || row.exam_type }}</template>
        </el-table-column>
        <el-table-column prop="exam_type" label="类型" width="100">
          <template #default="{ row }">{{ EXAM_TYPE_MAP[row.exam_type]?.label || row.exam_type }}</template>
        </el-table-column>
        <el-table-column label="开始时间" width="170">
          <template #default="{ row }">{{ fmtDate(row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.submitted" type="success" size="small">已交卷</el-tag>
            <el-tag v-else type="warning" size="small">进行中</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="得分" width="120">
          <template #default="{ row }">
            <span v-if="row.submitted">{{ row.obtained_score }} / {{ row.total_score }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="正确率" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.accuracy !== null" :type="accuracyTagType(row.accuracy)" effect="light">
              {{ row.accuracy }}%
            </el-tag>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="用时" width="120">
          <template #default="{ row }">{{ formatDuration(row.used_seconds) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button v-if="row.submitted" size="small" @click="viewResult(row)">查看报告</el-button>
            <el-button v-else size="small" type="primary" @click="$router.push(`/exam/run/${row.exam_id}`)">
              继续
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        class="pager"
        background
        layout="total, prev, pager, next"
        :total="historyTotal"
        :page-size="10"
        :current-page="historyPage"
        @current-change="loadHistory"
      />
    </el-card>
  </div>
</template>

<style scoped>
.exam-page {
  max-width: 1100px;
  margin: 0 auto;
}
.alert {
  margin-bottom: 16px;
}
.alert-btn {
  margin-left: 12px;
}
.block {
  margin-bottom: 16px;
}
.exam-card {
  margin-bottom: 16px;
}
.exam-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}
.exam-name {
  font-size: 16px;
  font-weight: 600;
  flex: 1;
  margin-right: 8px;
}
.exam-desc {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin-bottom: 8px;
  min-height: 20px;
}
.exam-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  margin-bottom: 4px;
}
.exam-meta span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.exam-creator {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 12px;
}
.exam-action {
  text-align: right;
}
.muted {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
