<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

// ===== 状态 =====
const subjects = ref([])
const chapters = ref([])
const sections = ref([])
const tags = ref([])
const subjectsLoading = ref(false)
const chaptersLoading = ref(false)
const tagsLoading = ref(false)

const selectedSubjectId = ref(null)
const filteredChapters = computed(() =>
  selectedSubjectId.value
    ? chapters.value.filter(c => c.subject_id === selectedSubjectId.value)
    : chapters.value
)

async function loadAll() {
  subjectsLoading.value = true
  chaptersLoading.value = true
  tagsLoading.value = true
  try {
    const [s, c, sec, t] = await Promise.all([
      api.get('/taxonomy/subjects'),
      api.get('/taxonomy/chapters'),
      api.get('/taxonomy/sections'),
      api.get('/taxonomy/tags')
    ])
    subjects.value = s.data
    chapters.value = c.data
    sections.value = sec.data
    tags.value = t.data
  } catch (err) {
    ElMessage.error('加载失败')
  } finally {
    subjectsLoading.value = false
    chaptersLoading.value = false
    tagsLoading.value = false
  }
}

// ===== 学科 =====
const subjectDlg = reactive({ visible: false, mode: 'create', form: { id: null, name: '', description: '', icon: '' } })
function openCreateSubject() {
  subjectDlg.mode = 'create'
  subjectDlg.form = { id: null, name: '', description: '', icon: '' }
  subjectDlg.visible = true
}
function openEditSubject(row) {
  subjectDlg.mode = 'edit'
  subjectDlg.form = { id: row.id, name: row.name, description: row.description || '', icon: row.icon || '' }
  subjectDlg.visible = true
}
async function submitSubject() {
  if (!subjectDlg.form.name.trim()) {
    ElMessage.error('请填写学科名称')
    return
  }
  try {
    if (subjectDlg.mode === 'create') {
      await api.post('/taxonomy/subjects', subjectDlg.form)
    } else {
      await api.put(`/taxonomy/subjects/${subjectDlg.form.id}`, subjectDlg.form)
    }
    ElMessage.success('已保存')
    subjectDlg.visible = false
    loadAll()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '保存失败')
  }
}
async function deleteSubject(row) {
  try {
    await ElMessageBox.confirm(`删除学科「${row.name}」？包含题目时无法删除。`, '删除学科', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消'
    })
  } catch { return }
  try {
    await api.delete(`/taxonomy/subjects/${row.id}`)
    ElMessage.success('已删除')
    loadAll()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '删除失败')
  }
}

// ===== 章 =====
const chapterDlg = reactive({
  visible: false, mode: 'create',
  form: { id: null, subject_id: null, name: '', description: '', order_num: 0 }
})
function openCreateChapter() {
  if (subjects.value.length === 0) {
    ElMessage.warning('请先创建学科')
    return
  }
  chapterDlg.mode = 'create'
  chapterDlg.form = {
    id: null,
    subject_id: selectedSubjectId.value || subjects.value[0].id,
    name: '', description: '', order_num: 0
  }
  chapterDlg.visible = true
}
function openEditChapter(row) {
  chapterDlg.mode = 'edit'
  chapterDlg.form = {
    id: row.id,
    subject_id: row.subject_id,
    name: row.name,
    description: row.description || '',
    order_num: row.order_num || 0
  }
  chapterDlg.visible = true
}
async function submitChapter() {
  if (!chapterDlg.form.name.trim() || !chapterDlg.form.subject_id) {
    ElMessage.error('请填写学科与章名')
    return
  }
  try {
    if (chapterDlg.mode === 'create') {
      await api.post('/taxonomy/chapters', chapterDlg.form)
    } else {
      // 后端不支持改 subject_id，仅更新其它字段
      await api.put(`/taxonomy/chapters/${chapterDlg.form.id}`, {
        name: chapterDlg.form.name,
        description: chapterDlg.form.description,
        order_num: chapterDlg.form.order_num
      })
    }
    ElMessage.success('已保存')
    chapterDlg.visible = false
    loadAll()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '保存失败')
  }
}
async function deleteChapter(row) {
  try {
    await ElMessageBox.confirm(`删除章「${row.name}」？包含题目或节时无法删除。`, '删除章', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消'
    })
  } catch { return }
  try {
    await api.delete(`/taxonomy/chapters/${row.id}`)
    ElMessage.success('已删除')
    loadAll()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '删除失败')
  }
}
function subjectName(id) {
  return subjects.value.find(s => s.id === id)?.name || '—'
}
function sectionsOf(chapterId) {
  return sections.value.filter(s => s.chapter_id === chapterId)
}

