<script setup>
/**
 * 发布/调整考试时间对话框：
 *  - datetimerange 选择开始/结束时间，清空 = 不限时（随时可考）
 *  - mode='publish'：POST /exam/papers/:id/publish（携带时间窗）
 *  - mode='window' ：PUT  /exam/papers/:id     （修改已发布试卷的时间窗）
 * 时间统一 toISOString() 提交，后端转 naive UTC 存储
 */
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  paperId: { type: Number, required: true },
  mode: { type: String, default: 'publish' },        // 'publish' | 'window'
  initialStart: { type: String, default: null },
  initialEnd: { type: String, default: null }
})
const emit = defineEmits(['update:modelValue', 'done'])

const range = ref(null)     // [Date, Date] | null
const submitting = ref(false)

// 打开时回填已有时间窗（编辑场景）
watch(() => props.modelValue, (visible) => {
  if (visible) {
    range.value = props.initialStart && props.initialEnd
      ? [new Date(props.initialStart), new Date(props.initialEnd)]
      : null
  }
})

function close() {
  emit('update:modelValue', false)
}

async function submit() {
  const body = {}
  if (range.value && range.value.length === 2) {
    body.start_time = range.value[0].toISOString()
    body.end_time = range.value[1].toISOString()
  }

  submitting.value = true
  try {
    if (props.mode === 'window') {
      // 修改窗口要求两个键都携带（null 表示清除限时）
      await api.put(`/exam/papers/${props.paperId}`, body)
      ElMessage.success('考试时间已更新')
    } else {
      await api.post(`/exam/papers/${props.paperId}/publish`, body)
      ElMessage.success(body.start_time ? '发布成功' : '发布成功，学生现在可以参加此考试')
    }
    close()
    emit('done')
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '操作失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="mode === 'window' ? '调整考试时间' : '发布试卷'"
    width="480px"
    :close-on-click-modal="false"
    @update:model-value="close"
  >
    <el-form label-width="90px">
      <el-form-item label="考试时间">
        <el-date-picker
          v-model="range"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始考试时间"
          end-placeholder="结束考试时间"
          clearable
          style="width: 100%"
        />
      </el-form-item>
      <div class="hint">
        不选择时间表示<strong>不限时</strong>：发布后学生随时可开始，仅受考试时长限制。<br />
        设置时间窗后：开始前不能开考，结束后无法开考，进行中的考试到结束时间自动截止。
      </div>
    </el-form>
    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">
        {{ mode === 'window' ? '保存' : '发布' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.hint {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.7;
  padding-left: 12px;
}
</style>
