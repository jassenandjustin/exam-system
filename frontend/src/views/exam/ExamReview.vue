<script setup>
/**
 * 试卷回顾（教师/管理员）：
 *  - 总体情况：参加 / 进行中 / 平均分 / 及格（≥60% 总分）/ 优秀（≥85% 总分）
 *  - 章统计：正确人数、正确率、薄弱章（<60%）高亮
 *  - 试题回顾：每题答对/答错人数与正确率（最差在前）
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { TooltipComponent, GridComponent, LegendComponent } from 'echarts/components'

import api from '@/api'

use([
  CanvasRenderer,
  BarChart,
  TooltipComponent, GridComponent, LegendComponent
])

const route = useRoute()
const router = useRouter()
const paperId = Number(route.params.id)

const paper = ref(null)
const overview = ref(null)
const chapters = ref([])
const questions = ref([])
const loading = ref(false)

const EXAM_TYPE_MAP = {
  quick: '快速练习',
  standard: '标准考试',
  comprehensive: '综合考试',
  custom: '自定义考试',
}
const QUESTION_TYPE_MAP = {
  single_choice: '单选',
  multiple_choice: '多选',
  fill_in_blank: '填空',
  true_false: '判断',
  subjective: '主观',
}
const STATUS_MAP = {
  not_started: { label: '未开始', type: 'info' },
  available: { label: '进行中', type: 'success' },
  ended: { label: '已结束', type: 'danger' },
}

async function loadReview() {
  loading.value = true
  try {
    const { data } = await api.get(`/exam/papers/${paperId}/review`)
    paper.value = data.paper
    overview.value = data.overview
    chapters.value = data.chapters || []
    questions.value = data.questions || []
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '加载试卷回顾失败')
    router.replace('/exam/teacher')
  } finally {
    loading.value = false
  }
}

function fmtDate(s) {
  if (!s) return '—'
  return new Date(s).toLocaleString()
}

const hasData = computed(() => overview.value && overview.value.participants > 0)

const chapterChartOption = computed(() => {
  if (!chapters.value.length) return {}
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['正确率(%)'], top: 0 },
    grid: { left: 12, right: 12, bottom: 12, top: 40, containLabel: true },
    xAxis: {
      type: 'category',
      data: chapters.value.map(c => c.chapter_name),
      axisLabel: { rotate: 25, interval: 0 }
    },
    yAxis: { type: 'value', name: '%', min: 0, max: 100 },
    series: [{
      name: '正确率(%)', type: 'bar',
      data: chapters.value.map(c => c.accuracy),
      itemStyle: { color: '#409EFF' },
      barMaxWidth: 40,
      label: { show: true, position: 'top', formatter: '{c}%' }
    }]
  }
})

const overviewCards = computed(() => {
  const ov = overview.value
  if (!ov) return []
  return [
    { label: '已交卷人数', value: ov.participants, suffix: ' 人', tone: 'primary' },
    { label: '进行中', value: ov.in_progress, suffix: ' 人', tone: 'warning' },
    { label: '平均分', value: ov.avg_obtained, suffix: ` / ${ov.total_score}`, tone: 'info' },
    { label: '及格人数', value: ov.pass_count, suffix: ` 人（${ov.pass_rate}%）`, tone: 'success' },
    { label: '及格率', value: ov.pass_rate, suffix: ' %', tone: 'success' },
    { label: '优秀人数', value: ov.excellent_count, suffix: ` 人（${ov.excellent_rate}%）`, tone: 'danger' },
    { label: '优秀率', value: ov.excellent_rate, suffix: ' %', tone: 'danger' },
  ]
})

const weakChapters = computed(() => chapters.value.filter(c => c.is_weak))

onMounted(loadReview)
</script>

<template>
  <div class="exam-review" v-loading="loading">
    <div class="page-header">
      <el-button text @click="router.push('/exam/teacher')">
        <el-icon><ArrowLeft /></el-icon> 返回
      </el-button>
      <h2>试卷回顾</h2>
    </div>

    <template v-if="paper">
      <!-- 试卷信息 -->
      <el-card class="block">
        <el-descriptions :column="3" border>
          <el-descriptions-item label="名称">{{ paper.name }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ EXAM_TYPE_MAP[paper.exam_type] || paper.exam_type }}</el-descriptions-item>
          <el-descriptions-item label="出题人">{{ paper.creator || '—' }}</el-descriptions-item>
          <el-descriptions-item label="总分">{{ paper.total_score }}</el-descriptions-item>
          <el-descriptions-item label="总题数">{{ paper.total_questions }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="STATUS_MAP[paper.status]?.type || 'success'" size="small">
              {{ STATUS_MAP[paper.status]?.label || '进行中' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ fmtDate(paper.start_time) }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ fmtDate(paper.end_time) }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 总体情况 -->
      <el-card class="block">
        <template #header>
          <div class="block-head">
            <span>总体情况</span>
            <span class="muted">及格线 = 总分 × 60%（{{ (paper.total_score * 0.6).toFixed(1) }} 分）；优秀线 = 总分 × 85%（{{ (paper.total_score * 0.85).toFixed(1) }} 分）</span>
          </div>
        </template>

        <el-empty v-if="!hasData" description="暂无学生交卷，暂无回顾数据" :image-size="80" />

        <template v-else>
          <el-row :gutter="16">
            <el-col :xs="12" :sm="8" :md="6" v-for="card in overviewCards" :key="card.label">
              <el-card class="stat-card" :class="`tone-${card.tone}`" shadow="never">
                <div class="stat-label">{{ card.label }}</div>
                <div class="stat-value">{{ card.value }}<span class="stat-suffix">{{ card.suffix }}</span></div>
              </el-card>
            </el-col>
          </el-row>

          <!-- 章统计 -->
          <div class="section-title">章正确情况</div>
          <template v-if="chapters.length">
            <el-alert
              v-if="weakChapters.length"
              type="warning"
              :closable="false"
              show-icon
              class="weak-alert"
            >
              <template #title>
                薄弱章：{{ weakChapters.map(c => c.chapter_name).join('、') }}（正确率低于 60%）
              </template>
            </el-alert>
            <el-row :gutter="16">
              <el-col :xs="24" :md="12">
                <el-table :data="chapters" stripe size="small">
                  <el-table-column prop="chapter_name" label="章" min-width="120" />
                  <el-table-column prop="question_count" label="卷内题数" width="90" align="center" />
                  <el-table-column prop="answered" label="答题记录" width="90" align="center" />
                  <el-table-column prop="correct_people" label="正确人数" width="90" align="center" />
                  <el-table-column label="正确率" width="170">
                    <template #default="{ row }">
                      <el-progress
                        :percentage="row.accuracy"
                        :color="row.accuracy >= 80 ? '#67C23A'
                          : row.accuracy >= 60 ? '#E6A23C' : '#F56C6C'"
                      />
                    </template>
                  </el-table-column>
                  <el-table-column label="薄弱" width="70" align="center">
                    <template #default="{ row }">
                      <el-tag v-if="row.is_weak" type="danger" size="small" effect="light">薄弱</el-tag>
                    </template>
                  </el-table-column>
                </el-table>
              </el-col>
              <el-col :xs="24" :md="12">
                <v-chart :option="chapterChartOption" autoresize style="height: 300px" />
              </el-col>
            </el-row>
          </template>
          <el-empty v-else description="试卷题目均未挂章" :image-size="80" />

          <!-- 试题回顾 -->
          <div class="section-title">试题回顾</div>
          <el-table :data="questions" stripe size="small">
            <el-table-column prop="order_num" label="序号" width="60" />
            <el-table-column label="题型" width="80">
              <template #default="{ row }">
                {{ QUESTION_TYPE_MAP[row.question_type] || row.question_type }}
              </template>
            </el-table-column>
            <el-table-column prop="title" label="题干" min-width="240" show-overflow-tooltip />
            <el-table-column prop="score" label="分值" width="70" align="center" />
            <el-table-column prop="correct_count" label="答对人数" width="90" align="center">
              <template #default="{ row }">
                <span class="ok-text">{{ row.correct_count }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="wrong_count" label="答错人数" width="90" align="center">
              <template #default="{ row }">
                <span class="err-text">{{ row.wrong_count }}</span>
              </template>
            </el-table-column>
            <el-table-column label="正确率" min-width="200">
              <template #default="{ row }">
                <el-progress
                  :percentage="row.accuracy"
                  :color="row.accuracy >= 80 ? '#67C23A'
                    : row.accuracy >= 60 ? '#E6A23C' : '#F56C6C'"
                />
              </template>
            </el-table-column>
          </el-table>
        </template>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.exam-review {
  max-width: 1200px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
}
.block {
  margin-bottom: 16px;
}
.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.muted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.stat-card {
  margin-bottom: 16px;
  border-left: 3px solid var(--el-color-primary);
}
.stat-card.tone-success { border-left-color: var(--el-color-success); }
.stat-card.tone-info { border-left-color: var(--el-color-info); }
.stat-card.tone-warning { border-left-color: var(--el-color-warning); }
.stat-card.tone-danger { border-left-color: var(--el-color-danger); }
.stat-card .stat-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}
.stat-card .stat-value {
  font-size: 22px;
  font-weight: 600;
  margin-top: 4px;
}
.stat-card .stat-suffix {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  font-weight: normal;
  margin-left: 4px;
}
.section-title {
  font-weight: 600;
  margin: 20px 0 10px;
}
.weak-alert {
  margin-bottom: 12px;
}
.ok-text {
  color: var(--el-color-success);
  font-weight: 600;
}
.err-text {
  color: var(--el-color-danger);
  font-weight: 600;
}
</style>
