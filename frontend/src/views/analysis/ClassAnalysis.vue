<script setup>
/**
 * 班级学科分析（教师=任教班级 / 管理员=全部班级）：
 *  - 班级下拉 + 时间范围
 *  - 概览卡片 / 学科练习量与正确率图（修复版图例置顶）/ 班级每日趋势
 *  - 学生列表，可钻取到该学生的个人分析（emit view-student）
 */
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, GridComponent, LegendComponent
} from 'echarts/components'

import api from '@/api'

use([
  CanvasRenderer,
  LineChart, BarChart,
  TitleComponent, TooltipComponent, GridComponent, LegendComponent
])

const emit = defineEmits(['view-student'])

// ===== 班级与时间范围 =====
const classes = ref([])
const classId = ref(null)
const periodDays = ref(30)
const periodOptions = [
  { value: 7, label: '近 7 天' },
  { value: 30, label: '近 30 天' },
  { value: 90, label: '近 90 天' }
]

// ===== 数据 =====
const subjects = ref([])
const students = ref([])
const trend = ref(null)
const loading = ref(false)

const currentClass = computed(() =>
  classes.value.find(c => c.id === classId.value) || null)

async function loadClasses() {
  try {
    const { data } = await api.get('/analysis/teacher/classes', { params: { days: periodDays.value } })
    classes.value = data.classes || []
    if (classes.value.length && !classId.value) {
      classId.value = classes.value[0].id
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '加载班级列表失败')
  }
}

async function loadClassDetail() {
  if (!classId.value) return
  loading.value = true
  try {
    const [sub, stu, tr] = await Promise.all([
      api.get(`/analysis/teacher/classes/${classId.value}/subjects`,
        { params: { days: periodDays.value } }),
      api.get(`/analysis/teacher/classes/${classId.value}/students`),
      api.get(`/analysis/teacher/classes/${classId.value}/trend`,
        { params: { days: periodDays.value } })
    ])
    subjects.value = sub.data.subjects || []
    students.value = stu.data.students || []
    trend.value = tr.data.trend
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '加载班级分析失败')
  } finally {
    loading.value = false
  }
}

function reloadAll() {
  loadClasses().then(loadClassDetail)
}

watch(classId, loadClassDetail)
watch(periodDays, reloadAll)

// ===== 图表 =====
// 与 PersonalAnalysis 的修复版同构：图例置顶 + containLabel + x 轴斜排
const subjectBarOption = computed(() => {
  if (!subjects.value.length) return {}
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['练习量', '正确率(%)'], top: 0 },
    grid: { left: 12, right: 12, bottom: 12, top: 56, containLabel: true },
    xAxis: {
      type: 'category',
      data: subjects.value.map(s => s.subject_name),
      axisLabel: { rotate: 30, interval: 0 }
    },
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

const trendOption = computed(() => {
  if (!trend.value || !trend.value.dates.length) return {}
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['练习量', '正确率(%)'], top: 0 },
    grid: { left: 12, right: 12, bottom: 12, top: 56, containLabel: true },
    xAxis: {
      type: 'category',
      data: trend.value.dates,
      boundaryGap: false,
      axisLabel: { interval: 'auto', rotate: 35, margin: 10 }
    },
    yAxis: [
      { type: 'value', name: '题量', position: 'left' },
      { type: 'value', name: '%', min: 0, max: 100, position: 'right' }
    ],
    series: [
      {
        name: '练习量', type: 'bar', yAxisIndex: 0,
        data: trend.value.practice_counts,
        itemStyle: { color: '#409EFF' },
        barMaxWidth: 24
      },
      {
        name: '正确率(%)', type: 'line', yAxisIndex: 1, smooth: true,
        data: trend.value.accuracies,
        itemStyle: { color: '#67C23A' }
      }
    ]
  }
})

const accuracyTagType = (acc) => {
  if (acc >= 80) return 'success'
  if (acc >= 60) return 'warning'
  return 'danger'
}

