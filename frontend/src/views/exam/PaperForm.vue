<script setup>
/**
 * 试卷创建/编辑表单：
 *  - 基本信息（名称、描述、类型、时长、及格分）
 *  - 支持新建和编辑模式
 */
import { onMounted, reactive, ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'

const router = useRouter()
const route = useRoute()
const loading = ref(false)

const isEdit = computed(() => !!route.params.id)
const pageTitle = computed(() => isEdit.value ? '编辑试卷' : '创建试卷')

const EXAM_TYPES = [
  { value: 'quick', label: '快速练习', duration: 15, desc: '10 题 / 15 分钟，热身练习' },
  { value: 'standard', label: '标准考试', duration: 45, desc: '30 题 / 45 分钟，常规模考' },
  { value: 'comprehensive', label: '综合考试', duration: 90, desc: '50 题 / 90 分钟，全面测验' },
  { value: 'custom', label: '自定义考试', duration: 60, desc: '自由设置考试参数' },
]

const form = reactive({
  name: '',
  description: '',
  exam_type: 'custom',
  duration_minutes: 60,
  passing_score: 60,
})

function onTypeChange(val) {
  const t = EXAM_TYPES.find(t => t.value === val)
  if (t && val !== 'custom') {
    form.duration_minutes = t.duration
  }
}

async function loadPaper(id) {
  loading.value = true
  try {
    const { data } = await api.get(`/exam/papers/${id}`)
    form.name = data.name
    form.description = data.description || ''
    form.exam_type = data.exam_type
    form.duration_minutes = data.duration_minutes
    form.passing_score = data.passing_score
  } catch {
    ElMessage.error('加载试卷失败')
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入试卷名称')
    return
  }
  loading.value = true
  try {
    if (isEdit.value) {
      await api.put(`/exam/papers/${route.params.id}`, form)
      ElMessage.success('更新成功')
    } else {
      const { data } = await api.post('/exam/papers', form)
      ElMessage.success('创建成功')
      router.replace(`/exam/paper/${data.id}/manage`)
      return
    }
    router.push('/exam/teacher')
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '操作失败')
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push('/exam/teacher')
}

onMounted(() => {
  if (isEdit.value) {
    loadPaper(route.params.id)
  }
})
</script>

<template>
  <div class="paper-form" v-loading="loading">
    <div class="page-header">
      <el-button text @click="goBack"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
      <h2>{{ pageTitle }}</h2>
    </div>

    <el-card>
      <el-form :model="form" label-width="100px" style="max-width: 600px;">
        <el-form-item label="试卷名称" required>
          <el-input v-model="form.name" placeholder="请输入试卷名称" maxlength="100" show-word-limit />
        </el-form-item>

        <el-form-item label="考试类型">
          <el-radio-group v-model="form.exam_type" @change="onTypeChange">
            <el-radio-button v-for="t in EXAM_TYPES" :key="t.value" :value="t.value">
              {{ t.label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="考试描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="可选，描述此考试"
          />
        </el-form-item>

        <el-form-item label="考试时长">
          <el-input-number v-model="form.duration_minutes" :min="1" :max="300" />
          <span class="muted"> 分钟</span>
        </el-form-item>

        <el-form-item label="及格分数">
          <el-input-number v-model="form.passing_score" :min="0" :max="999" :precision="1" />
          <span class="muted"> 分</span>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSubmit">
            {{ isEdit ? '保存修改' : '创建并继续' }}
          </el-button>
          <el-button @click="goBack">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.paper-form {
  max-width: 800px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.muted {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-left: 8px;
}
</style>