// ===== 节 =====
const sectionDlg = reactive({
  visible: false, mode: 'create',
  form: { id: null, chapter_id: null, name: '', description: '', order_num: 0 }
})
function chapterName(id) {
  return chapters.value.find(c => c.id === id)?.name || '—'
}
function openCreateSection(chapterId) {
  sectionDlg.mode = 'create'
  sectionDlg.form = { id: null, chapter_id: chapterId, name: '', description: '', order_num: 0 }
  sectionDlg.visible = true
}
function openEditSection(row) {
  sectionDlg.mode = 'edit'
  sectionDlg.form = {
    id: row.id,
    chapter_id: row.chapter_id,
    name: row.name,
    description: row.description || '',
    order_num: row.order_num || 0
  }
  sectionDlg.visible = true
}
async function submitSection() {
  if (!sectionDlg.form.name.trim()) {
    ElMessage.error('请填写节名称')
    return
  }
  try {
    if (sectionDlg.mode === 'create') {
      await api.post('/taxonomy/sections', {
        chapter_id: sectionDlg.form.chapter_id,
        name: sectionDlg.form.name,
        description: sectionDlg.form.description,
        order_num: sectionDlg.form.order_num
      })
    } else {
      // 后端不支持改 chapter_id，仅更新其它字段
      await api.put(`/taxonomy/sections/${sectionDlg.form.id}`, {
        name: sectionDlg.form.name,
        description: sectionDlg.form.description,
        order_num: sectionDlg.form.order_num
      })
    }
    ElMessage.success('已保存')
    sectionDlg.visible = false
    loadAll()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '保存失败')
  }
}
async function deleteSection(row) {
  try {
    await ElMessageBox.confirm(`删除节「${row.name}」？包含题目时无法删除。`, '删除节', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消'
    })
  } catch { return }
  try {
    await api.delete(`/taxonomy/sections/${row.id}`)
    ElMessage.success('已删除')
    loadAll()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '删除失败')
  }
}

// ===== 标签 =====
const tagDlg = reactive({ visible: false, mode: 'create', form: { id: null, name: '', category: 'knowledge_point' } })
const TAG_CATEGORIES = [
  { value: 'knowledge_point', label: '知识点' },
  { value: 'difficulty', label: '难度' },
  { value: 'year', label: '年份' },
  { value: 'region', label: '地区' },
  { value: 'other', label: '其他' }
]
const tagCatLabel = (c) => TAG_CATEGORIES.find(x => x.value === c)?.label || c
function openCreateTag() {
  tagDlg.mode = 'create'
  tagDlg.form = { id: null, name: '', category: 'knowledge_point' }
  tagDlg.visible = true
}
function openEditTag(row) {
  tagDlg.mode = 'edit'
  tagDlg.form = { id: row.id, name: row.name, category: row.category }
  tagDlg.visible = true
}
async function submitTag() {
  if (!tagDlg.form.name.trim()) {
    ElMessage.error('请填写标签名')
    return
  }
  try {
    if (tagDlg.mode === 'create') {
      await api.post('/taxonomy/tags', tagDlg.form)
    } else {
      await api.put(`/taxonomy/tags/${tagDlg.form.id}`, tagDlg.form)
    }
    ElMessage.success('已保存')
    tagDlg.visible = false
    loadAll()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '保存失败')
  }
}
async function deleteTag(row) {
  try {
    await ElMessageBox.confirm(`删除标签「${row.name}」？已关联的题目将解除关联。`, '删除标签', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消'
    })
  } catch { return }
  try {
    await api.delete(`/taxonomy/tags/${row.id}`)
    ElMessage.success('已删除')
    loadAll()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '删除失败')
  }
}

onMounted(loadAll)
</script>

