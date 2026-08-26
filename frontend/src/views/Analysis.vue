<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import {
  LineChart, BarChart, PieChart, RadarChart
} from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, GridComponent, LegendComponent,
  DataZoomComponent
} from 'echarts/components'

import { useAuthStore } from '@/stores/auth'
import api from '@/api'

use([
  CanvasRenderer,
  LineChart, BarChart, PieChart, RadarChart,
  TitleComponent, TooltipComponent, GridComponent, LegendComponent, DataZoomComponent
])

const auth = useAuthStore()
const userId = computed(() => auth.userId)

// ===== 顶部时间范围 =====
const periodDays = ref(30)
const periodOptions = [
  { value: 7, label: '近 7 天' },
  { value: 30, label: '近 30 天' },
  { value: 90, label: '近 90 天' }
]

// ===== 数据 =====
const stats = ref(null)              // /stats
const trend = ref(null)              // /trend
const subjects = ref([])             // /subject-analysis
const weakPoints = ref([])           // /weak-points
const typeDist = ref([])             // /type-distribution
const report = ref(null)             // /report
const recommends = ref([])           // /recommend

const reportType = ref('week')
const loading = ref(false)

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
const TREND_TEXT = {
  up: { txt: '上升', tag: 'success', icon: 'TrendCharts' },
  down: { txt: '下降', tag: 'danger', icon: 'Bottom' },
  stable: { txt: '稳定', tag: 'info', icon: 'DataLine' }
}

async function loadAll() {
  if (!userId.value) return
  loading.value = true
  try {
    const [s, t, sub, w, td, rep, rec] = await Promise.all([
      api.get(`/analysis/stats/${userId.value}`, { params: { days: periodDays.value } }),
      api.get(`/analysis/trend/${userId.value}`, { params: { days: periodDays.value } }),
      api.get(`/analysis/subject-analysis/${userId.value}`),
      api.get(`/analysis/weak-points/${userId.value}`, { params: { limit: 8 } }),
      api.get(`/analysis/type-distribution/${userId.value}`),
      api.get(`/analysis/report/${userId.value}`, { params: { type: reportType.value } }),
      api.get(`/analysis/recommend/${userId.value}`, { params: { count: 6 } })
    ])
    stats.value = s.data
    trend.value = t.data.trend
    subjects.value = sub.data.subjects || []
    weakPoints.value = w.data.weak_points || []
    typeDist.value = td.data.distribution || []
    report.value = rep.data.report
    recommends.value = rec.data.questions || []
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '加载分析数据失败')
  } finally {
    loading.value = false
  }
}

watch(periodDays, loadAll)

async function refreshReport() {
  try {
    const { data } = await api.get(`/analysis/report/${userId.value}`,
      { params: { type: reportType.value } })
    report.value = data.report
  } catch (err) {
    ElMessage.error('刷新报告失败')
  }
}

// ===== 图表配置 =====
const trendOption = computed(() => {
  if (!trend.value) return {}
  return {
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['练习量', '正确率(%)', '平均用时(s)'],
      top: 4
    },
    // containLabel:true 让 echarts 自动给坐标轴标签留位置，避免日期斜排时戳到图例区
    grid: { left: 12, right: 12, bottom: 12, top: 64, containLabel: true },
    xAxis: {
      type: 'category',
      data: trend.value.dates,
      boundaryGap: false,
      axisLabel: {
        interval: 'auto',   // 日期太密时自动稀释
        rotate: 35,         // 斜着排避免重叠
        margin: 10
      }
    },
    yAxis: [
      { type: 'value', name: '题量', position: 'left', nameGap: 24 },
      { type: 'value', name: '%', min: 0, max: 100, position: 'right', nameGap: 18 }
    ],
    series: [
      {
        name: '练习量', type: 'bar', yAxisIndex: 0,
        data: trend.value.practice_counts,
        itemStyle: { color: '#409EFF' },
        barMaxWidth: 24
      },
      {
        name: '正确率(%)', type: 'line', yAxisIndex: 1,
        data: trend.value.accuracies, smooth: true,
        itemStyle: { color: '#67C23A' }
      },
      {
        name: '平均用时(s)', type: 'line', yAxisIndex: 0,
        data: trend.value.avg_times, smooth: true,
        itemStyle: { color: '#E6A23C' }
      }
    ]
  }
})