function fmtAvgTime(sec) {
  if (!sec) return '—'
  return `${sec}s / 题`
}

onMounted(reloadAll)
</script>

<template>
  <div class="class-analysis" v-loading="loading">
    <div class="page-head">
      <h3>班级学科分析</h3>
      <div class="head-actions">
        <el-select
          v-model="classId"
          placeholder="选择班级"
          style="width: 180px"
          :disabled="classes.length === 0"
        >
          <el-option v-for="c in classes" :key="c.id" :value="c.id" :label="c.name" />
        </el-select>
        <el-segmented v-model="periodDays" :options="periodOptions" />
        <el-button :icon="'Refresh'" @click="reloadAll">刷新</el-button>
      </div>
    </div>

    <el-empty v-if="!classes.length" description="暂无可查看的班级" />

    <template v-else-if="currentClass">
      <!-- 概览卡片 -->
      <el-row :gutter="16">
        <el-col :xs="12" :sm="8" :md="4" v-for="card in [
          { label: '学生数', value: currentClass.student_count, suffix: ' 人', tone: 'primary' },
          { label: `近 ${periodDays} 天练习量`, value: currentClass.period_practice, suffix: ' 题', tone: 'primary' },
          { label: '活跃学生', value: currentClass.active_students, suffix: ' 人', tone: 'success' },
          { label: '累计练习', value: currentClass.total_practice, suffix: ' 题', tone: 'info' },
          { label: '总体正确率', value: currentClass.accuracy, suffix: ' %', tone: 'success' },
          { label: '平均用时', value: currentClass.avg_time_seconds, suffix: ' s/题', tone: 'warning' }
        ]" :key="card.label">
          <el-card class="stat-card" :class="`tone-${card.tone}`" shadow="never">
            <div class="stat-label">{{ card.label }}</div>
            <div class="stat-value">{{ card.value }}<span class="stat-suffix">{{ card.suffix }}</span></div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 学科练习量 / 正确率 -->
      <el-card class="block">
        <template #header>各学科练习量与正确率（全班）</template>
        <v-chart
          v-if="subjects.length"
          :option="subjectBarOption"
          autoresize
          style="height: 320px"
        />
        <el-empty v-else description="该班级暂无练习数据" :image-size="80" />
      </el-card>

      <!-- 班级趋势 -->
      <el-card class="block">
        <template #header>
          <div class="block-head">
            <span>班级每日练习趋势</span>
            <span class="muted">最近 {{ periodDays }} 天</span>
          </div>
        </template>
        <v-chart
          v-if="trend && trend.dates.length"
          :option="trendOption"
          autoresize
          style="height: 320px"
        />
        <el-empty v-else description="暂无练习数据" :image-size="80" />
      </el-card>

      <!-- 学生列表（钻取） -->
      <el-card class="block">
        <template #header>
          <div class="block-head">
            <span>学生学习情况</span>
            <span class="muted">点击「查看分析」查看单个学生的详细学习分析</span>
          </div>
        </template>
        <el-empty v-if="!students.length" description="该班级暂无学生" :image-size="80" />
        <el-table v-else :data="students" stripe>
          <el-table-column prop="username" label="用户名" min-width="120" />
          <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
          <el-table-column prop="total_practice" label="累计练习" width="100" align="center" />
          <el-table-column label="正确率" width="110" align="center">
            <template #default="{ row }">
              <el-tag :type="accuracyTagType(row.accuracy)" effect="light">{{ row.accuracy }}%</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="平均用时" width="110" align="center">
            <template #default="{ row }">{{ fmtAvgTime(row.avg_time_seconds) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="110" align="center">
            <template #default="{ row }">
              <el-button size="small" type="primary" @click="emit('view-student', row)">
                查看分析
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.class-analysis {
  max-width: 1200px;
  margin: 0 auto;
}
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}
.page-head h3 {
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
.stat-card .stat-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
</style>
