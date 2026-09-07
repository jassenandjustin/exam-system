<script setup>
/**
 * 学习分析壳组件：
 *  - 学生：只看个人分析（行为与旧版一致）
 *  - 教师/管理员：可切换「个人分析 / 班级学科分析」；
 *    从班级分析钻取学生时切回个人视图并展示该学生的分析
 */
import { computed, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import PersonalAnalysis from './analysis/PersonalAnalysis.vue'
import ClassAnalysis from './analysis/ClassAnalysis.vue'

const auth = useAuthStore()
const ownUserId = computed(() => auth.userId)
const isTeacherOrAdmin = computed(() => ['teacher', 'admin'].includes(auth.userRole))

const view = ref('personal')          // 'personal' | 'class'
const targetUser = ref(null)          // 钻取目标：{ user_id, username }；null = 本人

const viewOptions = [
  { value: 'personal', label: '个人分析' },
  { value: 'class', label: '班级学科分析' }
]

// PersonalAnalysis 的目标：钻取学生或本人
const personalTargetId = computed(() => targetUser.value?.user_id || ownUserId.value)

function onViewStudent(student) {
  targetUser.value = { user_id: student.user_id, username: student.username }
  view.value = 'personal'
}

function backToSelf() {
  targetUser.value = null
}
</script>

<template>
  <div class="analysis-page">
    <div class="page-head">
      <h2>学习分析</h2>
      <el-segmented
        v-if="isTeacherOrAdmin"
        v-model="view"
        :options="viewOptions"
      />
    </div>

    <!-- 钻取横幅 -->
    <el-alert
      v-if="targetUser"
      type="info"
      :closable="false"
      show-icon
      class="drill-banner"
    >
      <template #title>
        <span>正在查看：{{ targetUser.username }} 的学习分析</span>
        <el-button size="small" class="back-btn" @click="backToSelf">返回我的分析</el-button>
      </template>
    </el-alert>

    <PersonalAnalysis
      v-show="view === 'personal'"
      :user-id="personalTargetId"
      :key="personalTargetId"
    />

    <ClassAnalysis
      v-if="isTeacherOrAdmin"
      v-show="view === 'class'"
      @view-student="onViewStudent"
    />
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
.drill-banner {
  margin-bottom: 12px;
}
.back-btn {
  margin-left: 12px;
}
</style>
