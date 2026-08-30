<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
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

// ---------- 修改密码 ----------
const pwdFormRef = ref(null)
const pwdLoading = ref(false)
const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm: ''
})
const pwdRules = {
  old_password: [
    { required: true, message: '请输入原始密码', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' }
  ],
  confirm: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_r, value, cb) => {
        if (value !== pwdForm.new_password) cb(new Error('两次密码不一致'))
        else cb()
      },
      trigger: 'blur'
    }
  ]
}

async function onChangePassword() {
  await pwdFormRef.value.validate(async (valid) => {
    if (!valid) return
    pwdLoading.value = true
    try {
      await api.put('/users/change-password', {
        old_password: pwdForm.old_password,
        new_password: pwdForm.new_password,
        confirm_password: pwdForm.confirm
      })
      ElMessage.success('密码修改成功，请妥善保管新密码')
      pwdFormRef.value.resetFields()
    } catch (err) {
      ElMessage.error(err.response?.data?.error || '密码修改失败')
    } finally {
      pwdLoading.value = false
    }
  })
}

// ---------- 删除账号 ----------
const delFormRef = ref(null)
const delLoading = ref(false)
const delForm = reactive({ password: '' })
const delRules = {
  password: [
    { required: true, message: '请输入当前密码确认删除', trigger: 'blur' }
  ]
}

async function onDeleteAccount() {
  await delFormRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      await ElMessageBox.confirm(
        '删除账号将同时清除你的学习记录、错题本与收藏，且无法恢复。确定要删除吗？',
        '删除账号确认',
        {
          type: 'warning',
          confirmButtonText: '确认删除',
          cancelButtonText: '再想想',
          confirmButtonClass: 'el-button--danger'
        }
      )
    } catch {
      return // 用户取消了确认框
    }

    delLoading.value = true
    try {
      await api.delete('/users/me', { data: { password: delForm.password } })
      auth.logout()
      ElMessage.success('账号已删除')
      router.push('/')
    } catch (err) {
      ElMessage.error(err.response?.data?.error || '删除账号失败')
      delLoading.value = false
    }
  })
}
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
        <el-descriptions-item label="最后登录">{{ profile.last_login || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 账号设置：修改密码 / 删除账号 -->
    <el-card class="info-card">
      <template #header>账号设置</template>

      <h4 class="setting-title">修改密码</h4>
      <el-form
        ref="pwdFormRef"
        :model="pwdForm"
        :rules="pwdRules"
        label-position="top"
        @submit.prevent="onChangePassword"
      >
        <el-form-item label="原始密码" prop="old_password">
          <el-input
            v-model="pwdForm.old_password"
            type="password"
            show-password
            placeholder="请输入当前密码"
          />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="pwdForm.new_password"
            type="password"
            show-password
            placeholder="至少 6 位"
          />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm">
          <el-input
            v-model="pwdForm.confirm"
            type="password"
            show-password
            placeholder="再次输入新密码"
            @keyup.enter="onChangePassword"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="pwdLoading" @click="onChangePassword">
            修改密码
          </el-button>
        </el-form-item>
      </el-form>

      <el-divider />

      <h4 class="setting-title danger">删除账号</h4>
      <p class="setting-desc">删除后账号与学习数据无法恢复，需输入当前密码确认。</p>
      <el-form
        ref="delFormRef"
        :model="delForm"
        :rules="delRules"
        label-position="top"
        @submit.prevent="onDeleteAccount"
      >
        <el-form-item label="当前密码" prop="password">
          <el-input
            v-model="delForm.password"
            type="password"
            show-password
            placeholder="输入当前密码以确认删除"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="danger" :loading="delLoading" @click="onDeleteAccount">
            删除账号
          </el-button>
        </el-form-item>
      </el-form>
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
.setting-title {
  margin: 0 0 12px;
}
.setting-title.danger {
  color: var(--el-color-danger);
}
.setting-desc {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
</style>
