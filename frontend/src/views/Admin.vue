<script setup>
import { ref, defineAsyncComponent } from 'vue'

const tab = ref('users')

const UserManage = defineAsyncComponent(() => import('./admin/UserManage.vue'))
const QuestionManage = defineAsyncComponent(() => import('./admin/QuestionManage.vue'))
const SubjectManage = defineAsyncComponent(() => import('./admin/SubjectManage.vue'))
const ClassManage = defineAsyncComponent(() => import('./admin/ClassManage.vue'))
</script>

<template>
  <div class="admin-page">
    <h2>管理后台</h2>
    <el-tabs v-model="tab" type="border-card" class="admin-tabs">
      <el-tab-pane name="users" label="用户管理">
        <UserManage v-if="tab === 'users'" />
      </el-tab-pane>
      <el-tab-pane name="questions" label="题库管理">
        <QuestionManage v-if="tab === 'questions'" />
      </el-tab-pane>
      <el-tab-pane name="taxonomy" label="学科 / 章节 / 标签">
        <SubjectManage v-if="tab === 'taxonomy'" />
      </el-tab-pane>
      <el-tab-pane name="classes" label="班级管理">
        <ClassManage v-if="tab === 'classes'" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.admin-page {
  max-width: 1280px;
  margin: 0 auto;
}
.admin-tabs {
  margin-top: 12px;
}
</style>
