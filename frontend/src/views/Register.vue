<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'

const router = useRouter()

const formRef = ref(null)
const loading = ref(false)
const classes = ref([])
const form = reactive({
  username: '',
  email: '',
  phone: '',
  password: '',
  confirm: '',
  role: 'student',
  classId: null,        // 学生：单选
  teacherClassIds: []   // 教师：多选
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
  ],
  classId: [
    { required: true, message: '请选择班级', trigger: 'change' }
  ],
  teacherClassIds: [
    {
      validator: (_r, value, cb) => {
        if (form.role === 'teacher' && (!value || value.length === 0) && classes.value.length > 0) {
          cb(new Error('请选择至少一个任教班级'))
        } else {
          cb()
        }
      },
      trigger: 'change'
    }
  ]
}

onMounted(async () => {
  try {
    const { data } = await api.get('/classes')
    classes.value = data
  } catch {
    // 拉取失败不阻塞注册页，提交时再提示
  }
})

async function onSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    if (classes.value.length === 0) {
      ElMessage.error('暂无班级，请联系管理员先创建班级')
      return
    }
    if (form.role === 'student' && !form.classId) {
      ElMessage.error('请选择班级')
      return
    }
    if (form.role === 'teacher' && form.teacherClassIds.length === 0) {
      ElMessage.error('请选择任教班级')
      return
    }
    loading.value = true
    const payload = {
      username: form.username,
      email: form.email,
      password: form.password,
      role: form.role,
      class_ids: form.role === 'student' ? [form.classId] : [...form.teacherClassIds]
    }
    if (form.phone) payload.phone = form.phone

    try {
      await api.post('/users/register', payload)
      // 注册后需要管理员审核通过才能登录，不再自动登录
      ElMessage.success('注册成功，请等待管理员审核通过后再登录')
      router.push('/login')
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
        <el-form-item label="注册角色" prop="role">
          <el-radio-group v-model="form.role">
            <el-radio value="student">学生</el-radio>
            <el-radio value="teacher">教师</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="3-50 个字符" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="example@mail.com" />
        </el-form-item>
        <el-form-item label="手机号（可选）" prop="phone">
          <el-input v-model="form.phone" placeholder="选填" />
        </el-form-item>
        <el-form-item v-if="form.role === 'student'" label="班级" prop="classId">
          <el-select v-model="form.classId" placeholder="选择要加入的班级" style="width: 100%">
            <el-option v-for="c in classes" :key="c.id" :value="c.id" :label="c.name" />
          </el-select>
          <div v-if="classes.length === 0" class="class-tip">暂无班级，请联系管理员先创建班级</div>
        </el-form-item>
        <el-form-item v-else label="任教班级（可多选）" prop="teacherClassIds">
          <el-select
            v-model="form.teacherClassIds"
            multiple
            placeholder="选择任教的班级"
            style="width: 100%"
          >
            <el-option v-for="c in classes" :key="c.id" :value="c.id" :label="c.name" />
          </el-select>
          <div v-if="classes.length === 0" class="class-tip">暂无班级，请联系管理员先创建班级</div>
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
.class-tip {
  font-size: 12px;
  color: var(--el-color-warning);
  margin-top: 4px;
  line-height: 1.4;
}
</style>