const subjectRadarOption = computed(() => {
  if (!subjects.value.length) return {}
  return {
    tooltip: { trigger: 'item' },
    radar: {
      indicator: subjects.value.map(s => ({
        name: s.subject_name, max: 100
      })),
      radius: '65%'
    },
    series: [{
      type: 'radar',
      data: [{
        value: subjects.value.map(s => s.accuracy),
        name: '正确率 (%)',
        areaStyle: { color: 'rgba(64,158,255,0.25)' },
        lineStyle: { color: '#409EFF' }
      }]
    }]
  }
})

const subjectBarOption = computed(() => {
  if (!subjects.value.length) return {}
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['练习量', '正确率(%)'] },
    grid: { left: 50, right: 50, bottom: 30, top: 40 },
    xAxis: { type: 'category', data: subjects.value.map(s => s.subject_name) },
    yAxis: [
      { type: 'value', name: '题量', position: 'left' },
      { type: 'value', name: '%', min: 0, max: 100, position: 'right' }
    ],
    series: [
      {
        name: '练习量', type: 'bar', yAxisIndex: 0,
        data: subjects.value.map(s => s.total_practice),
        itemStyle: { color: '#409EFF' },
        barMaxWidth: 32
      },
      {
        name: '正确率(%)', type: 'line', yAxisIndex: 1, smooth: true,
        data: subjects.value.map(s => s.accuracy),
        itemStyle: { color: '#67C23A' }
      }
    ]
  }
})

const typeOption = computed(() => {
  if (!typeDist.value.length) return {}
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: true,
      label: { formatter: '{b}\n{c} 题' },
      data: typeDist.value.map(t => ({
        name: TYPE_LABEL[t.question_type] || t.question_type,
        value: t.total
      }))
    }]
  }
})

onMounted(loadAll)
</script>

