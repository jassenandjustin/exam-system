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
  role: '',
  status: ''
})

const classes = ref([])

const roleOptions = [
  { value: '', label: '全部' },
  { value: 'student', label: '学生' },
  { value: 'teacher', label: '教师' },
  { value: 'admin', label: '管理员' }
]

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'pending', label: '待审核' },
  { value: 'approved', label: '已通过' },
  { value: 'rejected', label: '已拒绝' }
]

const statusTagType = {
  pending: 'warning',
  approved: 'success',
  rejected: 'danger'
}
const statusLabel = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已拒绝'
}

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
    if (query.status) params.status = query.status
    const { data } = await api.get('/users/admin/users', { params })
    users.value = data.users
    total.value = data.total
  } catch (err) {
    ElMessage.error(err.response?.data?.error || `加载用户列表失败: ${err.message}`)
  } finally {
    tableLoading.value = false
  }
}

async function loadClasses() {
  try {
    const { data } = await api.get('/classes')
    classes.value = data
  } catch {
    // 班级加载失败不阻塞用户列表，分配班级时再提示
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

// ===== 注册审核 =====
async function setStatus(row, status) {
  if (status === row.status) return
  const actionLabel = {
    approved: '通过',
    rejected: '拒绝',
    pending: '重置为待审核'
  }[status]
  if (status === 'rejected') {
    try {
      await ElMessageBox.confirm(
        `拒绝用户 "${row.username}" 的注册？该账号将无法登录。`,
        '拒绝注册',
        { type: 'warning', confirmButtonText: '拒绝', cancelButtonText: '取消' }
      )
    } catch {
      return
    }
  }
  try {
    await api.put(`/users/admin/users/${row.id}/status`, { status })
    ElMessage.success(`已将 ${row.username} ${actionLabel}`)
    loadUsers()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '操作失败')
  }
}

// ===== 重置密码 =====
async function resetPassword(row) {
  let value
  try {
    const res = await ElMessageBox.prompt(
      `为用户 "${row.username}" 设置新密码（至少 6 位）：`,
      '重置密码',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputType: 'password',
        inputValidator: (v) => (v && v.length >= 6) || '密码至少 6 位'
      }
    )
    value = res.value
  } catch {
    return
  }
  try {
    await api.put(`/users/admin/users/${row.id}/reset-password`, { new_password: value })
    ElMessage.success(`已重置 ${row.username} 的密码`)
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '重置失败')
  }
}

// ===== 分配班级 =====
const assignDlg = reactive({
  visible: false,
  user: null,
  classIds: []
})

function openAssign(row) {
  assignDlg.user = row
  assignDlg.classIds = (row.classes || []).map(c => c.id)
  assignDlg.visible = true
}

async function submitAssign() {
  const row = assignDlg.user
  if (!row) return
  if (row.role === 'student' && assignDlg.classIds.length > 1) {
    ElMessage.error('学生只能属于一个班级')
    return
  }
  try {
    await api.put(`/users/admin/users/${row.id}/class`, { class_ids: assignDlg.classIds })
    ElMessage.success('班级已更新')
    assignDlg.visible = false
    loadUsers()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '分配班级失败')
  }
}

function classNames(row) {
  const names = (row.classes || []).map(c => c.name)
  return names.length ? names.join('、') : '—'
}

onMounted(() => {
  loadOverview()
  loadUsers()
  loadClasses()
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
            <el-select v-model="query.status" placeholder="状态" style="width: 120px" @change="onSearch">
              <el-option v-for="o in statusOptions" :key="o.value" :value="o.value" :label="o.label" />
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
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="roleTagType[row.role]" effect="light">{{ row.role }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType[row.status]" effect="light">
              {{ statusLabel[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="班级" min-width="140">
          <template #default="{ row }">{{ classNames(row) }}</template>
        </el-table-column>
        <el-table-column label="注册时间" width="170">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="最近登录" width="170">
          <template #default="{ row }">{{ formatDate(row.last_login) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="340" fixed="right">
          <template #default="{ row }">
            <el-dropdown
              :disabled="row.id === auth.userId"
              trigger="click"
              @command="(c) => setStatus(row, c)"
            >
              <el-button size="small" :disabled="row.id === auth.userId">
                审核<el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="approved" :disabled="row.status === 'approved'">通过</el-dropdown-item>
                  <el-dropdown-item command="rejected" :disabled="row.status === 'rejected'">拒绝</el-dropdown-item>
                  <el-dropdown-item command="pending" :disabled="row.status === 'pending'" divided>重置为待审核</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button
              size="small"
              :disabled="row.id === auth.userId"
              @click="openAssign(row)"
            >
              分配班级
            </el-button>
            <el-button
              size="small"
              :disabled="row.id === auth.userId"
              @click="resetPassword(row)"
            >
              重置密码
            </el-button>
            <el-dropdown
              :disabled="row.id === auth.userId"
              trigger="click"
              @command="(c) => changeRole(row, c)"
            >
              <el-button size="small" :disabled="row.id === auth.userId">
                角色<el-icon class="el-icon--right"><ArrowDown /></el-icon>
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

    <!-- 分配班级对话框 -->
    <el-dialog v-model="assignDlg.visible" title="分配班级" width="480px">
      <template v-if="assignDlg.user">
        <p class="assign-tip">
          {{ assignDlg.user.username }}（{{ assignDlg.user.role === 'student' ? '学生，只能属于一个班级' : '教师，可任教多个班级' }}）
        </p>
        <el-select
          v-model="assignDlg.classIds"
          :multiple="assignDlg.user.role !== 'student'"
          placeholder="选择班级"
          style="width: 100%"
        >
          <el-option v-for="c in classes" :key="c.id" :value="c.id" :label="c.name" />
        </el-select>
        <p class="assign-tip sub">
          学生未入班将无法刷题和考试；班级学科范围决定其可用的学科内容。
        </p>
      </template>
      <template #footer>
        <el-button @click="assignDlg.visible = false">取消</el-button>
        <el-button type="primary" @click="submitAssign">保存</el-button>
      </template>
    </el-dialog>
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
.assign-tip {
  margin: 0 0 12px;
  font-size: 14px;
}
.assign-tip.sub {
  margin: 12px 0 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
