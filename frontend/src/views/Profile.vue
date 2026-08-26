<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const profile = ref(null)
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const data = await auth.getCurrentUser()
    profile.value = data
  } catch (err) {
    ElMessage.error('加载用户信息失败')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="profile-page" v-loading="loading">
    <h2>个人中心</h2>
    <el-card v-if="profile" class="info-card">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="用户名">{{ profile.username }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ profile.email }}</el-descriptions-item>
        <el-descriptions-item label="手机">{{ profile.phone || '未设置' }}</el-descriptions-item>
        <el-descriptions-item label="角色">{{ profile.role }}</el-descriptions-item>
        <el-descriptions-item label="注册时间">{{ profile.created_at }}</el-descriptions-item>
        <el-descriptions-item label="最后登录">{{ profile.last_login || '—' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<style scoped>
.profile-page {
  max-width: 720px;
  margin: 0 auto;
}
.info-card {
  margin-top: 12px;
}
</style>