<template>
  <div class="analysis-page" v-loading="loading">
    <div class="page-head">
      <h2>学习分析</h2>
      <div class="head-actions">
        <el-segmented v-model="periodDays" :options="periodOptions" />
        <el-button :icon="'Refresh'" @click="loadAll">刷新</el-button>
      </div>
    </div>

    <!-- 概览 -->
    <el-row :gutter="16" v-if="stats">
      <el-col :xs="12" :sm="8" :md="6" v-for="card in [
        { label: '累计练习', value: stats.overall.total_practice, suffix: ' 题', tone: 'primary' },
        { label: '总体正确率', value: stats.overall.accuracy, suffix: ' %', tone: 'success' },
        { label: '已练题数', value: stats.overall.practiced_questions, suffix: ` / ${stats.overall.total_questions}`, tone: 'info' },
        { label: '题库覆盖率', value: stats.overall.coverage, suffix: ' %', tone: 'info' },
        { label: '错题数', value: stats.overall.error_count, suffix: ' 道', tone: 'danger' },
        { label: '收藏数', value: stats.overall.favorite_count, suffix: ' 道', tone: 'warning' },
        { label: '总学习时长', value: stats.overall.total_time_minutes, suffix: ' 分钟', tone: 'primary' },
        { label: '连续打卡', value: stats.overall.streak_days, suffix: ' 天', tone: 'success' }
      ]" :key="card.label">
        <el-card class="stat-card" :class="`tone-${card.tone}`" shadow="never">
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value">{{ card.value }}<span class="stat-suffix">{{ card.suffix }}</span></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势 -->
    <el-card class="block">
      <template #header>
        <div class="block-head">
          <span>每日学习趋势</span>
          <el-tag
            v-if="trend"
            :type="TREND_TEXT[trend.direction].tag"
            effect="light"
            size="small"
          >
            <el-icon><component :is="TREND_TEXT[trend.direction].icon" /></el-icon>
            {{ TREND_TEXT[trend.direction].txt }}
          </el-tag>
          <span class="muted">最近 {{ periodDays }} 天</span>
        </div>
      </template>
      <v-chart
        v-if="trend && trend.dates.length"
        :option="trendOption"
        autoresize
        style="height: 360px"
      />
      <el-empty v-else description="暂无练习数据" :image-size="80" />
    </el-card>

    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <el-card class="block">
          <template #header>学科正确率（雷达图）</template>
          <v-chart
            v-if="subjects.length"
            :option="subjectRadarOption"
            autoresize
            style="height: 320px"
          />
          <el-empty v-else description="暂无学科数据" :image-size="80" />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card class="block">
          <template #header>题型分布</template>
          <v-chart
            v-if="typeDist.length"
            :option="typeOption"
            autoresize
            style="height: 320px"
          />
          <el-empty v-else description="暂无题型数据" :image-size="80" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 学科练习量 / 正确率 -->
    <el-card class="block" v-if="subjects.length">
      <template #header>各学科练习量与正确率</template>
      <v-chart :option="subjectBarOption" autoresize style="height: 300px" />
    </el-card>

    <!-- 薄弱知识点 -->
    <el-card class="block">
      <template #header>
        <div class="block-head">
          <span>薄弱知识点</span>
          <span class="muted">基于错题标签聚合</span>
        </div>
      </template>
      <el-empty v-if="!weakPoints.length" description="暂无错题，未发现薄弱点" :image-size="80" />
      <el-table v-else :data="weakPoints" stripe size="small">
        <el-table-column prop="tag_name" label="知识点" />
        <el-table-column prop="tag_category" label="分类" width="120" />
        <el-table-column prop="error_count" label="错题次数" width="100" align="center" />
        <el-table-column prop="total_practice" label="练习次数" width="100" align="center" />
        <el-table-column label="掌握度" width="180">
          <template #default="{ row }">
            <el-progress
              :percentage="row.mastery_level"
              :color="row.mastery_level >= 80 ? '#67C23A'
                : row.mastery_level >= 60 ? '#E6A23C' : '#F56C6C'"
            />
          </template>
        </el-table-column>
        <el-table-column label="建议练习" width="120" align="center">
          <template #default="{ row }">{{ row.recommend_practice }} 题</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 报告 + 推荐 -->
    <el-row :gutter="16">
      <el-col :xs="24" :md="14">
        <el-card class="block">
          <template #header>
            <div class="block-head">
              <span>学习报告</span>
              <el-radio-group v-model="reportType" size="small" @change="refreshReport">
                <el-radio-button value="week">周报</el-radio-button>
                <el-radio-button value="month">月报</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div v-if="report" class="report">
            <div class="report-head">
              <span>{{ report.start_date }} ~ {{ report.end_date }}</span>
              <el-tag>练习 {{ report.total_practice }} 题</el-tag>
              <el-tag type="success">正确率 {{ report.accuracy }}%</el-tag>
              <el-tag type="warning">错题 {{ report.error_count }}</el-tag>
              <el-tag type="info">打卡 {{ report.active_days }} 天</el-tag>
            </div>
            <div class="report-section">
              <div class="section-title">坚持度</div>
              <el-progress
                :percentage="report.consistency_score"
                :color="report.consistency_score >= 80 ? '#67C23A'
                  : report.consistency_score >= 50 ? '#E6A23C' : '#F56C6C'"
              />
            </div>
            <div class="report-section" v-if="report.subjects_performance.length">
              <div class="section-title">学科表现</div>
              <el-table :data="report.subjects_performance" size="small">
                <el-table-column prop="subject" label="学科" />
                <el-table-column prop="practice_count" label="练习量" width="100" align="center" />
                <el-table-column prop="accuracy" label="正确率(%)" width="120" align="center" />
              </el-table>
            </div>
            <div class="report-section" v-if="report.suggestions.length">
              <div class="section-title">学习建议</div>
              <ul class="suggestion-list">
                <li v-for="(s, i) in report.suggestions" :key="i">{{ s }}</li>
              </ul>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="10">
        <el-card class="block">
          <template #header>智能推荐</template>
          <el-empty v-if="!recommends.length" description="暂无推荐题目" :image-size="80" />
          <ul v-else class="recommend-list">
            <li v-for="q in recommends" :key="q.id">
              <el-tag size="small" :type="DIFF_LABEL[q.difficulty]?.tag" effect="light">
                {{ DIFF_LABEL[q.difficulty]?.label || q.difficulty }}
              </el-tag>
              <span class="rec-title">{{ q.title }}</span>
              <span class="rec-reason">{{ q.recommend_reason }}</span>
            </li>
          </ul>
          <div class="rec-foot">
            <el-button type="primary" :icon="'EditPen'" @click="$router.push('/practice/sequential')">
              去练习
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.analysis-page {
  max-width: 1200px;
  margin: 0 auto;
}
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.page-head h2 {
  margin: 0;
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
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
.block {
  margin-bottom: 16px;
}
.block-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.muted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin-left: auto;
}
.report-head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}
.report-section {
  margin-top: 12px;
}
.section-title {
  font-weight: 600;
  margin-bottom: 6px;
}
.suggestion-list {
  margin: 0;
  padding-left: 18px;
  color: var(--el-text-color-regular);
  line-height: 1.8;
}
.recommend-list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.recommend-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px dashed var(--el-border-color-light);
}
.recommend-list li:last-child {
  border-bottom: none;
}
.rec-title {
  flex: 1;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.rec-reason {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}
.rec-foot {
  margin-top: 12px;
  text-align: center;
}
</style>
