<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

// ===== 状态 =====
const classes = ref([])
const subjects = ref([])
const loading = ref(false)

async function loadAll() {
  loading.value = true
  try {
    const [c, s] = await Promise.all([
      api.get('/classes'),
      api.get('/taxonomy/subjects')
    ])
    classes.value = c.data
    subjects.value = s.data
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '加载失败')
  } finally {
    loading.value = false
  }
}

// ===== 班级 CRUD =====
const classDlg = reactive({
  visible: false,
  mode: 'create',
  form: { id: null, name: '', description: '', subject_ids: [] }
})

function openCreate() {
  classDlg.mode = 'create'
  classDlg.form = { id: null, name: '', description: '', subject_ids: [] }
  classDlg.visible = true
}

function openEdit(row) {
  classDlg.mode = 'edit'
  classDlg.form = {
    id: row.id,
    name: row.name,
    description: row.description || '',
    subject_ids: [...(row.subject_ids || [])]
  }
  classDlg.visible = true
}

async function submitClass() {
  if (!classDlg.form.name.trim()) {
    ElMessage.error('请填写班级名称')
    return
  }
  if (!classDlg.form.subject_ids.length) {
    ElMessage.error('请至少选择一个学科（班级可刷题的范围）')
    return
  }
  try {
    if (classDlg.mode === 'create') {
      await api.post('/classes', classDlg.form)
    } else {
      await api.put(`/classes/${classDlg.form.id}`, classDlg.form)
    }
    ElMessage.success('已保存')
    classDlg.visible = false
    loadAll()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '保存失败')
  }
}

async function deleteClass(row) {
  try {
    await ElMessageBox.confirm(
      `删除班级「${row.name}」？该班学生将失去班级归属（学生未入班将无法刷题和考试），已产生的学习记录不受影响。`,
      '删除班级',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await api.delete(`/classes/${row.id}`)
    ElMessage.success('已删除')
    loadAll()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '删除失败')
  }
}

function formatDate(s) {
  if (!s) return '—'
  try {
    return new Date(s).toLocaleString()
  } catch {
    return s
  }
}

onMounted(loadAll)
</script>

<template>
  <div class="class-manage">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>班级管理</span>
          <el-button size="small" type="primary" @click="openCreate">新增班级</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="classes" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="班级名称" min-width="120" />
        <el-table-column prop="description" label="描述" min-width="140">
          <template #default="{ row }">{{ row.description || '—' }}</template>
        </el-table-column>
        <el-table-column label="可刷题学科" min-width="200">
          <template #default="{ row }">
            <el-tag
              v-for="name in (row.subject_names || [])"
              :key="name"
              size="small"
              style="margin-right: 4px"
            >
              {{ name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="student_count" label="学生数" width="80" align="center" />
        <el-table-column prop="teacher_count" label="教师数" width="80" align="center" />
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteClass(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 班级对话框 -->
    <el-dialog
      v-model="classDlg.visible"
      :title="classDlg.mode === 'create' ? '新增班级' : '编辑班级'"
      width="520px"
    >
      <el-form label-width="90px">
        <el-form-item label="班级名称" required>
          <el-input v-model="classDlg.form.name" placeholder="如：软件工程 2301 班" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="classDlg.form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="可刷题学科" required>
          <el-select
            v-model="classDlg.form.subject_ids"
            multiple
            placeholder="选择该班级可以刷题的学科范围"
            style="width: 100%"
          >
            <el-option v-for="s in subjects" :key="s.id" :value="s.id" :label="s.name" />
          </el-select>
          <div class="subject-tip">该班学生只能练习 / 考试所选学科范围内的内容</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="classDlg.visible = false">取消</el-button>
        <el-button type="primary" @click="submitClass">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}
.subject-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
  line-height: 1.4;
}
</style>
