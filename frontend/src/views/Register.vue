<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

const router = useRouter()
const auth = useAuthStore()

const formRef = ref(null)
const loading = ref(false)
const form = reactive({
  username: '',
  email: '',
  phone: '',
  password: '',
  confirm: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '长度 3-50 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' }
  ],
  confirm: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (_r, value, cb) => {
        if (value !== form.password) cb(new Error('两次密码不一致'))
        else cb()
      },
      trigger: 'blur'
    }
  ]
}

async function onSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    const payload = {
      username: form.username,
      email: form.email,
      password: form.password
    }
    if (form.phone) payload.phone = form.phone

    // authStore.register 期望接口同时返回 token；当前后端 register 只返回 user_id，
    // 因此这里注册成功后再调用登录，兼容两种行为。
    try {
      await api.post('/users/register', payload)
      const loginRes = await auth.login(form.username, form.password)
      if (loginRes.success) {
        ElMessage.success('注册并登录成功')
        router.push('/')
      } else {
        ElMessage.success('注册成功，请登录')
        router.push('/login')
      }
    } catch (err) {
      ElMessage.error(err.response?.data?.error || '注册失败')
    } finally {
      loading.value = false
    }
  })
}
</script>

<template>
  <div class="auth-page">
    <el-card class="auth-card" shadow="always">
      <h2 class="title">注册</h2>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="onSubmit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="3-50 个字符" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="example@mail.com" />
        </el-form-item>
        <el-form-item label="手机号（可选）" prop="phone">
          <el-input v-model="form.phone" placeholder="选填" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm">
          <el-input
            v-model="form.confirm"
            type="password"
            show-password
            placeholder="再次输入密码"
            @keyup.enter="onSubmit"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" class="submit" @click="onSubmit">
            注册
          </el-button>
        </el-form-item>
      </el-form>
      <div class="footer-link">
        已有账号？<router-link to="/login">立即登录</router-link>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.auth-page {
  display: flex;
  justify-content: center;
  padding: 32px 16px;
}
.auth-card {
  width: 100%;
  max-width: 460px;
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