<template>
  <div class="subject-manage">
    <el-row :gutter="16">
      <!-- 学科 -->
      <el-col :xs="24" :md="10">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>学科</span>
              <el-button size="small" type="primary" @click="openCreateSubject">新增学科</el-button>
            </div>
          </template>
          <el-table v-loading="subjectsLoading" :data="subjects" stripe @row-click="(row) => selectedSubjectId = row.id" highlight-current-row>
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="name" label="名称" min-width="120" />
            <el-table-column prop="chapter_count" label="章" width="70" align="center" />
            <el-table-column prop="question_count" label="题目" width="70" align="center" />
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button size="small" @click.stop="openEditSubject(row)">编辑</el-button>
                <el-button size="small" type="danger" @click.stop="deleteSubject(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 章（展开行显示节） -->
      <el-col :xs="24" :md="14">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>
                章
                <el-tag v-if="selectedSubjectId" size="small" style="margin-left:8px">{{ subjectName(selectedSubjectId) }}</el-tag>
                <el-button v-if="selectedSubjectId" size="small" link @click="selectedSubjectId = null">清除筛选</el-button>
              </span>
              <el-button size="small" type="primary" @click="openCreateChapter">新增章</el-button>
            </div>
          </template>
          <el-table
            v-loading="chaptersLoading"
            :data="filteredChapters"
            stripe
            row-key="id"
          >
            <el-table-column type="expand">
              <template #default="{ row }">
                <div class="section-expand">
                  <div class="section-expand-header">
                    <span>节（{{ sectionsOf(row.id).length }}）</span>
                    <el-button size="small" type="primary" @click="openCreateSection(row.id)">新增节</el-button>
                  </div>
                  <el-table
                    :data="sectionsOf(row.id)"
                    size="small"
                    :show-header="sectionsOf(row.id).length > 0"
                  >
                    <el-table-column prop="order_num" label="序号" width="80" align="center" />
                    <el-table-column prop="name" label="名称" min-width="120" />
                    <el-table-column prop="question_count" label="题目数" width="90" align="center" />
                    <el-table-column label="操作" width="140">
                      <template #default="scope">
                        <el-button size="small" @click="openEditSection(scope.row)">编辑</el-button>
                        <el-button size="small" type="danger" @click="deleteSection(scope.row)">删除</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                  <el-empty
                    v-if="sectionsOf(row.id).length === 0"
                    description="该章下暂无节，题目可直接挂在章上"
                    :image-size="40"
                  />
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column label="所属学科" width="120">
              <template #default="{ row }">{{ subjectName(row.subject_id) }}</template>
            </el-table-column>
            <el-table-column prop="name" label="名称" min-width="160" />
            <el-table-column prop="order_num" label="序号" width="70" align="center" />
            <el-table-column label="节" width="60" align="center">
              <template #default="{ row }">{{ sectionsOf(row.id).length }}</template>
            </el-table-column>
            <el-table-column prop="question_count" label="题目数" width="80" align="center" />
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button size="small" @click="openEditChapter(row)">编辑</el-button>
                <el-button size="small" type="danger" @click="deleteChapter(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 标签 -->
    <el-card style="margin-top:16px">
      <template #header>
        <div class="card-header">
          <span>标签</span>
          <el-button size="small" type="primary" @click="openCreateTag">新增标签</el-button>
        </div>
      </template>
      <el-table v-loading="tagsLoading" :data="tags" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column label="分类" width="120">
          <template #default="{ row }">
            <el-tag>{{ tagCatLabel(row.category) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="usage_count" label="引用次数" width="100" align="center" />
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" @click="openEditTag(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteTag(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 学科对话框 -->
    <el-dialog v-model="subjectDlg.visible" :title="subjectDlg.mode === 'create' ? '新增学科' : '编辑学科'" width="480px">
      <el-form label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="subjectDlg.form.name" placeholder="如：高等数学" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="subjectDlg.form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="subjectDlg.form.icon" placeholder="选填，icon 名称或 URL" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="subjectDlg.visible = false">取消</el-button>
        <el-button type="primary" @click="submitSubject">保存</el-button>
      </template>
    </el-dialog>

    <!-- 章对话框 -->
    <el-dialog v-model="chapterDlg.visible" :title="chapterDlg.mode === 'create' ? '新增章' : '编辑章'" width="520px">
      <el-form label-width="80px">
        <el-form-item label="所属学科" required>
          <el-select v-model="chapterDlg.form.subject_id" :disabled="chapterDlg.mode === 'edit'" style="width:100%">
            <el-option v-for="s in subjects" :key="s.id" :value="s.id" :label="s.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="chapterDlg.form.name" placeholder="如：导数与微分" />
        </el-form-item>
        <el-form-item label="序号">
          <el-input-number v-model="chapterDlg.form.order_num" :min="0" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="chapterDlg.form.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="chapterDlg.visible = false">取消</el-button>
        <el-button type="primary" @click="submitChapter">保存</el-button>
      </template>
    </el-dialog>

    <!-- 节对话框 -->
    <el-dialog v-model="sectionDlg.visible" :title="sectionDlg.mode === 'create' ? '新增节' : '编辑节'" width="480px">
      <el-form label-width="80px">
        <el-form-item label="所属章">
          <el-input :model-value="chapterName(sectionDlg.form.chapter_id)" disabled />
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="sectionDlg.form.name" placeholder="如：第一节" />
        </el-form-item>
        <el-form-item label="序号">
          <el-input-number v-model="sectionDlg.form.order_num" :min="0" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="sectionDlg.form.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="sectionDlg.visible = false">取消</el-button>
        <el-button type="primary" @click="submitSection">保存</el-button>
      </template>
    </el-dialog>

    <!-- 标签对话框 -->
    <el-dialog v-model="tagDlg.visible" :title="tagDlg.mode === 'create' ? '新增标签' : '编辑标签'" width="420px">
      <el-form label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="tagDlg.form.name" placeholder="如：求导" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="tagDlg.form.category" style="width:100%">
            <el-option v-for="c in TAG_CATEGORIES" :key="c.value" :value="c.value" :label="c.label" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="tagDlg.visible = false">取消</el-button>
        <el-button type="primary" @click="submitTag">保存</el-button>
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
.section-expand {
  padding: 8px 16px 12px 48px;
}
.section-expand-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
</style>
