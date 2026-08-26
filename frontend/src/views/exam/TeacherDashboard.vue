<script setup>
/**
 * 教师端试卷管理仪表盘：
 *  - 试卷列表（卡片形式）
 *  - 创建 / 编辑 / 管理 / 删除 / 发布 操作
 */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

const router = useRouter()
const papers = ref([])
const loading = ref(false)

const EXAM_TYPE_MAP = {
  quick: { label: '快速练习', color: '#67c23a' },
  standard: { label: '标准考试', color: '#409eff' },
  comprehensive: { label: '综合考试', color: '#e6a23c' },
  custom: { label: '自定义考试', color: '#909399' },
}

async function loadPapers() {
  loading.value = true
  try {
    const { data } = await api.get('/exam/papers')
    papers.value = data
  } catch {
    ElMessage.error('加载试卷列表失败')
  } finally {
    loading.value = false
  }
}

function createPaper() {
  router.push('/exam/paper/create')
}

function editPaper(id) {
  router.push(`/exam/paper/${id}/edit`)
}

function managePaper(id) {
  router.push(`/exam/paper/${id}/manage`)
}

async function deletePaper(id) {
  try {
    await ElMessageBox.confirm('确定要删除此试卷吗？', '删除确认', { type: 'warning' })
    await api.delete(`/exam/papers/${id}`)
    ElMessage.success('删除成功')
    loadPapers()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err.response?.data?.error || '删除失败')
    }
  }
}

async function togglePublish(paper) {
  try {
    if (paper.is_published) {
      await api.post(`/exam/papers/${paper.id}/unpublish`)
      ElMessage.success('已取消发布')
    } else {
      await api.post(`/exam/papers/${paper.id}/publish`)
      ElMessage.success('发布成功，学生现在可以参加此考试')
    }
    loadPapers()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '操作失败')
  }
}

function fmtDate(s) {
  if (!s) return '—'
  return new Date(s).toLocaleString()
}

onMounted(loadPapers)
</script>

<template>
  <div class="teacher-dashboard" v-loading="loading">
    <div class="page-header">
      <h2>试卷管理</h2>
      <el-button type="primary" @click="createPaper">创建试卷</el-button>
    </div>

    <el-empty v-if="!loading && papers.length === 0" description="还没有创建试卷，点击上方按钮创建" />

    <el-row :gutter="16">
      <el-col v-for="p in papers" :key="p.id" :xs="24" :sm="12" :md="8" :lg="6">
        <el-card class="paper-card" shadow="hover">
          <div class="card-header">
            <span class="paper-name">{{ p.name }}</span>
            <el-tag
              :color="EXAM_TYPE_MAP[p.exam_type]?.color"
              effect="dark"
              size="small"
              class="type-tag"
            >
              {{ EXAM_TYPE_MAP[p.exam_type]?.label || p.exam_type }}
            </el-tag>
          </div>
          <p class="paper-desc">{{ p.description || '暂无描述' }}</p>
          <div class="card-meta">
            <span><el-icon><Clock /></el-icon> {{ p.duration_minutes }} 分钟</span>
            <span><el-icon><Document /></el-icon> {{ p.total_questions || p.question_count || 0 }} 题</span>
            <span><el-icon><Trophy /></el-icon> {{ p.total_score || 0 }} 分</span>
          </div>
          <div class="card-status">
            <el-tag v-if="p.is_published" type="success" size="small">已发布</el-tag>
            <el-tag v-else type="info" size="small">未发布</el-tag>
            <span class="rule-count">{{ p.rule_count }} 条规则</span>
          </div>
          <div class="card-actions">
            <el-button size="small" @click="editPaper(p.id)">编辑</el-button>
            <el-button size="small" type="primary" @click="managePaper(p.id)">管理题目</el-button>
            <el-button
              size="small"
              :type="p.is_published ? 'warning' : 'success'"
              @click="togglePublish(p)"
            >
              {{ p.is_published ? '取消发布' : '发布' }}
            </el-button>
            <el-button
              v-if="!p.is_published"
              size="small"
              type="danger"
              @click="deletePaper(p.id)"
            >删除</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.teacher-dashboard {
  max-width: 1280px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.paper-card {
  margin-bottom: 16px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}
.paper-name {
  font-size: 16px;
  font-weight: 600;
  flex: 1;
  margin-right: 8px;
}
.type-tag {
  flex-shrink: 0;
}
.paper-desc {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin-bottom: 12px;
  min-height: 20px;
}
.card-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  margin-bottom: 8px;
}
.card-meta span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.card-status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.rule-count {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
</style>
