<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

const auth = useAuthStore()

const overview = ref(null)
const overviewLoading = ref(false)

const users = ref([])
const total = ref(0)
const tableLoading = ref(false)
const query = reactive({
  page: 1,
  per_page: 10,
  search: '',
  role: ''
})

const roleOptions = [
  { value: '', label: '全部' },
  { value: 'student', label: '学生' },
  { value: 'teacher', label: '教师' },
  { value: 'admin', label: '管理员' }
]

const roleTagType = {
  admin: 'danger',
  teacher: 'warning',
  student: 'info'
}

async function loadOverview() {
  overviewLoading.value = true
  try {
    const { data } = await api.get('/users/admin/overview')
    overview.value = data
  } catch (err) {
    ElMessage.error(err.response?.data?.error || `加载概览失败: ${err.message}`)
  } finally {
    overviewLoading.value = false
  }
}

async function loadUsers() {
  tableLoading.value = true
  try {
    const params = { page: query.page, per_page: query.per_page }
    if (query.search) params.search = query.search
    if (query.role) params.role = query.role
    const { data } = await api.get('/users/admin/users', { params })
    users.value = data.users
    total.value = data.total
  } catch (err) {
    ElMessage.error(err.response?.data?.error || `加载用户列表失败: ${err.message}`)
  } finally {
    tableLoading.value = false
  }
}

function onSearch() {
  query.page = 1
  loadUsers()
}

function onPageChange(p) {
  query.page = p
  loadUsers()
}

async function changeRole(row, newRole) {
  if (newRole === row.role) return
  try {
    await api.put(`/users/admin/users/${row.id}/role`, { role: newRole })
    row.role = newRole
    ElMessage.success(`已将 ${row.username} 角色改为 ${newRole}`)
    loadOverview()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '修改角色失败')
    loadUsers()
  }
}

async function deleteUser(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户 "${row.username}" 吗？此操作不可恢复。`,
      '删除用户',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await api.delete(`/users/admin/users/${row.id}`)
    ElMessage.success('已删除')
    loadUsers()
    loadOverview()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '删除失败')
  }
}

function formatDate(s) {
  if (!s) return '—'
  try {
    return new Date(s).toLocaleString()
  } catch {
    return s
  }
}

onMounted(() => {
  loadOverview()
  loadUsers()
})
</script>

<template>
  <div>
    <el-row :gutter="16" class="overview" v-loading="overviewLoading">
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover">
          <div class="metric">
            <div class="label">用户总数</div>
            <div class="value">{{ overview?.users?.total ?? '—' }}</div>
            <div class="sub">本周新增 {{ overview?.users?.new_this_week ?? 0 }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover">
          <div class="metric">
            <div class="label">题库题目</div>
            <div class="value">{{ overview?.questions?.total ?? '—' }}</div>
            <div class="sub">{{ overview?.questions?.subjects ?? 0 }} 个学科</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover">
          <div class="metric">
            <div class="label">练习次数</div>
            <div class="value">{{ overview?.activity?.total_practice ?? '—' }}</div>
            <div class="sub">本周 {{ overview?.activity?.practice_this_week ?? 0 }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover">
          <div class="metric">
            <div class="label">考试次数</div>
            <div class="value">{{ overview?.activity?.total_exams ?? '—' }}</div>
            <div class="sub">
              管 {{ overview?.users?.by_role?.admin ?? 0 }} ·
              师 {{ overview?.users?.by_role?.teacher ?? 0 }} ·
              生 {{ overview?.users?.by_role?.student ?? 0 }}
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card>
      <template #header>
        <div class="section-header">
          <span>用户管理</span>
          <div class="filters">
            <el-input
              v-model="query.search"
              placeholder="搜索用户名 / 邮箱"
              clearable
              style="width: 220px"
              @keyup.enter="onSearch"
              @clear="onSearch"
            />
            <el-select v-model="query.role" placeholder="角色" style="width: 120px" @change="onSearch">
              <el-option v-for="o in roleOptions" :key="o.value" :value="o.value" :label="o.label" />
            </el-select>
            <el-button type="primary" @click="onSearch">查询</el-button>
            <el-button @click="loadUsers">刷新</el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="tableLoading" :data="users" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="phone" label="手机" width="130">
          <template #default="{ row }">{{ row.phone || '—' }}</template>
        </el-table-column>
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="roleTagType[row.role]" effect="light">{{ row.role }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="注册时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="最近登录" width="180">
          <template #default="{ row }">{{ formatDate(row.last_login) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-dropdown
              :disabled="row.id === auth.userId"
              trigger="click"
              @command="(c) => changeRole(row, c)"
            >
              <el-button size="small" :disabled="row.id === auth.userId">
                修改角色<el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="student">学生</el-dropdown-item>
                  <el-dropdown-item command="teacher">教师</el-dropdown-item>
                  <el-dropdown-item command="admin">管理员</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button
              size="small"
              type="danger"
              :disabled="row.id === auth.userId"
              @click="deleteUser(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pager"
        background
        layout="total, prev, pager, next"
        :total="total"
        :page-size="query.per_page"
        :current-page="query.page"
        @current-change="onPageChange"
      />
    </el-card>
  </div>
</template>

<style scoped>
.overview {
  margin-bottom: 16px;
}
.metric {
  text-align: center;
}
.metric .label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.metric .value {
  font-size: 28px;
  font-weight: 600;
  margin: 4px 0;
  color: var(--el-color-primary);
}
.metric .sub {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}
.filters {
  display: flex;
  gap: 8px;
}
.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
