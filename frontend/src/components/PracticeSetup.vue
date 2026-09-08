<script setup>
/**
 * 练习开始前的配置面板：选学科、可选章/节、可选题量。
 *
 * Props:
 *  - showChapter:  是否显示章/节选择（顺序练习/章节练习需要，随机练习不需要）
 *  - chapterRequired: 章是否必填（章节练习需要）
 *  - showCount:    是否显示题量选择（随机练习需要）
 *  - defaultCount: 默认题量
 *
 * Emits:
 *  - start:  { subject_id, chapter_id, section_id, count }
 */
import { onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const props = defineProps({
  showChapter: { type: Boolean, default: true },
  chapterRequired: { type: Boolean, default: false },
  showCount: { type: Boolean, default: false },
  defaultCount: { type: Number, default: 10 }
})
const emit = defineEmits(['start'])

const subjects = ref([])
const chapters = ref([])
const sections = ref([])
const subjectId = ref(null)
const chapterId = ref(null)
const sectionId = ref(null)
const count = ref(props.defaultCount)
const loading = ref(false)

async function loadMeta() {
  try {
    const [s, c, sec] = await Promise.all([
      api.get('/taxonomy/subjects'),
      api.get('/taxonomy/chapters'),
      api.get('/taxonomy/sections')
    ])
    subjects.value = s.data
    chapters.value = c.data
    sections.value = sec.data
  } catch (err) {
    ElMessage.error('加载学科/章/节失败')
  }
}

const filteredChapters = ref([])
const filteredSections = ref([])
watch(
  [subjectId, chapters, sections],
  () => {
    filteredChapters.value = subjectId.value
      ? chapters.value.filter(c => c.subject_id === subjectId.value)
      : []
    // 切换学科时清掉旧的章/节
    if (chapterId.value && !filteredChapters.value.some(c => c.id === chapterId.value)) {
      chapterId.value = null
      sectionId.value = null
    }
    filteredSections.value = chapterId.value
      ? sections.value.filter(s => s.chapter_id === chapterId.value)
      : []
  },
  { immediate: true }
)

// 切换章时清掉旧的节
watch(chapterId, () => {
  if (sectionId.value && !filteredSections.value.some(s => s.id === sectionId.value)) {
    sectionId.value = null
  }
})

function start() {
  if (!subjectId.value) {
    ElMessage.warning('请选择学科')
    return
  }
  if (props.chapterRequired && !chapterId.value) {
    ElMessage.warning('请选择章')
    return
  }
  emit('start', {
    subject_id: subjectId.value,
    chapter_id: chapterId.value || null,
    section_id: sectionId.value || null,
    count: count.value
  })
}

onMounted(loadMeta)
</script>

<template>
  <el-card class="setup-card" v-loading="loading">
    <el-form label-width="80px" @submit.prevent>
      <el-form-item label="学科">
        <el-select v-model="subjectId" placeholder="请选择学科" style="width:280px">
          <el-option v-for="s in subjects" :key="s.id" :value="s.id" :label="s.name" />
        </el-select>
      </el-form-item>

      <el-form-item v-if="showChapter" label="章">
        <el-select
          v-model="chapterId"
          :placeholder="chapterRequired ? '请选择章' : '不限章'"
          clearable
          :disabled="!subjectId"
          style="width:280px"
        >
          <el-option v-for="c in filteredChapters" :key="c.id" :value="c.id" :label="c.name" />
        </el-select>
      </el-form-item>

      <el-form-item v-if="showChapter" label="节">
        <el-select
          v-model="sectionId"
          placeholder="不限节"
          clearable
          :disabled="!chapterId"
          style="width:280px"
        >
          <el-option v-for="s in filteredSections" :key="s.id" :value="s.id" :label="s.name" />
        </el-select>
      </el-form-item>

      <el-form-item v-if="showCount" label="题量">
        <el-input-number v-model="count" :min="5" :max="50" :step="5" />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="start">开始练习</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<style scoped>
.setup-card {
  max-width: 520px;
  margin: 16px auto;
}
</style>
