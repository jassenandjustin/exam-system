<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const formRef = ref(null)
const loading = ref(false)
const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function onSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    const res = await auth.login(form.username, form.password)
    loading.value = false
    if (res.success) {
      ElMessage.success('登录成功')
      router.push('/')
    } else {
      ElMessage.error(res.error || '登录失败')
    }
  })
}
</script>

<template>
  <div class="auth-page">
    <el-card class="auth-card" shadow="always">
      <h2 class="title">登录</h2>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="onSubmit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            :prefix-icon="'User'"
            autocomplete="username"
          />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
            :prefix-icon="'Lock'"
            autocomplete="current-password"
            @keyup.enter="onSubmit"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" class="submit" @click="onSubmit">
            登录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="footer-link">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.auth-page {
  display: flex;
  justify-content: center;
  padding: 48px 16px;
}
.auth-card {
  width: 100%;
  max-width: 420px;
}
.title {
  text-align: center;
  margin: 0 0 16px;
}
.submit {
  width: 100%;
}
.footer-link {
  text-align: center;
  margin-top: 8px;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}
.footer-link a {
  color: var(--el-color-primary);
}
</style>
